import pytest
import os
import json
from database import async_session_factory
from evaluation.harness import EvaluationHarness, EvaluationReport

@pytest.mark.asyncio
async def test_evaluation_harness_metrics_consistency(tmp_path):
    output_json = os.path.join(str(tmp_path), "test_eval_report.json")
    async with async_session_factory() as session:
        harness = EvaluationHarness(session)
        report: EvaluationReport = await harness.generate_report(output_file_path=output_json)

    assert report.total_cases > 0
    assert report.total_recovered_amount <= report.total_at_risk_amount
    assert report.total_recovered_amount >= 0.0
    assert report.gross_recovery_rate_pct >= 0.0
    assert report.gross_recovery_rate_pct <= 100.0

    assert report.total_intervention_cost >= 0.0
    expected_net = max(0.0, round(report.total_recovered_amount - report.total_intervention_cost, 2))
    assert abs(report.net_recovered_amount - expected_net) < 0.01

    recovered_count = sum(b.recovered_count for b in report.case_type_breakdown.values())
    assert len(report.exception_list) + recovered_count == report.total_cases

    assert report.precision_metric.precision_score_pct >= 0.0
    assert report.precision_metric.precision_score_pct <= 100.0

    assert os.path.exists(output_json)
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["total_cases"] == report.total_cases
        assert data["gross_recovery_rate_pct"] == report.gross_recovery_rate_pct
