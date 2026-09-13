"""
Mandate data structure.

This shape is deliberately designed to match what we'll eventually ask
Anakin's Browser Sessions API to extract from a real netbanking mandate
page (via `generateJson: true` + this same schema). Building against this
shape now means Step 5 (live data) is a drop-in replacement for the mock
data source in Step 1 — nothing downstream (classification, risk, UI)
needs to change.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Frequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    WEEKLY = "weekly"
    UNKNOWN = "unknown"


class MandateStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class Category(str, Enum):
    SUBSCRIPTION = "subscription"
    INVESTMENT = "investment"
    INSURANCE = "insurance"
    LOAN = "loan"
    UTILITY = "utility"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    CRITICAL = "critical"   # protected merchant — never touch
    HIGH = "high"            # read-only
    MEDIUM = "medium"        # recommend only, no auto-cancel
    LOW = "low"              # cancellation allowed (with confirmation)


@dataclass
class Mandate:
    """
    A single recurring-payment mandate, as read from a netbanking mandate
    page (or, for now, mock data shaped identically).
    """
    id: str
    merchant_raw: str              # exact string as shown on the bank page, e.g. "SPOTIFY INDIA"
    amount: float
    currency: str = "INR"
    frequency: Frequency = Frequency.UNKNOWN
    next_debit_date: Optional[date] = None
    status: MandateStatus = MandateStatus.ACTIVE
    source: str = "netbanking"     # "netbanking" | "upi_app" (for later UPI support)
    raw_snippet: Optional[str] = None  # the raw text/markdown this was extracted from — kept for traceability/debugging

    # ---- fields populated by the pipeline (Steps 2-3), not by the data source ----
    merchant_normalized: Optional[str] = None
    is_protected: bool = False
    category: Optional[Category] = None
    category_confidence: Optional[float] = None   # 0.0 - 1.0
    classification_source: Optional[str] = None    # "protected_list" | "layer1_keyword" | "layer2_llm"
    risk_level: Optional[RiskLevel] = None
    evidence: dict = field(default_factory=dict)
    reasoning: list[str] = field(default_factory=list)
    recommendation: Optional[str] = None            # "cancel" | "keep" | None


# This is the JSON schema we'll eventually pass to Anakin's URL Scraper /
# Browser Sessions API with generateJson=True, so live extraction returns
# data shaped exactly like the fields above (before pipeline enrichment).
ANAKIN_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "mandates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "merchant_raw": {"type": "string", "description": "Merchant/payee name exactly as shown on the mandate page"},
                    "amount": {"type": "number", "description": "Debit amount in INR"},
                    "frequency": {"type": "string", "enum": ["monthly", "quarterly", "annually", "weekly", "unknown"]},
                    "next_debit_date": {"type": "string", "description": "ISO date YYYY-MM-DD if shown"},
                    "status": {"type": "string", "enum": ["active", "paused", "cancelled"]},
                },
                "required": ["merchant_raw", "amount"],
            },
        }
    },
    "required": ["mandates"],
}
