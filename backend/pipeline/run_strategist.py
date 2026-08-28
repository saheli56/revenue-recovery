import asyncio
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import async_session_factory
from pipeline.strategist import StrategistService
from models import Decision

async def execute_strategist_stage():
    async with async_session_factory() as session:
        strategist = StrategistService(session)
        decisions: List[Decision] = await strategist.run_strategist_batch()

    total = len(decisions)
    passed_guardrails = [d for d in decisions if d.guardrail_checks_passed]
    blocked_guardrails = [d for d in decisions if not d.guardrail_checks_passed]

    action_counts: Dict[str, int] = {}
    rule_counts: Dict[str, int] = {}
    for d in decisions:
        action_counts[d.chosen_action] = action_counts.get(d.chosen_action, 0) + 1
        rule_counts[d.policy_rule_id] = rule_counts.get(d.policy_rule_id, 0) + 1

    print("\n=======================================================")
    print(f"       STRATEGIST STAGE EXECUTION REPORT ({total} CASES)")
    print("=======================================================")
    print(f"Total Decisions Generated   : {total}")
    print(f"Guardrail Checks Passed     : {len(passed_guardrails):3d} ({(len(passed_guardrails) / max(total, 1)) * 100:5.1f}%)")
    print(f"Guardrail Blocks / Halts    : {len(blocked_guardrails):3d} ({(len(blocked_guardrails) / max(total, 1)) * 100:5.1f}%)")
    print("-------------------------------------------------------")
    print("Action Breakdown:")
    for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {action:<42}: {count:3d}")
    print("-------------------------------------------------------")
    print("Policy Rules Triggered:")
    for rule_id, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {rule_id:<30}: {count:3d}")
    print("=======================================================\n")
    return decisions

if __name__ == "__main__":
    asyncio.run(execute_strategist_stage())
