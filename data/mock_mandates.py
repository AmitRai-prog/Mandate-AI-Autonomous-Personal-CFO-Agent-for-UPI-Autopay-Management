"""
Mock mandate data — comprehensive dataset representing real-world netbanking auto-debits.
Encompasses all asset classes:
  - Discretionary Subscriptions (Low Risk: cancel vs keep)
  - Statutory Life & Health Insurance (Critical Risk: permanently protected)
  - Wealth Systematic Investment Plans / Mutual Funds (Critical Risk: permanently protected)
  - Contractual Debt / Loan EMIs (Critical Risk: permanently protected)
  - Essential Utilities / Broadband (High Risk: read-only by policy)
  - Ambiguous Merchant Names (High Risk: confidence gated to unknown)
  - High-Value Subscriptions (Medium Risk: amount escalated cap)
"""

from datetime import date
from .mandate_schema import Mandate, Frequency, MandateStatus


def get_mock_mandates() -> list[Mandate]:
    return [
        # --- 1. Low risk cancel-eligible subscription ---
        Mandate(
            id="m1",
            merchant_raw="SPOTIFY INDIA",
            amount=299,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 10),
            status=MandateStatus.ACTIVE,
        ),
        # --- 2. Low risk active subscription (retain) ---
        Mandate(
            id="m2",
            merchant_raw="GOOGLE *YouTube Premium",
            amount=149,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 15),
            status=MandateStatus.ACTIVE,
        ),
        # --- 3. Low risk active productivity AI (retain) ---
        Mandate(
            id="m3",
            merchant_raw="Google Gemini Advanced",
            amount=1950,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 11),
            status=MandateStatus.ACTIVE,
        ),
        # --- 4. Critical Risk: Statutory Life Insurance (Protected) ---
        Mandate(
            id="m4",
            merchant_raw="LIC OF INDIA PREMIUM",
            amount=12450,
            frequency=Frequency.ANNUALLY,
            next_debit_date=date(2027, 3, 1),
            status=MandateStatus.ACTIVE,
        ),
        # --- 5. Critical Risk: Wealth Compounding SIP (Protected) ---
        Mandate(
            id="m5",
            merchant_raw="GROWW SIP - NIFTY 50 INDEX",
            amount=5000,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 5),
            status=MandateStatus.ACTIVE,
        ),
        # --- 6. Critical Risk: Health & Term Cover (Protected via keyword) ---
        Mandate(
            id="m6",
            merchant_raw="ICICI PRU LIFE INS PREM",
            amount=8200,
            frequency=Frequency.ANNUALLY,
            next_debit_date=date(2027, 1, 20),
            status=MandateStatus.ACTIVE,
        ),
        # --- 7. Critical Risk: Contractual Loan EMI (Protected) ---
        Mandate(
            id="m7",
            merchant_raw="HDFC BANK EMI - PERSONAL LOAN",
            amount=18500,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 7),
            status=MandateStatus.ACTIVE,
        ),
        # --- 8. High Risk: Essential Municipal Utility (Read-Only) ---
        Mandate(
            id="m8",
            merchant_raw="BESCOM ELECTRICITY AUTOPAY",
            amount=2150,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 12),
            status=MandateStatus.ACTIVE,
        ),
        # --- 9. High Risk: Ambiguous Merchant without product (Confidence Gated) ---
        Mandate(
            id="m9",
            merchant_raw="HDFC",
            amount=2500,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 18),
            status=MandateStatus.ACTIVE,
        ),
        # --- 10. Medium Risk: High-Value Subscription (Amount Escalated > Rs 500) ---
        Mandate(
            id="m10",
            merchant_raw="Netflix Premium 4K Family Plan",
            amount=649,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 9),
            status=MandateStatus.ACTIVE,
        ),
        # --- 11. Low Risk: Active AI Developer Subscription (Retain) ---
        Mandate(
            id="m11",
            merchant_raw="OpenAI *ChatGPT Plus",
            amount=1999,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 21),
            status=MandateStatus.ACTIVE,
        ),
        # --- 12. Low Risk: Active Amazon Prime (Retain) ---
        Mandate(
            id="m12",
            merchant_raw="Amazon Prime Annual",
            amount=1499,
            frequency=Frequency.ANNUALLY,
            next_debit_date=date(2027, 2, 14),
            status=MandateStatus.ACTIVE,
        ),
        # --- 13. Low Risk: Unused OTT Entertainment (Cancel) ---
        Mandate(
            id="m13",
            merchant_raw="Disney+ Hotstar Super",
            amount=899,
            frequency=Frequency.ANNUALLY,
            next_debit_date=date(2026, 11, 28),
            status=MandateStatus.ACTIVE,
        ),
        # --- 14. Low Risk: Active Coding Assistant (Retain) ---
        Mandate(
            id="m14",
            merchant_raw="Anthropic *Claude Pro",
            amount=1999,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 25),
            status=MandateStatus.ACTIVE,
        ),
        # --- 15. Critical Risk: Mutual Fund SIP (Protected) ---
        Mandate(
            id="m15",
            merchant_raw="Zerodha Coin SIP - Large Cap",
            amount=3000,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 8),
            status=MandateStatus.ACTIVE,
        ),
        # --- 16. Critical Risk: Vehicle Loan EMI (Protected) ---
        Mandate(
            id="m16",
            merchant_raw="SBI Vehicle Loan EMI",
            amount=14200,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 10),
            status=MandateStatus.ACTIVE,
        ),
        # --- 17. High Risk: Broadband Internet (Read-Only) ---
        Mandate(
            id="m17",
            merchant_raw="ACT Fibernet Broadband",
            amount=1179,
            frequency=Frequency.MONTHLY,
            next_debit_date=date(2026, 9, 16),
            status=MandateStatus.ACTIVE,
        ),
    ]


# Self-reported usage telemetry for subscription reasoning
MOCK_USAGE_INPUT = {
    "m1": {"last_used_days_ago": 47},   # Spotify — unused (Cancel)
    "m2": {"last_used_days_ago": 1},    # YT Premium — active user (Keep)
    "m3": {"last_used_days_ago": 2},    # Gemini — active user (Keep)
    "m10": {"last_used_days_ago": 90},  # Netflix — unused, amount escalated
    "m11": {"last_used_days_ago": 3},   # ChatGPT Plus — active user (Keep)
    "m12": {"last_used_days_ago": 5},   # Amazon Prime — active user (Keep)
    "m13": {"last_used_days_ago": 42},  # Disney+ Hotstar — unused (Cancel)
    "m14": {"last_used_days_ago": 2},   # Claude Pro — active user (Keep)
}
