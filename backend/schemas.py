from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from models import CaseType

class RawEvent(BaseModel):
    model_config = ConfigDict(extra='allow')
    source_reference: str
    customer_id: str
    amount: float
    currency: str = "INR"
    case_type: str
    created_at: datetime
    
    # Extra fields can include error_code, customer_note, time_since_abandonment_hours, etc.

class RecoveryCaseCreate(BaseModel):
    case_type: CaseType
    source_reference: str
    customer_id: str
    amount: float
    currency: str
    status: str = "open"
    # To pass along the raw event context to the next stage, we can store it in a dict or pass it alongside
    raw_event_context: Dict[str, Any]
