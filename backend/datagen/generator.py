import json
import random
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datagen.config import DatasetDistributionConfig

HINGLISH_CUSTOMER_NOTES = [
    "Paise cut gaye account se par order confirm nahi hua, please check",
    "Card details update karne ka link bhej do payment baar baar fail ho rahi hai",
    "Server timeout ho gaya tha checkout page pe, amount deduct nahi hua",
    "Bhai OTP der se aaya isliye session expire ho gaya tha dobara try karna hai",
    "Mera subscription renew nahi hua card change karna hai",
    "Bank server slow chal raha tha transaction decline ho gaya",
    "Payment debited but showing pending in razorpay gateway, urgently fix",
    "Sir discount code apply nahi ho raha tha isliye cart chhod diya",
    "Card expired ho chuka hai new virtual card accept nahi ho raha",
    "UPI app pe request nahi aayi timeout ho gaya"
]

STANDARD_CUSTOMER_NOTES = [
    "Payment declined by bank with insufficient balance notification",
    "Customer card reached expiry date during renewal cycle",
    "Issuer bank gateway timed out after 3D Secure verification",
    "Customer dropped off at payment method selection step",
    "Recurring subscription mandate renewal failed on primary card"
]

def generate_synthetic_dataset(config: DatasetDistributionConfig = DatasetDistributionConfig()) -> List[Dict[str, Any]]:
    random.seed(config.seed)
    records: List[Dict[str, Any]] = []

    case_types = ["payment_failure", "checkout_abandonment", "subscription_failure"]
    case_weights = [
        config.payment_failure_weight,
        config.checkout_abandonment_weight,
        config.subscription_failure_weight
    ]

    error_codes = list(config.error_code_weights.keys())
    error_weights = list(config.error_code_weights.values())

    base_time = datetime.now(timezone.utc)

    for i in range(1, config.total_records + 1):
        case_type = random.choices(case_types, weights=case_weights, k=1)[0]
        customer_id = f"cust_in_{random.randint(1000, 9999)}"
        source_ref = f"txn_rzp_{i:04d}_{random.randint(10000, 99999)}"
        created_time = base_time - timedelta(hours=random.randint(1, 168), minutes=random.randint(0, 59))

        is_fraud = random.random() < config.fraud_exclusion_rate
        is_refunded = random.random() < config.refund_exclusion_rate
        is_duplicate = random.random() < config.duplicate_exclusion_rate

        has_hinglish = random.random() < config.hinglish_note_rate
        note = random.choice(HINGLISH_CUSTOMER_NOTES) if has_hinglish else random.choice(STANDARD_CUSTOMER_NOTES)

        amount = round(random.choice([499.0, 999.0, 1499.0, 2499.0, 4999.0, 8999.0, 14999.0]) + random.uniform(0.0, 0.99), 2)

        context: Dict[str, Any] = {
            "source_reference": source_ref,
            "customer_id": customer_id,
            "amount": amount,
            "currency": "INR",
            "case_type": case_type,
            "created_at": created_time.isoformat(),
            "customer_note": note,
            "is_fraud_flagged": is_fraud,
            "is_already_refunded": is_refunded,
            "is_duplicate": is_duplicate
        }

        if case_type == "payment_failure":
            selected_error = random.choices(error_codes, weights=error_weights, k=1)[0]
            context.update({
                "error_code": selected_error,
                "gateway": "razorpay_standard",
                "attempt_number": random.randint(1, 2),
                "card_network": random.choice(["Visa", "MasterCard", "RuPay"]),
                "payment_mode": random.choice(["card", "upi", "netbanking"])
            })
        elif case_type == "checkout_abandonment":
            context.update({
                "time_since_abandonment_hours": random.randint(1, 48),
                "customer_history": random.choice(["first_time", "repeat_loyal", "repeat_occasional"]),
                "cart_items_count": random.randint(1, 6),
                "cart_category": random.choice(["electronics", "saas_plan", "fashion", "education"]),
                "device": random.choice(["mobile_android", "mobile_ios", "desktop_chrome"])
            })
        elif case_type == "subscription_failure":
            context.update({
                "subscription_id": f"sub_rzp_{random.randint(1000, 9999)}",
                "plan_name": random.choice(["Starter Monthly", "Pro Annual", "Enterprise Growth"]),
                "retry_count": random.randint(0, 4),
                "last_charge_attempt_at": (created_time - timedelta(days=random.randint(1, 3))).isoformat(),
                "billing_cycle": random.choice(["monthly", "yearly"])
            })

        records.append(context)

    return records

def print_dataset_summary(records: List[Dict[str, Any]]) -> None:
    total = len(records)
    case_type_counts: Dict[str, int] = {}
    error_counts: Dict[str, int] = {}
    fraud_count = 0
    refund_count = 0
    duplicate_count = 0
    hinglish_count = 0
    total_at_risk_val = 0.0

    for r in records:
        ctype = r["case_type"]
        case_type_counts[ctype] = case_type_counts.get(ctype, 0) + 1
        total_at_risk_val += r["amount"]

        if r.get("is_fraud_flagged"):
            fraud_count += 1
        if r.get("is_already_refunded"):
            refund_count += 1
        if r.get("is_duplicate"):
            duplicate_count += 1
        if any(h_word in r.get("customer_note", "") for h_word in ["Paise", "gaye", "Bhai", "karna", "nahi", "raha", "chhod"]):
            hinglish_count += 1

        if "error_code" in r:
            ecode = r["error_code"]
            error_counts[ecode] = error_counts.get(ecode, 0) + 1

    print("\n=======================================================")
    print(f"  SYNTHETIC DATASET GENERATION SUMMARY ({total} RECORDS)")
    print("=======================================================")
    print(f"Total Gross Value at Risk: INR {total_at_risk_val:,.2f}")
    print("\nBreakdown by Case Type:")
    for ctype, count in case_type_counts.items():
        pct = (count / total) * 100
        print(f"  - {ctype:<25}: {count:3d} ({pct:5.1f}%)")

    print("\nBreakdown by Payment Error Codes:")
    for err, count in error_counts.items():
        print(f"  - {err:<25}: {count:3d}")

    print("\nGuardrail Disqualification & Ambiguity Metrics:")
    print(f"  - Fraud Flagged Records  : {fraud_count:3d} (Should be excluded)")
    print(f"  - Already Refunded       : {refund_count:3d} (Should be excluded)")
    print(f"  - Duplicate Records      : {duplicate_count:3d} (Should be excluded)")
    print(f"  - Hinglish Support Notes : {hinglish_count:3d} (Triggers LLM fallback)")
    print("=======================================================\n")

def export_and_print_dataset(output_path: str = None) -> List[Dict[str, Any]]:
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_path = os.path.join(base_dir, "data", "synthetic_batch.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    records = generate_synthetic_dataset()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print_dataset_summary(records)
    print(f"Exported {len(records)} records to {output_path}")
    return records

if __name__ == "__main__":
    export_and_print_dataset()
