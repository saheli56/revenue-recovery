import pytest
import uuid
import httpx
from httpx import ASGITransport
from main import app
from config import settings

@pytest.mark.asyncio
async def test_api_health_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data

@pytest.mark.asyncio
async def test_api_ingest_and_list_cases():
    test_run_id = uuid.uuid4().hex[:6]
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "case_type": "payment_failure",
            "source_reference": f"txn_api_{test_run_id}",
            "customer_id": f"cust_api_{test_run_id}",
            "amount": 2499.0,
            "currency": "INR",
            "auto_process": True,
            "metadata": {"error_code": "insufficient_funds"}
        }
        ingest_res = await client.post("/api/v1/cases/ingest", json=payload)
        assert ingest_res.status_code == 201
        ingest_data = ingest_res.json()
        case_id = ingest_data["id"]
        assert ingest_data["source_reference"] == f"txn_api_{test_run_id}"

        get_res = await client.get(f"/api/v1/cases/{case_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == case_id

        list_res = await client.get(f"/api/v1/cases?search={test_run_id}")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert any(c["id"] == case_id for c in list_data["items"])

        trace_res = await client.get(f"/api/v1/cases/{case_id}/trace")
        assert trace_res.status_code == 200
        trace_data = trace_res.json()
        assert "case" in trace_data
        assert "audit_logs" in trace_data
        assert len(trace_data["audit_logs"]) >= 2

@pytest.mark.asyncio
async def test_api_analytics_endpoints():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        summary_res = await client.get("/api/v1/analytics/summary")
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert "total_cases" in summary_data
        assert "gross_recovery_rate_pct" in summary_data
        assert "net_recovered_amount" in summary_data

        breakdown_res = await client.get("/api/v1/analytics/breakdown")
        assert breakdown_res.status_code == 200
        breakdown_data = breakdown_res.json()
        assert "case_type_breakdown" in breakdown_data
        assert "root_cause_breakdown" in breakdown_data
        assert "exception_list" in breakdown_data

@pytest.mark.asyncio
async def test_api_policies_and_guardrails():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        policies_res = await client.get("/api/v1/policies")
        assert policies_res.status_code == 200
        policies_data = policies_res.json()
        assert policies_data["total_rules"] >= 12

        status_res = await client.get("/api/v1/guardrails/status")
        assert status_res.status_code == 200
        assert "kill_switch_active" in status_res.json()

        toggle_res = await client.post("/api/v1/guardrails/kill-switch", json={"kill_switch_active": True})
        assert toggle_res.status_code == 200
        assert toggle_res.json()["kill_switch_active"] is True

        reset_res = await client.post("/api/v1/guardrails/kill-switch", json={"kill_switch_active": False})
        assert reset_res.status_code == 200
        assert reset_res.json()["kill_switch_active"] is False
