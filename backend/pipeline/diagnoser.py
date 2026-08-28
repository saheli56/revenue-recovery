import json
import os
import sys
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from models import RecoveryCase, Diagnosis, AuditLog, CaseType, DiagnosisMethod

class StructuredDiagnosisOutput(BaseModel):
    root_cause: str = Field(description="Standardized root cause category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence: Dict[str, Any] = Field(description="Evidence dictionary supporting the diagnosis")

DIAGNOSIS_TOOL_SCHEMA = {
    "name": "record_diagnosis",
    "description": "Records the root cause diagnosis with confidence and evidence for a failed transaction or abandonment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause": {
                "type": "string",
                "enum": [
                    "insufficient_funds",
                    "card_expired",
                    "issuer_timeout",
                    "authentication_failed",
                    "gateway_declined",
                    "customer_dispute_or_charged_unconfirmed",
                    "otp_latency_timeout",
                    "high_intent_abandonment",
                    "price_sensitive_abandonment",
                    "subscription_mandate_exhausted",
                    "subscription_card_update_needed",
                    "technical_unknown_error"
                ]
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0
            },
            "evidence": {
                "type": "object",
                "properties": {
                    "detected_intent": {"type": "string"},
                    "extracted_keywords": {"type": "array", "items": {"type": "string"}},
                    "signals_used": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["signals_used"]
            }
        },
        "required": ["root_cause", "confidence", "evidence"]
    }
}

class DiagnoserService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session
        self.anthropic_client = (
            anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "mock_or_real_key"
            else None
        )

    def is_ambiguous_case(self, case: RecoveryCase, raw_payload: Dict[str, Any]) -> bool:
        note = raw_payload.get("customer_note", "")
        hinglish_keywords = ["Paise", "gaye", "Bhai", "karna", "nahi", "raha", "chhod", "OTP", "kat", "dekh"]
        has_hinglish = any(word in note for word in hinglish_keywords)
        error_code = raw_payload.get("error_code")

        if has_hinglish:
            return True
        if error_code == "BAD_REQUEST_ERROR":
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

    async def diagnose_with_llm(self, case: RecoveryCase, raw_payload: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        system_prompt = (
            "You are the expert Diagnoser agent in an AI Revenue Recovery Engine. "
            "Analyze the ambiguous transaction or regional language note, and extract the exact root cause, "
            "confidence score, and supporting signals using the record_diagnosis tool."
        )

        user_content = json.dumps({
            "case_type": case.case_type.value,
            "amount": case.amount,
            "currency": case.currency,
            "raw_payload": raw_payload
        })

        if self.anthropic_client:
            try:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                    tools=[DIAGNOSIS_TOOL_SCHEMA],
                    tool_choice={"type": "tool", "name": "record_diagnosis"}
                )

                for block in response.content:
                    if block.type == "tool_use" and block.name == "record_diagnosis":
                        input_data = block.input
                        return (
                            input_data["root_cause"],
                            float(input_data["confidence"]),
                            input_data["evidence"]
                        )
            except Exception as exc:
                pass

        note = raw_payload.get("customer_note", "").lower()
        if "otp" in note:
            return "otp_latency_timeout", 0.88, {"detected_intent": "otp_delivery_failure", "signals_used": ["customer_note_otp"]}
        if "cut" in note or "debit" in note or "kat" in note:
            return "customer_dispute_or_charged_unconfirmed", 0.92, {"detected_intent": "money_deducted_unconfirmed", "signals_used": ["hinglish_debit_keywords"]}
        if "expired" in note:
            return "card_expired", 0.95, {"detected_intent": "card_expiry_reported", "signals_used": ["customer_note_expiry"]}
        if "discount" in note or "chhod" in note:
            return "price_sensitive_abandonment", 0.89, {"detected_intent": "coupon_dropoff", "signals_used": ["cart_coupon_note"]}

        return "technical_unknown_error", 0.65, {"detected_intent": "unclassified_ambiguity", "signals_used": ["fallback_classifier"]}

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
