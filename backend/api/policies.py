import os
import sys
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from pipeline.policy_rules import POLICY_RULES_REGISTRY, PolicyRule
from api.auth import verify_api_key

router = APIRouter(prefix="", tags=["Policies & Guardrails"])

class KillSwitchUpdateRequest(BaseModel):
    kill_switch_active: bool

class GuardrailStatusResponse(BaseModel):
    kill_switch_active: bool
    daily_customer_cap: int = 3
    channel_timeout_seconds: int = 10
    total_active_policies: int

@router.get("/policies", dependencies=[Depends(verify_api_key)])
async def get_all_policy_rules() -> Dict[str, Any]:
    rules_list = []
    for r in POLICY_RULES_REGISTRY.values():
        rules_list.append({
            "rule_id": r.rule_id,
            "root_cause": r.root_cause,
            "allowed_actions": r.allowed_actions,
            "default_action": r.default_action,
            "max_retries": r.max_retries,
            "cooldown_hours": r.cooldown_hours,
            "template_justification": r.template_justification
        })
    return {
        "total_rules": len(rules_list),
        "rules": rules_list
    }

@router.get("/guardrails/status", response_model=GuardrailStatusResponse, dependencies=[Depends(verify_api_key)])
async def get_guardrail_status():
    return GuardrailStatusResponse(
        kill_switch_active=settings.GLOBAL_KILL_SWITCH,
        daily_customer_cap=3,
        channel_timeout_seconds=10,
        total_active_policies=len(POLICY_RULES_REGISTRY)
    )

@router.post("/guardrails/kill-switch", response_model=GuardrailStatusResponse, dependencies=[Depends(verify_api_key)])
async def toggle_kill_switch(
    req: KillSwitchUpdateRequest
):
    settings.GLOBAL_KILL_SWITCH = req.kill_switch_active
    return GuardrailStatusResponse(
        kill_switch_active=settings.GLOBAL_KILL_SWITCH,
        daily_customer_cap=3,
        channel_timeout_seconds=10,
        total_active_policies=len(POLICY_RULES_REGISTRY)
    )
