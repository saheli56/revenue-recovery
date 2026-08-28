import os
import sys
import json
import random
from datetime import datetime, timedelta, timezone

# Add backend to path to import models if needed, but we can just generate JSON for decoupling
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

def generate_dataset(num_records=150):
    records = []
    
    error_codes = [
        "BAD_REQUEST_ERROR",
        "gateway_declined",
        "insufficient_funds",
        "card_expired",
        "issuer_timeout",
        "authentication_failed",
        "fraud_suspected"
    ]
    
    notes = [
        "Customer reported payment failed but money deducted",
        "Bhai payment nahi ho raha",
        "Card expired, need to update",
        "Payment timeout error shown",
        "Customer says: mere paise kat gaye, order nahi aaya",
        "",
        ""
    ]
    
    for i in range(num_records):
        case_type = random.choices(
            ["payment_failure", "checkout_abandonment", "subscription_failure"],
            weights=[0.5, 0.3, 0.2]
        )[0]
        
        record = {
            "source_reference": f"txn_{random.randint(100000, 999999)}",
            "customer_id": f"cust_{random.randint(1000, 9999)}",
            "amount": round(random.uniform(100, 5000), 2),
            "currency": "INR",
            "case_type": case_type,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 10))).isoformat()
        }
        
        if case_type == "payment_failure":
            record["error_code"] = random.choice(error_codes)
            record["customer_note"] = random.choice(notes)
            if record["error_code"] == "fraud_suspected":
                record["should_recover"] = False
            else:
                record["should_recover"] = True
                
        elif case_type == "checkout_abandonment":
            record["time_since_abandonment_hours"] = random.randint(1, 48)
            record["customer_history"] = random.choice(["first_time", "repeat"])
            record["should_recover"] = True
            
        elif case_type == "subscription_failure":
            record["retry_count"] = random.randint(0, 4)
            record["should_recover"] = True if record["retry_count"] < 3 else False
            
        # Add some duplicates or already refunded
        if random.random() < 0.05:
            record["is_already_refunded"] = True
            record["should_recover"] = False
            
        records.append(record)
        
    return records

if __name__ == "__main__":
    data = generate_dataset(150)
    output_path = os.path.join(os.path.dirname(__file__), 'synthetic_data.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} records to {output_path}")
