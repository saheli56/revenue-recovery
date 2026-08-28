import pytest
from detector import detect_at_risk_revenue
from models import CaseType

def test_detect_valid_events():
    raw_events = [
        {
            "source_reference": "txn_1",
            "customer_id": "cust_1",
            "amount": 500.0,
            "currency": "INR",
            "case_type": "payment_failure",
            "created_at": "2023-10-01T12:00:00Z",
            "error_code": "insufficient_funds"
        },
        {
            "source_reference": "txn_2",
            "customer_id": "cust_2",
            "amount": 1000.0,
            "currency": "USD", # test other currency
            "case_type": "checkout_abandonment",
            "created_at": "2023-10-02T12:00:00Z",
            "time_since_abandonment_hours": 2
        }
    ]
    
    cases = detect_at_risk_revenue(raw_events)
    assert len(cases) == 2
    
    assert cases[0].source_reference == "txn_1"
    assert cases[0].case_type == CaseType.payment_failure
    assert cases[0].amount == 500.0
    assert "error_code" in cases[0].raw_event_context
    assert cases[0].raw_event_context["error_code"] == "insufficient_funds"
    
    assert cases[1].source_reference == "txn_2"
    assert cases[1].case_type == CaseType.checkout_abandonment
    assert cases[1].amount == 1000.0

def test_detect_skips_invalid():
    raw_events = [
        {
            "source_reference": "txn_1",
            # missing customer_id
            "amount": 500.0,
            "currency": "INR",
            "case_type": "payment_failure",
            "created_at": "2023-10-01T12:00:00Z",
        },
        {
            "source_reference": "txn_2",
            "customer_id": "cust_2",
            "amount": 1000.0,
            "currency": "INR",
            "case_type": "unknown_type", # Invalid enum
            "created_at": "2023-10-02T12:00:00Z"
        }
    ]
    cases = detect_at_risk_revenue(raw_events)
    assert len(cases) == 0 # Both should be skipped
