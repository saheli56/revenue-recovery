import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any

class NotificationService:
    def _compute_delivery_success(self, channel: str, recipient_id: str, case_id: int) -> bool:
        seed_str = f"{channel}:{recipient_id}:{case_id}"
        hash_val = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:6], 16)
        probability = (hash_val % 100) / 100.0

        if channel == "simulated_email_service":
            return probability < 0.96
        if channel in ["simulated_whatsapp_service", "simulated_sms_service"]:
            return probability < 0.92
        return True

    def send_email_nudge(self, customer_id: str, case_id: int, subject: str, body: str) -> Dict[str, Any]:
        msg_id = f"email_msg_{uuid.uuid4().hex[:12]}"
        is_delivered = self._compute_delivery_success("simulated_email_service", customer_id, case_id)

        return {
            "channel": "simulated_email_service",
            "message_id": msg_id,
            "recipient": f"{customer_id}@example.com",
            "subject": subject,
            "status": "delivered" if is_delivered else "bounced",
            "provider_response": {
                "smtp_code": 250 if is_delivered else 550,
                "latency_ms": 142,
                "delivered_at": datetime.now(timezone.utc).isoformat() if is_delivered else None
            }
        }

    def send_whatsapp_nudge(self, customer_id: str, case_id: int, template_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        msg_id = f"wa_msg_{uuid.uuid4().hex[:12]}"
        is_delivered = self._compute_delivery_success("simulated_whatsapp_service", customer_id, case_id)

        return {
            "channel": "simulated_whatsapp_service",
            "message_id": msg_id,
            "recipient": f"+9198{case_id:04d}1234",
            "template": template_name,
            "status": "delivered" if is_delivered else "undelivered",
            "provider_response": {
                "whatsapp_msg_id": f"wamid.{msg_id}",
                "read_receipt": is_delivered,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def send_sms_nudge(self, customer_id: str, case_id: int, message_text: str) -> Dict[str, Any]:
        msg_id = f"sms_msg_{uuid.uuid4().hex[:12]}"
        is_delivered = self._compute_delivery_success("simulated_sms_service", customer_id, case_id)

        return {
            "channel": "simulated_sms_service",
            "message_id": msg_id,
            "recipient": f"+9198{case_id:04d}5678",
            "status": "delivered" if is_delivered else "failed",
            "provider_response": {
                "telecom_carrier": "Airtel / Jio DLT",
                "dlt_template_id": "DLT_RECOVERY_001",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def trigger_internal_escalation(self, case_id: int, reason: str, details: Dict[str, Any]) -> Dict[str, Any]:
        ticket_id = f"ticket_esc_{uuid.uuid4().hex[:8]}"

        return {
            "channel": "simulated_internal_escalation",
            "ticket_id": ticket_id,
            "status": "queued_for_human_agent",
            "priority": "P2_HIGH",
            "reason": reason,
            "details": details,
            "assigned_team": "Revenue Operations Tier-2",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
