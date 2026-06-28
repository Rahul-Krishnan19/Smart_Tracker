from __future__ import annotations
"""
Standalone eval harness for the Gemini-backed agents.

NOT part of the FastAPI app. Run from the project root:

    cd backend && python evals/run_evals.py
    # or: python backend/evals/run_evals.py

Requires GEMINI_API_KEY in the environment (or backend/.env). If the key is
absent, the LLM-dependent checks simply fail/score 0 rather than crash, which
still exercises the plumbing.

Two suites:
  1. LLM email parser vs. fake bank emails with ground-truth fields.
  2. Categorizer vs. merchant names with expected categories.
"""
import os
import sys
from datetime import date, datetime

# Make `import app...` work whether invoked from project root or backend/.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Best-effort load of backend/.env so GEMINI_API_KEY is available.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
except Exception:
    pass

from app.agents.llm_parser import LLMEmailParser  # noqa: E402
from app.parsers.categorizer import categorize  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
EMAIL_FIXTURES = [
    {
        "name": "Axis UPI debit",
        "email": {
            "sender": "Axis Bank <alerts@axisbank.com>",
            "subject": "Transaction Alert",
            "body": (
                "Dear Customer, INR 250.00 has been debited from your Axis Bank "
                "account XX1234 via UPI to swiggy.food@axis on 2026-06-20. "
                "UPI Ref no 412345678901."
            ),
            "received_at": datetime(2026, 6, 20, 13, 0, 0),
        },
        "expected": {
            "amount": 250.00,
            "merchant_contains": "swiggy",
            "transaction_date": date(2026, 6, 20),
            "payment_method": "UPI",
        },
    },
    {
        "name": "Kotak card spend",
        "email": {
            "sender": "Kotak Bank <noreply@kotak.com>",
            "subject": "Card Transaction",
            "body": (
                "Rs 1,499.00 spent using your Kotak Credit Card ending 8810 at "
                "AMAZON IN on 2026-06-18. Available limit Rs 48,000."
            ),
            "received_at": datetime(2026, 6, 18, 9, 30, 0),
        },
        "expected": {
            "amount": 1499.00,
            "merchant_contains": "amazon",
            "transaction_date": date(2026, 6, 18),
            "payment_method": "Credit Card",
        },
    },
    {
        "name": "Yes Bank debit card",
        "email": {
            "sender": "YES BANK <transaction@yesbank.in>",
            "subject": "Debit Card Transaction Alert",
            "body": (
                "INR 89.00 was debited via your YES BANK Debit Card at "
                "BLINKIT on 2026-06-15. Ref 778899."
            ),
            "received_at": datetime(2026, 6, 15, 18, 5, 0),
        },
        "expected": {
            "amount": 89.00,
            "merchant_contains": "blinkit",
            "transaction_date": date(2026, 6, 15),
            "payment_method": "Debit Card",
        },
    },
    {
        "name": "Promotional (non-transaction)",
        "email": {
            "sender": "Offers <offers@somebank.com>",
            "subject": "You have a pre-approved loan!",
            "body": (
                "Congratulations! You are eligible for a pre-approved personal "
                "loan of up to Rs 5,00,000. Apply now to avail special rates."
            ),
            "received_at": datetime(2026, 6, 10, 11, 0, 0),
        },
        "expected": None,  # parser should return None
    },
]

CATEGORY_FIXTURES = [
    ("Swiggy", "UPI to swiggy.food@axis", "Food & Dining"),
    ("Amazon", "CC purchase at Amazon", "Shopping"),
    ("BESCOM", "Electricity bill payment", "Electricity"),
    ("Uber", "UPI to uber rides", "Transport"),
    ("Apollo Pharmacy", "Medicine purchase", "Healthcare"),
    ("Netflix", "Subscription renewal", "Entertainment"),
    ("BigBasket", "Grocery order", "Groceries"),
]


# ---------------------------------------------------------------------------
# Email parser eval
# ---------------------------------------------------------------------------
def run_email_evals() -> tuple[int, int]:
    print("=" * 70)
    print("EMAIL PARSER EVAL")
    print("=" * 70)
    parser = LLMEmailParser()
    field_pass = 0
    field_total = 0

    for fixture in EMAIL_FIXTURES:
        name = fixture["name"]
        expected = fixture["expected"]
        result = parser.parse(fixture["email"])
        print(f"\n[{name}]")

        if expected is None:
            field_total += 1
            ok = result is None
            field_pass += int(ok)
            print(f"  expected non-transaction (None): {'PASS' if ok else 'FAIL'}"
                  + ("" if ok else f" -> got {result}"))
            continue

        if result is None:
            # All expected fields count as failures.
            for field in expected:
                field_total += 1
                print(f"  {field}: FAIL (parser returned None)")
            continue

        checks = {
            "amount": float(result.amount) == expected["amount"],
            "merchant": expected["merchant_contains"] in (result.merchant or "").lower(),
            "transaction_date": result.transaction_date == expected["transaction_date"],
            "payment_method": result.payment_method == expected["payment_method"],
        }
        for field, ok in checks.items():
            field_total += 1
            field_pass += int(ok)
            detail = ""
            if not ok:
                got = getattr(result, field if field != "merchant" else "merchant")
                detail = f" -> got {got!r}"
            print(f"  {field}: {'PASS' if ok else 'FAIL'}{detail}")

    print(f"\nEmail parser field score: {field_pass}/{field_total}")
    return field_pass, field_total


# ---------------------------------------------------------------------------
# Categorizer eval
# ---------------------------------------------------------------------------
def run_category_evals() -> tuple[int, int]:
    print("\n" + "=" * 70)
    print("CATEGORIZER EVAL")
    print("=" * 70)
    correct = 0
    total = len(CATEGORY_FIXTURES)

    for merchant, description, expected in CATEGORY_FIXTURES:
        got = categorize(merchant, description)
        ok = got == expected
        correct += int(ok)
        print(f"  {merchant:<18} expected={expected:<15} got={got:<15} "
              f"{'PASS' if ok else 'FAIL'}")

    pct = (correct / total * 100) if total else 0.0
    print(f"\nCategorizer accuracy: {correct}/{total} ({pct:.0f}%)")
    return correct, total


def main() -> None:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        print("WARNING: GEMINI_API_KEY not set — LLM-backed checks will score 0.\n")

    email_pass, email_total = run_email_evals()
    cat_pass, cat_total = run_category_evals()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    email_pct = (email_pass / email_total * 100) if email_total else 0.0
    cat_pct = (cat_pass / cat_total * 100) if cat_total else 0.0
    print(f"  {'Suite':<22}{'Score':<12}{'Pct'}")
    print(f"  {'-' * 40}")
    print(f"  {'Email parser fields':<22}{f'{email_pass}/{email_total}':<12}{email_pct:.0f}%")
    print(f"  {'Categorizer':<22}{f'{cat_pass}/{cat_total}':<12}{cat_pct:.0f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
