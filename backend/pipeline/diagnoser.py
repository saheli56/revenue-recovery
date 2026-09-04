import json
import os
import sys
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from models import RecoveryCase, Diagnosis, AuditLog, CaseType, DiagnosisMethod

class StructuredDiagnosisOutput(BaseModel):
    root_cause: str = Field(description="Standardized root cause category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence: Dict[str, Any] = Field(description="Evidence dictionary supporting the diagnosis")

GEMINI_FLASH_CASCADING_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-omni-1.1-flash"
]

class DiagnoserService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    def is_ambiguous_case(self, case: RecoveryCase, raw_payload: Dict[str, Any]) -> bool:
        note = raw_payload.get("customer_note", "") or raw_payload.get("notes", "") or raw_payload.get("customer_inquiry", "")
        hinglish_keywords = ["paise", "gaye", "bhai", "karna", "nahi", "raha", "chhod", "otp", "kat", "dekh", "cut", "debit", "kat gaya"]
        note_lower = note.lower()
        has_hinglish = any(word in note_lower for word in hinglish_keywords)
        error_code = raw_payload.get("error_code")

        if has_hinglish:
            return True
        if error_code in ["BAD_REQUEST_ERROR", "technical_error", "gateway_error", "UNKNOWN"]:
            return True
        if case.case_type == CaseType.payment_failure and not error_code:
            return True
        return False

    def diagnose_with_rules(self, case: RecoveryCase, raw_payload: Dict[str, Any]) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        if case.case_type == CaseType.payment_failure:
            error_code = raw_payload.get("error_code")
            if error_code == "insufficient_funds":
                return "insufficient_funds", 1.0, {"error_code": "insufficient_funds", "source": "gateway_exact_match"}
            if error_code == "card_expired":
                return "card_expired", 1.0, {"error_code": "card_expired", "source": "gateway_exact_match"}
            if error_code == "issuer_timeout":
                return "issuer_timeout", 1.0, {"error_code": "issuer_timeout", "source": "gateway_exact_match"}
            if error_code == "authentication_failed":
                return "authentication_failed", 1.0, {"error_code": "authentication_failed", "source": "gateway_exact_match"}
            if error_code == "gateway_declined":
                return "gateway_declined", 1.0, {"error_code": "gateway_declined", "source": "gateway_exact_match"}

        elif case.case_type == CaseType.checkout_abandonment:
            time_hrs = raw_payload.get("time_since_abandonment_hours", 12)
            history = raw_payload.get("customer_history", "first_time")
            if time_hrs <= 12 and history in ["repeat_loyal", "repeat_occasional"]:
                return "high_intent_abandonment", 0.95, {
                    "abandonment_hours": time_hrs,
                    "customer_history": history,
                    "source": "deterministic_abandonment_matrix"
                }
            if time_hrs > 24:
                return "price_sensitive_abandonment", 0.90, {
                    "abandonment_hours": time_hrs,
                    "source": "deterministic_abandonment_matrix"
                }
            return "high_intent_abandonment", 0.85, {
                "abandonment_hours": time_hrs,
                "source": "default_abandonment_rule"
            }

        elif case.case_type == CaseType.subscription_failure:
            retry_count = raw_payload.get("retry_count", 0)
            if retry_count >= 3:
                return "subscription_mandate_exhausted", 1.0, {
                    "retry_count": retry_count,
                    "max_retries_exceeded": True,
                    "source": "subscription_retry_counter"
                }
            return "subscription_card_update_needed", 0.90, {
                "retry_count": retry_count,
                "source": "subscription_retry_counter"
            }

        return None

    async def _call_groq_llm(self, system_prompt: str, user_content: str) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "mock_key":
            return None
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt + "\nReturn strictly JSON formatted with keys: root_cause (enum string), confidence (float between 0 and 1), evidence (object)."},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return (
                        parsed.get("root_cause", "technical_unknown_error"),
                        float(parsed.get("confidence", 0.90)),
                        parsed.get("evidence", {"provider": "groq", "model": settings.GROQ_MODEL})
                    )
            except Exception:
                return None
        return None

    async def _call_gemini_llm(self, system_prompt: str, user_content: str) -> Optional[Tuple[str, float, Dict[str, Any]]]:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "mock_key":
            return None

        prompt_text = (
            f"{system_prompt}\n"
            f"Analyze this payload and return strictly a valid JSON object with keys: root_cause, confidence, evidence.\n"
            f"Allowed root_cause values: insufficient_funds, card_expired, issuer_timeout, authentication_failed, "
            f"gateway_declined, customer_dispute_or_charged_unconfirmed, otp_latency_timeout, "
            f"high_intent_abandonment, price_sensitive_abandonment, subscription_mandate_exhausted, "
            f"subscription_card_update_needed, technical_unknown_error.\n\n"
            f"Payload: {user_content}"
        )

        async with httpx.AsyncClient(timeout=8.0) as client:
            for model_name in GEMINI_FLASH_CASCADING_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "temperature": 0.1
                    }
                }
                try:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            raw_text = candidates[0]["content"]["parts"][0]["text"]
                            parsed = json.loads(raw_text)
                            evidence = parsed.get("evidence", {})
                            if isinstance(evidence, dict):
                                evidence["provider"] = "gemini"
                                evidence["model"] = model_name
                                if "signals_used" not in evidence:
                                    evidence["signals_used"] = ["gemini_llm_inference", model_name]
                            else:
                                evidence = {"provider": "gemini", "model": model_name, "signals_used": ["gemini_llm_inference"], "raw_evidence": evidence}
                            return (
                                parsed.get("root_cause", "technical_unknown_error"),
                                float(parsed.get("confidence", 0.92)),
                                evidence
                            )
                except Exception:
                    continue
        return None

    async def diagnose_with_llm(self, case: RecoveryCase, raw_payload: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        system_prompt = (
            "You are the expert Diagnoser agent in an AI Revenue Recovery Engine for Razorpay. "
            "Analyze the ambiguous transaction, Hinglish regional support note, or dropoff context. "
            "Extract the exact root cause, confidence score (0.0 - 1.0), and supporting evidence signals."
        )

        user_content = json.dumps({
            "case_type": case.case_type.value,
            "amount": case.amount,
            "currency": case.currency,
            "raw_payload": raw_payload
        })

        groq_result = await self._call_groq_llm(system_prompt, user_content)
        if groq_result:
            return groq_result

        gemini_result = await self._call_gemini_llm(system_prompt, user_content)
        if gemini_result:
            return gemini_result

        note = str(raw_payload.get("customer_note", "") or raw_payload.get("notes", "") or raw_payload.get("customer_inquiry", "")).lower()
        if "otp" in note:
            return "otp_latency_timeout", 0.88, {"detected_intent": "otp_delivery_failure", "signals_used": ["customer_note_otp"], "provider": "rule_fallback"}
        if "cut" in note or "debit" in note or "kat" in note or "paise" in note:
            return "customer_dispute_or_charged_unconfirmed", 0.92, {"detected_intent": "money_deducted_unconfirmed", "signals_used": ["hinglish_debit_keywords"], "provider": "rule_fallback"}
        if "expired" in note:
            return "card_expired", 0.95, {"detected_intent": "card_expiry_reported", "signals_used": ["customer_note_expiry"], "provider": "rule_fallback"}
        if "discount" in note or "chhod" in note:
            return "price_sensitive_abandonment", 0.89, {"detected_intent": "coupon_dropoff", "signals_used": ["cart_coupon_note"], "provider": "rule_fallback"}

        return "technical_unknown_error", 0.65, {"detected_intent": "unclassified_ambiguity", "signals_used": ["fallback_classifier"], "provider": "rule_fallback"}

    async def diagnose_single_case(self, case_id: int) -> Optional[Diagnosis]:
        case = await self.session.get(RecoveryCase, case_id)
        if not case or case.status == "excluded":
            return None

        audit_stmt = (
            select(AuditLog)
            .where(and_(AuditLog.case_id == case_id, AuditLog.stage == "ingestion"))
            .order_by(AuditLog.id.desc())
        )
        audit_res = await self.session.execute(audit_stmt)
        ingestion_log = audit_res.scalars().first()
        raw_payload = ingestion_log.payload if ingestion_log else {}

        if self.is_ambiguous_case(case, raw_payload):
            root_cause, confidence, evidence = await self.diagnose_with_llm(case, raw_payload)
            method = DiagnosisMethod.llm
        else:
            rule_result = self.diagnose_with_rules(case, raw_payload)
            if rule_result:
                root_cause, confidence, evidence = rule_result
                method = DiagnosisMethod.rule
            else:
                root_cause, confidence, evidence = await self.diagnose_with_llm(case, raw_payload)
                method = DiagnosisMethod.llm

        diagnosis = Diagnosis(
            case_id=case.id,
            root_cause=root_cause,
            confidence=confidence,
            evidence=evidence,
            method=method,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(diagnosis)
        await self.session.flush()

        case.status = "diagnosed"

        audit_log = AuditLog(
            case_id=case.id,
            stage="diagnoser",
            event="diagnosis_completed",
            payload={
                "diagnosis_id": diagnosis.id,
                "root_cause": root_cause,
                "confidence": confidence,
                "method": method.value,
                "evidence": evidence
            },
            timestamp=datetime.now(timezone.utc)
        )
        self.session.add(audit_log)
        await self.session.flush()

        return diagnosis

    async def run_diagnoser_batch(self, limit: Optional[int] = None) -> List[Diagnosis]:
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.status != "excluded")
            .order_by(RecoveryCase.id.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        cases = result.scalars().all()

        diagnoses: List[Diagnosis] = []
        for case in cases:
            existing_diag_stmt = select(Diagnosis).where(Diagnosis.case_id == case.id)
            diag_res = await self.session.execute(existing_diag_stmt)
            existing = diag_res.scalars().first()
            if existing:
                diagnoses.append(existing)
                continue

            diag = await self.diagnose_single_case(case.id)
            if diag:
                diagnoses.append(diag)

        await self.session.commit()
        return diagnoses
