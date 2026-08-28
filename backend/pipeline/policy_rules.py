from dataclasses import dataclass
from typing import List, Dict, Optional
from models import CaseType

@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    root_cause: str
    target_case_type: Optional[CaseType]
    description: str
    allowed_actions: List[str]
    default_action: str
    max_retries: int
    cooldown_hours: int
    channel: str
    template_justification: str

POLICY_RULES_REGISTRY: Dict[str, PolicyRule] = {
    "POL_INSUFFICIENT_FUNDS": PolicyRule(
        rule_id="POL_INSUFFICIENT_FUNDS",
        root_cause="insufficient_funds",
        target_case_type=CaseType.payment_failure,
        description="Delayed retry scheduled on payday cycle window with max 3 attempts",
        allowed_actions=["delayed_retry_smart_schedule", "send_flexible_payment_link"],
        default_action="delayed_retry_smart_schedule",
        max_retries=3,
        cooldown_hours=48,
        channel="razorpay_orders_api",
        template_justification="Insufficient funds diagnosed; policy prescribes delayed retry aligned to liquidity cycles with max 3 attempts"
    ),
    "POL_CARD_EXPIRED": PolicyRule(
        rule_id="POL_CARD_EXPIRED",
        root_cause="card_expired",
        target_case_type=None,
        description="Send update payment method link without automated card retries",
        allowed_actions=["send_update_payment_method_link"],
        default_action="send_update_payment_method_link",
        max_retries=2,
        cooldown_hours=24,
        channel="simulated_email_service",
        template_justification="Card expiration requires customer payment method update; auto-retries suppressed"
    ),
    "POL_ISSUER_TIMEOUT": PolicyRule(
        rule_id="POL_ISSUER_TIMEOUT",
        root_cause="issuer_timeout",
        target_case_type=CaseType.payment_failure,
        description="Immediate single retry on bank gateway timeout",
        allowed_actions=["immediate_single_retry", "send_quick_retry_sms"],
        default_action="immediate_single_retry",
        max_retries=1,
        cooldown_hours=1,
        channel="razorpay_orders_api",
        template_justification="Transient bank issuer timeout; policy authorizes single immediate retry"
    ),
    "POL_AUTH_FAILED": PolicyRule(
        rule_id="POL_AUTH_FAILED",
        root_cause="authentication_failed",
        target_case_type=CaseType.payment_failure,
        description="Send fresh 3DS payment link via omnichannel messaging",
        allowed_actions=["send_fresh_payment_link", "send_quick_retry_sms"],
        default_action="send_fresh_payment_link",
        max_retries=2,
        cooldown_hours=4,
        channel="razorpay_payment_links_api",
        template_justification="3D Secure authentication dropped; fresh payment link dispatched to customer"
    ),
    "POL_GATEWAY_DECLINED": PolicyRule(
        rule_id="POL_GATEWAY_DECLINED",
        root_cause="gateway_declined",
        target_case_type=CaseType.payment_failure,
        description="Offer alternative payment methods (UPI/Netbanking)",
        allowed_actions=["send_alternative_payment_method_nudge"],
        default_action="send_alternative_payment_method_nudge",
        max_retries=2,
        cooldown_hours=12,
        channel="simulated_whatsapp_service",
        template_justification="Card declined by gateway; alternative payment channels recommended"
    ),
    "POL_HIGH_INTENT_ABANDON": PolicyRule(
        rule_id="POL_HIGH_INTENT_ABANDON",
        root_cause="high_intent_abandonment",
        target_case_type=CaseType.checkout_abandonment,
        description="Cart recovery reminder for repeat loyal customers",
        allowed_actions=["send_cart_recovery_reminder", "send_fresh_payment_link"],
        default_action="send_cart_recovery_reminder",
        max_retries=2,
        cooldown_hours=6,
        channel="simulated_email_service",
        template_justification="High intent cart abandonment; gentle reminder dispatched within recovery window"
    ),
    "POL_PRICE_SENSITIVE_ABANDON": PolicyRule(
        rule_id="POL_PRICE_SENSITIVE_ABANDON",
        root_cause="price_sensitive_abandonment",
        target_case_type=CaseType.checkout_abandonment,
        description="Incentivized cart recovery discount nudge for threshold value carts",
        allowed_actions=["send_incentivized_discount_nudge", "send_cart_recovery_reminder"],
        default_action="send_incentivized_discount_nudge",
        max_retries=1,
        cooldown_hours=24,
        channel="simulated_whatsapp_service",
        template_justification="Price-sensitive abandonment with cart value above threshold; discount incentive nudge authorized"
    ),
    "POL_SUB_EXHAUSTED": PolicyRule(
        rule_id="POL_SUB_EXHAUSTED",
        root_cause="subscription_mandate_exhausted",
        target_case_type=CaseType.subscription_failure,
        description="Escalate to human account recovery queue after max retries exhausted",
        allowed_actions=["escalate_to_human_recovery_queue"],
        default_action="escalate_to_human_recovery_queue",
        max_retries=0,
        cooldown_hours=0,
        channel="simulated_internal_escalation",
        template_justification="Subscription retry budget exhausted; stopping automated attempts and escalating to operations"
    ),
    "POL_SUB_UPDATE_NEEDED": PolicyRule(
        rule_id="POL_SUB_UPDATE_NEEDED",
        root_cause="subscription_card_update_needed",
        target_case_type=CaseType.subscription_failure,
        description="Dispatch recurring subscription mandate update link",
        allowed_actions=["send_subscription_payment_update_link"],
        default_action="send_subscription_payment_update_link",
        max_retries=2,
        cooldown_hours=24,
        channel="razorpay_payment_links_api",
        template_justification="Subscription recurring charge failed; mandate update link provided to subscriber"
    ),
    "POL_CUSTOMER_DISPUTE": PolicyRule(
        rule_id="POL_CUSTOMER_DISPUTE",
        root_cause="customer_dispute_or_charged_unconfirmed",
        target_case_type=None,
        description="Halt automated collections and escalate customer billing dispute",
        allowed_actions=["escalate_to_human_support_dispute"],
        default_action="escalate_to_human_support_dispute",
        max_retries=0,
        cooldown_hours=0,
        channel="simulated_internal_escalation",
        template_justification="Customer reported unconfirmed debit; automated recovery halted to prevent double charging"
    ),
    "POL_OTP_TIMEOUT": PolicyRule(
        rule_id="POL_OTP_TIMEOUT",
        root_cause="otp_latency_timeout",
        target_case_type=None,
        description="Dispatch quick retry link via SMS channel",
        allowed_actions=["send_quick_retry_sms"],
        default_action="send_quick_retry_sms",
        max_retries=2,
        cooldown_hours=2,
        channel="simulated_sms_service",
        template_justification="OTP delivery latency caused session expiry; quick retry SMS link dispatched"
    ),
    "POL_TECHNICAL_UNKNOWN": PolicyRule(
        rule_id="POL_TECHNICAL_UNKNOWN",
        root_cause="technical_unknown_error",
        target_case_type=None,
        description="Escalate unclassified failure for engineering inspection",
        allowed_actions=["escalate_to_technical_queue"],
        default_action="escalate_to_technical_queue",
        max_retries=0,
        cooldown_hours=0,
        channel="simulated_internal_escalation",
        template_justification="Unclassified technical failure; automated actions withheld pending manual triage"
    )
}

def get_policy_rule_for_root_cause(root_cause: str) -> PolicyRule:
    for rule in POLICY_RULES_REGISTRY.values():
        if rule.root_cause == root_cause:
            return rule
    return POLICY_RULES_REGISTRY["POL_TECHNICAL_UNKNOWN"]

def get_all_policy_rules() -> List[Dict]:
    return [
        {
            "rule_id": r.rule_id,
            "root_cause": r.root_cause,
            "target_case_type": r.target_case_type.value if r.target_case_type else "all",
            "description": r.description,
            "allowed_actions": r.allowed_actions,
            "default_action": r.default_action,
            "max_retries": r.max_retries,
            "cooldown_hours": r.cooldown_hours,
            "channel": r.channel,
            "template_justification": r.template_justification
        }
        for r in POLICY_RULES_REGISTRY.values()
    ]
