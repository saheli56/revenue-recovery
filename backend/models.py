from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum
import datetime

Base = declarative_base()

class CaseType(enum.Enum):
    payment_failure = "payment_failure"
    checkout_abandonment = "checkout_abandonment"
    subscription_failure = "subscription_failure"

class FinalStatus(enum.Enum):
    recovered = "recovered"
    failed = "failed"
    escalated = "escalated"
    stopped_by_policy = "stopped_by_policy"

class RecoveryCase(Base):
    __tablename__ = "recovery_case"
    id = Column(Integer, primary_key=True, index=True)
    case_type = Column(Enum(CaseType), nullable=False)
    source_reference = Column(String, nullable=False, unique=True)
    customer_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    status = Column(String, nullable=False, default="open") # open, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Diagnosis(Base):
    __tablename__ = "diagnosis"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_case.id"), nullable=False)
    root_cause = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=False)
    method = Column(String, nullable=False) # 'rule' or 'llm'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Decision(Base):
    __tablename__ = "decision"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_case.id"), nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("diagnosis.id"), nullable=False)
    chosen_action = Column(String, nullable=False)
    justification = Column(String, nullable=False)
    policy_rule_id = Column(String, nullable=False)
    guardrail_checks_passed = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Execution(Base):
    __tablename__ = "execution"
    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, ForeignKey("decision.id"), nullable=False)
    channel = Column(String, nullable=False)
    external_reference = Column(String, nullable=True)
    status = Column(String, nullable=False)
    raw_response = Column(JSON, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

class Outcome(Base):
    __tablename__ = "outcome"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_case.id"), nullable=False)
    recovered = Column(Boolean, nullable=False, default=False)
    recovered_amount = Column(Float, nullable=True)
    recovered_at = Column(DateTime(timezone=True), nullable=True)
    final_status = Column(Enum(FinalStatus), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_case.id"), nullable=False)
    stage = Column(String, nullable=False)
    event = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
