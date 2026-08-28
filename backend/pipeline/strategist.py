import json
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from models import RecoveryCase, Diagnosis, Decision, AuditLog
from pipeline.policy_rules import get_policy_rule_for_root_cause, PolicyRule
from pipeline.guardrails import GuardrailEngine, GuardrailResult

STRATEGY_TOOL_SCHEMA = {
    "name": "select_bounded_action",
    "description": "Selects a recovery action strictly from the permitted policy actions and provides a human-readable justification.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chosen_action": {
                "type": "string",
                "description": "The exact selected action from the permitted set"
            },
            "justification": {
                "type": "string",
                "description": "Detailed reasoning and rationale for why this action was selected"
            }
        },
        "required": ["chosen_action", "justification"]
    }
}

class StrategistService:
    def __init__(self, db_session: AsyncSession, kill_switch_active: Optional[bool] = None):
        self.session = db_session
        self.guardrail_engine = GuardrailEngine(db_session, kill_switch_active=kill_switch_active)
        self.anthropic_client = (
            anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "mock_or_real_key"
            else None
        )

    async def select_bounded_action_with_llm(
        self,
        rule: PolicyRule,
        case: RecoveryCase,
        diagnosis: Diagnosis
    ) -> tuple[str, str]:
        if len(rule.allowed_actions) == 1:
            return rule.default_action, rule.template_justification

        if self.anthropic_client:
            try:
                system_prompt = (
                    "You are the Strategist agent in an AI Revenue Recovery Engine. "
                    "Select exactly one action from the permitted policy list and justify it."
                )
                user_msg = json.dumps({
                    "root_cause": diagnosis.root_cause,
                    "case_amount": case.amount,
                    "allowed_actions": rule.allowed_actions,
                    "policy_rule_id": rule.rule_id
                })
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=300,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_msg}],
                    tools=[STRATEGY_TOOL_SCHEMA],
                    tool_choice={"type": "tool", "name": "select_bounded_action"}
                )
                for block in response.content:
                    if block.type == "tool_use" and block.name == "select_bounded_action":
                        action = block.input.get("chosen_action")
                        justification = block.input.get("justification")
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
