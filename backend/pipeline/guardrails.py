from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from models import RecoveryCase, Decision, Execution, AuditLog

@dataclass
class GuardrailResult:
    passed: bool
    failed_checks: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

class GuardrailEngine:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def evaluate_guardrails(
        self,
        case: RecoveryCase,
        max_allowed_retries: int,
        cooldown_hours: int,
        daily_customer_cap: int = 3
    ) -> GuardrailResult:
        failed_checks: List[str] = []
        reasons: List[str] = []
        now = datetime.now(timezone.utc)

        if settings.GLOBAL_KILL_SWITCH:
            failed_checks.append("GLOBAL_KILL_SWITCH_ACTIVE")
            reasons.append("Global kill switch is enabled across the recovery engine")

        if case.status == "excluded":
            failed_checks.append("CASE_EXCLUDED")
            reasons.append("Case was marked as excluded by detector stage")

        decision_count_stmt = select(func.count(Decision.id)).where(Decision.case_id == case.id)
        decision_count_res = await self.session.execute(decision_count_stmt)
        total_case_decisions = decision_count_res.scalar() or 0

        retry_limit_threshold = 1 if max_allowed_retries == 0 else max_allowed_retries
        if total_case_decisions >= retry_limit_threshold:
            failed_checks.append("MAX_RETRIES_EXCEEDED")
            reasons.append(f"Case attempts ({total_case_decisions}) reached or exceeded policy maximum ({max_allowed_retries})")

        last_exec_stmt = (
            select(Execution.executed_at)
            .join(Decision, Execution.decision_id == Decision.id)
            .where(Decision.case_id == case.id)
            .order_by(Execution.executed_at.desc())
        )
        last_exec_res = await self.session.execute(last_exec_stmt)
        last_executed_at = last_exec_res.scalars().first()

        if last_executed_at and cooldown_hours > 0:
            if last_executed_at.tzinfo is None:
                last_executed_at = last_executed_at.replace(tzinfo=timezone.utc)
            elapsed_time = now - last_executed_at
            required_cooldown = timedelta(hours=cooldown_hours)
            if elapsed_time < required_cooldown:
                remaining_mins = int((required_cooldown - elapsed_time).total_seconds() / 60)
                failed_checks.append("COOLDOWN_WINDOW_ACTIVE")
                reasons.append(f"Action blocked by cooldown window ({remaining_mins} minutes remaining)")

        one_day_ago = now - timedelta(days=1)
        customer_actions_stmt = (
            select(func.count(Decision.id))
            .join(RecoveryCase, Decision.case_id == RecoveryCase.id)
            .where(
                and_(
                    RecoveryCase.customer_id == case.customer_id,
                    Decision.created_at >= one_day_ago,
                    Decision.guardrail_checks_passed.is_(True)
                )
            )
        )
        cust_actions_res = await self.session.execute(customer_actions_stmt)
        daily_actions_count = cust_actions_res.scalar() or 0

        if daily_actions_count >= daily_customer_cap:
            failed_checks.append("DAILY_CUSTOMER_CAP_REACHED")
            reasons.append(f"Daily recovery action cap reached for customer ({daily_actions_count}/{daily_customer_cap})")

        passed = len(failed_checks) == 0
        return GuardrailResult(
            passed=passed,
            failed_checks=failed_checks,
            reasons=reasons,
            metrics={
                "case_attempts": total_case_decisions,
                "daily_customer_actions": daily_actions_count,
                "max_allowed_retries": max_allowed_retries,
                "cooldown_hours": cooldown_hours,
                "kill_switch_active": settings.GLOBAL_KILL_SWITCH
            }
        )
