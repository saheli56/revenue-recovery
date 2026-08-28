"""initial_schema_all_tables

Revision ID: 98235a7cb7a3
Revises: 
Create Date: 2026-08-28 10:40:58.296197+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '98235a7cb7a3'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('recovery_case',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('case_type', sa.Enum('payment_failure', 'checkout_abandonment', 'subscription_failure', name='case_type_enum'), nullable=False),
    sa.Column('source_reference', sa.String(length=255), nullable=False),
    sa.Column('customer_id', sa.String(length=255), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_case_case_type'), 'recovery_case', ['case_type'], unique=False)
    op.create_index(op.f('ix_recovery_case_customer_id'), 'recovery_case', ['customer_id'], unique=False)
    op.create_index(op.f('ix_recovery_case_id'), 'recovery_case', ['id'], unique=False)
    op.create_index(op.f('ix_recovery_case_source_reference'), 'recovery_case', ['source_reference'], unique=True)
    op.create_index(op.f('ix_recovery_case_status'), 'recovery_case', ['status'], unique=False)
    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('stage', sa.String(length=100), nullable=False),
    sa.Column('event', sa.String(length=255), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['recovery_case.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_case_id'), 'audit_log', ['case_id'], unique=False)
    op.create_index(op.f('ix_audit_log_event'), 'audit_log', ['event'], unique=False)
    op.create_index(op.f('ix_audit_log_id'), 'audit_log', ['id'], unique=False)
    op.create_index(op.f('ix_audit_log_stage'), 'audit_log', ['stage'], unique=False)
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'], unique=False)
    op.create_table('diagnosis',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('root_cause', sa.String(length=255), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('evidence', sa.JSON(), nullable=False),
    sa.Column('method', sa.Enum('rule', 'llm', name='diagnosis_method_enum'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['recovery_case.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diagnosis_case_id'), 'diagnosis', ['case_id'], unique=False)
    op.create_index(op.f('ix_diagnosis_id'), 'diagnosis', ['id'], unique=False)
    op.create_index(op.f('ix_diagnosis_root_cause'), 'diagnosis', ['root_cause'], unique=False)
    op.create_table('outcome',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('recovered', sa.Boolean(), nullable=False),
    sa.Column('recovered_amount', sa.Float(), nullable=True),
    sa.Column('recovered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('final_status', sa.Enum('recovered', 'failed', 'escalated', 'stopped_by_policy', name='final_status_enum'), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['recovery_case.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outcome_case_id'), 'outcome', ['case_id'], unique=False)
    op.create_index(op.f('ix_outcome_final_status'), 'outcome', ['final_status'], unique=False)
    op.create_index(op.f('ix_outcome_id'), 'outcome', ['id'], unique=False)
    op.create_index(op.f('ix_outcome_recovered'), 'outcome', ['recovered'], unique=False)
    op.create_table('decision',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('diagnosis_id', sa.Integer(), nullable=False),
    sa.Column('chosen_action', sa.String(length=255), nullable=False),
    sa.Column('justification', sa.String(length=1000), nullable=False),
    sa.Column('policy_rule_id', sa.String(length=255), nullable=False),
    sa.Column('guardrail_checks_passed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['recovery_case.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnosis.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_decision_case_id'), 'decision', ['case_id'], unique=False)
    op.create_index(op.f('ix_decision_chosen_action'), 'decision', ['chosen_action'], unique=False)
    op.create_index(op.f('ix_decision_diagnosis_id'), 'decision', ['diagnosis_id'], unique=False)
    op.create_index(op.f('ix_decision_id'), 'decision', ['id'], unique=False)
    op.create_index(op.f('ix_decision_policy_rule_id'), 'decision', ['policy_rule_id'], unique=False)
    op.create_table('execution',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('decision_id', sa.Integer(), nullable=False),
    sa.Column('channel', sa.String(length=100), nullable=False),
    sa.Column('external_reference', sa.String(length=255), nullable=True),
    sa.Column('status', sa.String(length=100), nullable=False),
    sa.Column('raw_response', sa.JSON(), nullable=True),
    sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['decision_id'], ['decision.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_channel'), 'execution', ['channel'], unique=False)
    op.create_index(op.f('ix_execution_decision_id'), 'execution', ['decision_id'], unique=False)
    op.create_index(op.f('ix_execution_external_reference'), 'execution', ['external_reference'], unique=False)
    op.create_index(op.f('ix_execution_id'), 'execution', ['id'], unique=False)
    op.create_index(op.f('ix_execution_status'), 'execution', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_execution_status'), table_name='execution')
    op.drop_index(op.f('ix_execution_id'), table_name='execution')
    op.drop_index(op.f('ix_execution_external_reference'), table_name='execution')
    op.drop_index(op.f('ix_execution_decision_id'), table_name='execution')
    op.drop_index(op.f('ix_execution_channel'), table_name='execution')
    op.drop_table('execution')
    op.drop_index(op.f('ix_decision_policy_rule_id'), table_name='decision')
    op.drop_index(op.f('ix_decision_id'), table_name='decision')
    op.drop_index(op.f('ix_decision_diagnosis_id'), table_name='decision')
    op.drop_index(op.f('ix_decision_chosen_action'), table_name='decision')
    op.drop_index(op.f('ix_decision_case_id'), table_name='decision')
    op.drop_table('decision')
    op.drop_index(op.f('ix_outcome_recovered'), table_name='outcome')
    op.drop_index(op.f('ix_outcome_id'), table_name='outcome')
    op.drop_index(op.f('ix_outcome_final_status'), table_name='outcome')
    op.drop_index(op.f('ix_outcome_case_id'), table_name='outcome')
    op.drop_table('outcome')
    op.drop_index(op.f('ix_diagnosis_root_cause'), table_name='diagnosis')
    op.drop_index(op.f('ix_diagnosis_id'), table_name='diagnosis')
    op.drop_index(op.f('ix_diagnosis_case_id'), table_name='diagnosis')
    op.drop_table('diagnosis')
    op.drop_index(op.f('ix_audit_log_timestamp'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_stage'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_event'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_case_id'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index(op.f('ix_recovery_case_status'), table_name='recovery_case')
    op.drop_index(op.f('ix_recovery_case_source_reference'), table_name='recovery_case')
    op.drop_index(op.f('ix_recovery_case_id'), table_name='recovery_case')
    op.drop_index(op.f('ix_recovery_case_customer_id'), table_name='recovery_case')
    op.drop_index(op.f('ix_recovery_case_case_type'), table_name='recovery_case')
    op.drop_table('recovery_case')
