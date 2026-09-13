"""
Layer 1 — Keyword-based classification.

Priority order matters: insurance -> loan -> investment -> utility ->
subscription -> unknown. Checking risk categories FIRST means an
ambiguous merchant name (e.g. "HDFC" alone) never accidentally falls
into the "safe to cancel" subscription bucket by default.

Confidence rules:
- Exact/near-exact match on a specific keyword -> high confidence (0.95-0.99)
- Single ambiguous fragment (e.g. just a bank name with no category word) -> low confidence
- No match at all -> Unknown, confidence 0.0
"""

import re
from data.mandate_schema import Category
from pipeline.protected_list import normalize_merchant


# Each entry: (keyword, confidence_if_matched)
# More specific / unambiguous keywords get higher confidence.
INSURANCE_KEYWORDS = [
    ("insurance", 0.98), ("life ins", 0.97), ("health ins", 0.97),
    ("premium", 0.85), ("policy", 0.9), ("term plan", 0.95),
]

LOAN_KEYWORDS = [
    ("emi", 0.97), ("loan", 0.95), ("credit card bill", 0.95),
    ("bnpl", 0.9), ("overdraft", 0.9),
]

INVESTMENT_KEYWORDS = [
    ("sip", 0.97), ("mutual fund", 0.97), ("nav", 0.85),
    ("folio", 0.9), ("recurring deposit", 0.95), ("nps", 0.9),
]

UTILITY_KEYWORDS = [
    ("electricity", 0.97), ("water board", 0.95), ("broadband", 0.9),
    ("recharge", 0.8), ("gas board", 0.95), ("power", 0.75),
]

SUBSCRIPTION_KEYWORDS = [
    ("spotify", 0.99), ("netflix", 0.99), ("youtube premium", 0.99),
    ("hotstar", 0.99), ("prime video", 0.99), ("gemini", 0.95),
    ("chatgpt", 0.95), ("claude", 0.95), ("gym", 0.85), ("fitness", 0.8),
    ("news", 0.75), ("cloud storage", 0.85), ("app store", 0.7),
]

# Risk-category priority used ONLY as a tiebreaker when two matches are
# equally specific (same word count) — see classify_layer1 below.
RISK_PRIORITY = {
    Category.INSURANCE: 0,
    Category.LOAN: 1,
    Category.INVESTMENT: 2,
    Category.UTILITY: 3,
    Category.SUBSCRIPTION: 4,
}

CATEGORY_KEYWORD_SETS = [
    (Category.INSURANCE, INSURANCE_KEYWORDS),
    (Category.LOAN, LOAN_KEYWORDS),
    (Category.INVESTMENT, INVESTMENT_KEYWORDS),
    (Category.UTILITY, UTILITY_KEYWORDS),
    (Category.SUBSCRIPTION, SUBSCRIPTION_KEYWORDS),
]

# Flattened once at import time: (category, keyword, confidence).
# Sorted so more specific (longer / multi-word) phrases are checked
# BEFORE generic single-word ones — this stops a generic word like
# "premium" (insurance keyword) from shadowing a more specific match
# like "youtube premium" (subscription keyword). Risk-category priority
# is only used as a tiebreaker between equally-specific matches, so
# genuine ambiguity still favors the safer (risk) category.
_ALL_KEYWORDS = [
    (category, keyword, confidence)
    for category, keywords in CATEGORY_KEYWORD_SETS
    for keyword, confidence in keywords
]
_ALL_KEYWORDS.sort(key=lambda item: (-len(item[1].split()), -item[2], RISK_PRIORITY[item[0]]))


def classify_layer1(merchant_raw: str) -> tuple[Category, float]:
    """
    Returns (category, confidence). If nothing matches, returns
    (Category.UNKNOWN, 0.0) so it falls through to Layer 2.
    """
    normalized = normalize_merchant(merchant_raw)

    for category, keyword, confidence in _ALL_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, normalized):
            return category, confidence

    return Category.UNKNOWN, 0.0
