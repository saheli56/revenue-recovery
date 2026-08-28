from pydantic import BaseModel, Field
from typing import Dict

class DatasetDistributionConfig(BaseModel):
    total_records: int = Field(default=150, ge=10, le=1000)
    seed: int = Field(default=42)
    payment_failure_weight: float = Field(default=0.5)
    checkout_abandonment_weight: float = Field(default=0.3)
    subscription_failure_weight: float = Field(default=0.2)
    fraud_exclusion_rate: float = Field(default=0.06)
    refund_exclusion_rate: float = Field(default=0.04)
    duplicate_exclusion_rate: float = Field(default=0.04)
    hinglish_note_rate: float = Field(default=0.35)
    error_code_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "insufficient_funds": 0.30,
            "card_expired": 0.20,
            "issuer_timeout": 0.20,
            "authentication_failed": 0.15,
            "gateway_declined": 0.10,
            "BAD_REQUEST_ERROR": 0.05
        }
    )
