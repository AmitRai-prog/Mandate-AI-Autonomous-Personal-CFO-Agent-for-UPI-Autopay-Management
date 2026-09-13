"""
Protected Merchant List.

This is the single most important safety layer in the whole pipeline —
unlike everything downstream, it is NOT probabilistic. If a merchant
normalizes to something on this list, it is locked as CRITICAL risk
before Layer 1 or Layer 2 ever run. No keyword match, no LLM call, no
confidence score can override this.

Keep this list human-editable and easy to extend live during a demo.
"""

import re

# Normalized (lowercase, punctuation-stripped) merchant name fragments.
# Matching is "does this substring appear in the normalized merchant name",
# so partial/legal-suffix variations still hit.
PROTECTED_MERCHANTS = [
    # Insurance
    "lic", "lic of india", "hdfc life", "icici prudential", "icici pru",
    "sbi life", "max life", "bajaj allianz", "tata aig", "star health",
    "care health", "niva bupa", "hdfc ergo",

    # Investment / SIP / Mutual Funds
    "groww", "zerodha", "sip", "mutual fund", "sbi mutual fund",
    "hdfc mutual fund", "icici prudential mf", "axis mutual fund",
    "kuvera", "coin by zerodha", "nps", "national pension",

    # Loans / EMI
    "emi", "personal loan", "home loan", "car loan", "bajaj finserv",
    "credit card bill", "hdfc credit card", "sbi card",
]


def normalize_merchant(raw_name: str) -> str:
    """Lowercase, strip punctuation/extra whitespace for reliable matching."""
    name = raw_name.lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def is_protected(merchant_raw: str) -> bool:
    """
    Returns True if this merchant should be locked as CRITICAL/read-only
    before any classification logic runs.

    Uses word-boundary matching, not raw substring — short keywords like
    "emi" or "sip" would otherwise false-positive inside unrelated words
    (e.g. "emi" is a substring of "premium" and "gemini").
    """
    normalized = normalize_merchant(merchant_raw)
    for protected in PROTECTED_MERCHANTS:
        pattern = r"\b" + re.escape(protected) + r"\b"
        if re.search(pattern, normalized):
            return True
    return False
