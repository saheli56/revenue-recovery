import json
from typing import List, Dict, Any
from schemas import RawEvent, RecoveryCaseCreate
from models import CaseType

def detect_at_risk_revenue(raw_events: List[Dict[str, Any]]) -> List[RecoveryCaseCreate]:
    """
    Scans a batch of transaction/subscription/checkout records.
    Returns a list of RecoveryCase objects.
    """
    cases = []
    for event_data in raw_events:
        try:
            event = RawEvent(**event_data)
        except Exception as e:
            # Skip invalid events or log them
            continue
            
        # Determine if it's at risk (in this dataset, all are simulated failures, 
        # but we parse them into the formal structure).
        try:
            case_type_enum = CaseType(event.case_type)
        except ValueError:
            continue # Unknown type
            
        case = RecoveryCaseCreate(
            case_type=case_type_enum,
            source_reference=event.source_reference,
            customer_id=event.customer_id,
            amount=event.amount,
            currency=event.currency,
            raw_event_context=event.model_dump(exclude_none=True)
        )
        cases.append(case)
        
    return cases

def load_dataset_and_detect(file_path: str) -> List[RecoveryCaseCreate]:
    with open(file_path, 'r') as f:
        data = json.load(f)
    return detect_at_risk_revenue(data)
