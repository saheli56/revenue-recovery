import sys
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import RecoveryCase, Decision, Execution, AuditLog
from integrations.razorpay_client import RazorpayClient
from integrations.notification_service import NotificationService

class ExecutorService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session
        self.razorpay_client = RazorpayClient()
        self.notification_service = NotificationService()

    async def execute_single_decision(self, decision_id: int) -> Optional[Execution]:
        decision = await self.session.get(Decision, decision_id)
        if not decision:
            return None

        case = await self.session.get(RecoveryCase, decision.case_id)
        if not case:
            return None

        if not decision.guardrail_checks_passed:
            execution = Execution(
                decision_id=decision.id,
                channel="guardrail_circuit_breaker",
                external_reference=None,
                status="refused_by_guardrails",
                raw_response={
                    "error": "Execution refused",
                    "reason": decision.justification,
                    "policy_rule_id": decision.policy_rule_id
                },
                executed_at=datetime.now(timezone.utc)
            )
            self.session.add(execution)
            await self.session.flush()

            audit = AuditLog(
                case_id=case.id,
                stage="executor",
                event="execution_refused_guardrail_failed",
                payload={
                    "execution_id": execution.id,
                    "decision_id": decision.id,
                    "reason": decision.justification
                },
                timestamp=datetime.now(timezone.utc)
            )
            self.session.add(audit)
            await self.session.flush()
            return execution

        action = decision.chosen_action
        channel_name = "unknown"
        ext_ref = None
        status = "pending"
        raw_response: Dict[str, Any] = {}

        if action in ["delayed_retry_smart_schedule", "immediate_single_retry"]:
            channel_name = "razorpay_orders_api"
            order_res = await self.razorpay_client.create_order(
                amount=case.amount,
                currency=case.currency,
                receipt=f"rcpt_{case.source_reference[:20]}",
                notes={"case_id": case.id, "action": action, "customer_id": case.customer_id}
            )
            ext_ref = order_res.get("data", {}).get("id")
            status = "dispatched" if order_res.get("status") == "success" else "failed"
            raw_response = order_res

        elif action in ["send_fresh_payment_link", "send_flexible_payment_link", "send_subscription_payment_update_link"]:
            channel_name = "razorpay_payment_links_api"
            plink_res = await self.razorpay_client.create_payment_link(
                amount=case.amount,
                currency=case.currency,
                customer_id=case.customer_id,
                description=f"Payment recovery link for {case.source_reference}",
                notes={"case_id": case.id, "action": action}
            )
            ext_ref = plink_res.get("data", {}).get("id")
            status = "dispatched" if plink_res.get("status") == "success" else "failed"
            raw_response = plink_res

        elif action in ["send_update_payment_method_link", "send_cart_recovery_reminder"]:
            channel_name = "simulated_email_service"
            email_res = self.notification_service.send_email_nudge(
                customer_id=case.customer_id,
                case_id=case.id,
                subject=f"Update payment method for Order #{case.source_reference}",
                body="Please update your card or retry payment using our secure link."
            )
            ext_ref = email_res.get("message_id")
            status = email_res.get("status", "delivered")
            raw_response = email_res

        elif action in ["send_incentivized_discount_nudge", "send_alternative_payment_method_nudge"]:
            channel_name = "simulated_whatsapp_service"
            wa_res = self.notification_service.send_whatsapp_nudge(
                customer_id=case.customer_id,
                case_id=case.id,
                template_name="recovery_incentive_v1",
                parameters={"amount": case.amount, "ref": case.source_reference}
            )
            ext_ref = wa_res.get("message_id")
            status = wa_res.get("status", "delivered")
            raw_response = wa_res

        elif action == "send_quick_retry_sms":
            channel_name = "simulated_sms_service"
            sms_res = self.notification_service.send_sms_nudge(
                customer_id=case.customer_id,
                case_id=case.id,
                message_text=f"Click here to instantly retry your payment for {case.source_reference}"
            )
            ext_ref = sms_res.get("message_id")
            status = sms_res.get("status", "delivered")
            raw_response = sms_res

        elif action in [
            "escalate_to_human_recovery_queue",
            "escalate_to_human_support_dispute",
            "escalate_to_technical_queue",
            "escalate_or_stop_by_policy"
        ]:
            channel_name = "simulated_internal_escalation"
            esc_res = self.notification_service.trigger_internal_escalation(
                case_id=case.id,
                reason=decision.justification,
                details={"amount": case.amount, "customer_id": case.customer_id, "action": action}
            )
            ext_ref = esc_res.get("ticket_id")
            status = esc_res.get("status", "queued_for_human_agent")
            raw_response = esc_res

        execution = Execution(
            decision_id=decision.id,
            channel=channel_name,
            external_reference=ext_ref,
            status=status,
            raw_response=raw_response,
            executed_at=datetime.now(timezone.utc)
        )
        self.session.add(execution)
        await self.session.flush()

        case.status = "executed" if status != "failed" else "execution_failed"

        audit = AuditLog(
            case_id=case.id,
            stage="executor",
            event="action_executed",
            payload={
                "execution_id": execution.id,
                "decision_id": decision.id,
                "channel": channel_name,
                "external_reference": ext_ref,
                "status": status,
                "action": action
            },
            timestamp=datetime.now(timezone.utc)
        )
        self.session.add(audit)
        await self.session.flush()

        return execution

    async def run_executor_batch(self, limit: Optional[int] = None) -> List[Execution]:
        stmt = (
            select(Decision)
            .join(RecoveryCase, Decision.case_id == RecoveryCase.id)
            .where(RecoveryCase.status.in_(["decided", "stopped_by_policy"]))
            .order_by(Decision.id.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        decisions = result.scalars().all()

        executions: List[Execution] = []
        for decision in decisions:
            existing_exec_stmt = select(Execution).where(Execution.decision_id == decision.id)
            exec_res = await self.session.execute(existing_exec_stmt)
            existing = exec_res.scalars().first()
            if existing:
                executions.append(existing)
                continue

            ex = await self.execute_single_decision(decision.id)
            if ex:
                executions.append(ex)

        await self.session.commit()
        return executions
