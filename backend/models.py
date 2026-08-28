import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class CaseType(str, enum.Enum):
    payment_failure = "payment_failure"
    checkout_abandonment = "checkout_abandonment"
    subscription_failure = "subscription_failure"

class DiagnosisMethod(str, enum.Enum):
    rule = "rule"
    llm = "llm"

class FinalStatus(str, enum.Enum):
    recovered = "recovered"
    failed = "failed"
    escalated = "escalated"
    stopped_by_policy = "stopped_by_policy"

class RecoveryCase(Base):
    __tablename__ = "recovery_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    case_type: Mapped[CaseType] = mapped_column(SQLEnum(CaseType, name="case_type_enum"), nullable=False, index=True)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    diagnoses: Mapped[List["Diagnosis"]] = relationship("Diagnosis", back_populates="case", cascade="all, delete-orphan")
    decisions: Mapped[List["Decision"]] = relationship("Decision", back_populates="case", cascade="all, delete-orphan")
    outcomes: Mapped[List["Outcome"]] = relationship("Outcome", back_populates="case", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")

class Diagnosis(Base):
    __tablename__ = "diagnosis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("recovery_case.id", ondelete="CASCADE"), nullable=False, index=True)
    root_cause: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    method: Mapped[DiagnosisMethod] = mapped_column(SQLEnum(DiagnosisMethod, name="diagnosis_method_enum"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    case: Mapped["RecoveryCase"] = relationship("RecoveryCase", back_populates="diagnoses")
    decisions: Mapped[List["Decision"]] = relationship("Decision", back_populates="diagnosis", cascade="all, delete-orphan")

class Decision(Base):
    __tablename__ = "decision"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("recovery_case.id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis_id: Mapped[int] = mapped_column(Integer, ForeignKey("diagnosis.id", ondelete="CASCADE"), nullable=False, index=True)
    chosen_action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    justification: Mapped[str] = mapped_column(String(1000), nullable=False)
    policy_rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    guardrail_checks_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    case: Mapped["RecoveryCase"] = relationship("RecoveryCase", back_populates="decisions")
    diagnosis: Mapped["Diagnosis"] = relationship("Diagnosis", back_populates="decisions")
    executions: Mapped[List["Execution"]] = relationship("Execution", back_populates="decision", cascade="all, delete-orphan")

class Execution(Base):
    __tablename__ = "execution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(Integer, ForeignKey("decision.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    decision: Mapped["Decision"] = relationship("Decision", back_populates="executions")

class Outcome(Base):
    __tablename__ = "outcome"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("recovery_case.id", ondelete="CASCADE"), nullable=False, index=True)
    recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    recovered_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    final_status: Mapped[FinalStatus] = mapped_column(SQLEnum(FinalStatus, name="final_status_enum"), nullable=False, index=True)

    case: Mapped["RecoveryCase"] = relationship("RecoveryCase", back_populates="outcomes")

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("recovery_case.id", ondelete="CASCADE"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    case: Mapped["RecoveryCase"] = relationship("RecoveryCase", back_populates="audit_logs")
