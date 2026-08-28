from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from models import CaseType, DiagnosisMethod, FinalStatus

class RecoveryCaseBase(BaseModel):
    case_type: CaseType
    source_reference: str
    customer_id: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    status: str = "open"

class RecoveryCaseCreate(RecoveryCaseBase):
    pass

class RecoveryCaseResponse(RecoveryCaseBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DiagnosisBase(BaseModel):
    case_id: int
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Dict[str, Any]
    method: DiagnosisMethod

class DiagnosisCreate(DiagnosisBase):
    pass

class DiagnosisResponse(DiagnosisBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DecisionBase(BaseModel):
    case_id: int
    diagnosis_id: int
    chosen_action: str
    justification: str
    policy_rule_id: str
    guardrail_checks_passed: bool

class DecisionCreate(DecisionBase):
    pass

class DecisionResponse(DecisionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ExecutionBase(BaseModel):
    decision_id: int
    channel: str
    external_reference: Optional[str] = None
    status: str
    raw_response: Optional[Dict[str, Any]] = None

class ExecutionCreate(ExecutionBase):
    pass

class ExecutionResponse(ExecutionBase):
    id: int
    executed_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OutcomeBase(BaseModel):
    case_id: int
    recovered: bool = False
    recovered_amount: Optional[float] = None
    recovered_at: Optional[datetime] = None
    final_status: FinalStatus

class OutcomeCreate(OutcomeBase):
    pass

class OutcomeResponse(OutcomeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AuditLogBase(BaseModel):
    case_id: int
    stage: str
    event: str
    payload: Dict[str, Any]

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class CaseTraceResponse(BaseModel):
    case: RecoveryCaseResponse
    diagnoses: List[DiagnosisResponse] = []
    decisions: List[DecisionResponse] = []
    executions: List[ExecutionResponse] = []
    outcomes: List[OutcomeResponse] = []
    audit_logs: List[AuditLogResponse] = []
    model_config = ConfigDict(from_attributes=True)
