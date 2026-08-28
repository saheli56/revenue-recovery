import json
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from models import RecoveryCase, Diagnosis, Decision, AuditLog
from pipeline.policy_rules import get_policy_rule_for_root_cause, PolicyRule
from pipeline.guardrails import GuardrailEngine, GuardrailResult

class StrategistService:
    def __init__(self, db_session: AsyncSession, kill_switch_active: Optional[bool] = None):
        self.session = db_session
        self.guardrail_engine = GuardrailEngine(db_session, kill_switch_active=kill_switch_active)

    async def select_bounded_action_with_llm(
        self,
        rule: PolicyRule,
        case: RecoveryCase,
        diagnosis: Diagnosis
    ) -> tuple[str, str]:
        if len(rule.allowed_actions) == 1:
            return rule.default_action, rule.template_justification

        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "mock_key":
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                system_prompt = (
                    "You are the Strategist in an AI Revenue Recovery Engine for Razorpay. "
                    "Select exactly one action from allowed_actions and provide a concise justification. "
                    "Return JSON with keys: chosen_action, justification."
                )
                user_msg = json.dumps({
                    "root_cause": diagnosis.root_cause,
                    "case_amount": case.amount,
                    "allowed_actions": rule.allowed_actions,
                    "policy_rule_id": rule.rule_id
                })
                payload = {
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.post(url, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        parsed = json.loads(data["choices"][0]["message"]["content"])
                        action = parsed.get("chosen_action")
                        justification = parsed.get("justification")
                        if action in rule.allowed_actions:
                            return action, justification
            except Exception:
                pass

        if case.amount >= 2000.0 and "send_incentivized_discount_nudge" in rule.allowed_actions:
            return (
                "send_incentivized_discount_nudge",
                f"High cart value (INR {case.amount:,.2f}) qualifies for authorized discount recovery nudge"
            )

        return rule.default_action, rule.template_justification

    async def decide_single_case(self, case_id: int) -> Optional[Decision]:
        case = await self.session.get(RecoveryCase, case_id)
        if not case or case.status == "excluded":
            return None

        diag_stmt = select(Diagnosis).where(Diagnosis.case_id == case_id).order_by(Diagnosis.id.desc())
        diag_res = await self.session.execute(diag_stmt)
        diagnosis = diag_res.scalars().first()
        if not diagnosis:
            return None

        rule = get_policy_rule_for_root_cause(diagnosis.root_cause)

        guardrail_result: GuardrailResult = await self.guardrail_engine.evaluate_guardrails(
            case=case,
            max_allowed_retries=rule.max_retries,
            cooldown_hours=rule.cooldown_hours
        )

        if guardrail_result.passed:
            chosen_action, justification = await self.select_bounded_action_with_llm(rule, case, diagnosis)
            guardrails_passed = True
            case.status = "decided"
        else:
            chosen_action = "escalate_or_stop_by_policy"
            justification = f"Guardrail blocked action: {'; '.join(guardrail_result.reasons)}"
            guardrails_passed = False
            case.status = "stopped_by_policy"

        decision = Decision(
            case_id=case.id,
            diagnosis_id=diagnosis.id,
            chosen_action=chosen_action,
            justification=justification,
            policy_rule_id=rule.rule_id,
            guardrail_checks_passed=guardrails_passed,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(decision)
        await self.session.flush()

        audit_log = AuditLog(
            case_id=case.id,
            stage="strategist",
            event="decision_created",
            payload={
                "decision_id": decision.id,
                "policy_rule_id": rule.rule_id,
                "chosen_action": chosen_action,
                "guardrail_checks_passed": guardrails_passed,
                "failed_checks": guardrail_result.failed_checks,
                "metrics": guardrail_result.metrics,
                "justification": justification
            },
            timestamp=datetime.now(timezone.utc)
        )
        self.session.add(audit_log)
        await self.session.flush()

        return decision

    async def run_strategist_batch(self, limit: Optional[int] = None) -> List[Decision]:
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.status.in_(["diagnosed", "detected_at_risk"]))
            .order_by(RecoveryCase.id.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        cases = result.scalars().all()

        decisions: List[Decision] = []
        for case in cases:
            existing_dec_stmt = select(Decision).where(Decision.case_id == case.id)
            dec_res = await self.session.execute(existing_dec_stmt)
            existing = dec_res.scalars().first()
            if existing:
                decisions.append(existing)
                continue

            dec = await self.decide_single_case(case.id)
            if dec:
                decisions.append(dec)

        await self.session.commit()
        return decisions
