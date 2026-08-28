from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models import RecoveryCase, AuditLog, CaseType

@dataclass
class DetectionResult:
    case_id: int
    source_reference: str
    case_type: CaseType
    amount: float
    is_at_risk: bool
    is_excluded: bool
    exclusion_reason: Optional[str]
    raw_payload: Dict[str, Any]

class DetectorService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    def evaluate_case_qualification(self, case: RecoveryCase, raw_payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if raw_payload.get("is_fraud_flagged", False):
            return False, "FRAUD_DISQUALIFIED: Flagged for suspicious fraud pattern"
        if raw_payload.get("is_already_refunded", False):
            return False, "REFUND_DISQUALIFIED: Prior refund already issued for source reference"
        if raw_payload.get("is_duplicate", False):
            return False, "DUPLICATE_DISQUALIFIED: Identical source reference already recorded"
        return True, None

    async def detect_single_case(self, case_id: int) -> Optional[DetectionResult]:
        case = await self.session.get(RecoveryCase, case_id)
        if not case:
            return None

        audit_stmt = (
            select(AuditLog)
            .where(and_(AuditLog.case_id == case_id, AuditLog.stage == "ingestion"))
            .order_by(AuditLog.id.desc())
        )
        audit_res = await self.session.execute(audit_stmt)
        ingestion_log = audit_res.scalars().first()
        raw_payload = ingestion_log.payload if ingestion_log else {}

        is_at_risk, exclusion_reason = self.evaluate_case_qualification(case, raw_payload)
        is_excluded = not is_at_risk

        if is_excluded:
            case.status = "excluded"
            event_type = "case_excluded_from_recovery"
            log_payload = {
                "decision": "excluded",
                "exclusion_reason": exclusion_reason,
                "amount": case.amount,
                "case_type": case.case_type.value,
                "raw_flags": {
                    "is_fraud": raw_payload.get("is_fraud_flagged", False),
                    "is_refunded": raw_payload.get("is_already_refunded", False),
                    "is_duplicate": raw_payload.get("is_duplicate", False)
                }
            }
        else:
            case.status = "detected_at_risk"
            event_type = "case_qualified_at_risk"
            log_payload = {
                "decision": "qualified",
                "amount": case.amount,
                "case_type": case.case_type.value,
                "context_summary": {
                    "customer_id": case.customer_id,
                    "error_code": raw_payload.get("error_code"),
                    "note_length": len(raw_payload.get("customer_note", ""))
                }
            }

        detection_audit = AuditLog(
            case_id=case.id,
            stage="detector",
            event=event_type,
            payload=log_payload,
            timestamp=datetime.now(timezone.utc)
        )
        self.session.add(detection_audit)
        await self.session.flush()

        return DetectionResult(
            case_id=case.id,
            source_reference=case.source_reference,
            case_type=case.case_type,
            amount=case.amount,
            is_at_risk=is_at_risk,
            is_excluded=is_excluded,
            exclusion_reason=exclusion_reason,
            raw_payload=raw_payload
        )

    async def run_detection_batch(self, limit: Optional[int] = None) -> List[DetectionResult]:
        stmt = select(RecoveryCase).order_by(RecoveryCase.id.asc())
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        cases = result.scalars().all()

        results: List[DetectionResult] = []
        for case in cases:
            det_res = await self.detect_single_case(case.id)
            if det_res:
                results.append(det_res)

        await self.session.commit()
        return results
