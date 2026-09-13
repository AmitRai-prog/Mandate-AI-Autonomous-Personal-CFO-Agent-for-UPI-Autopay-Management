"""
Risk level engine.

Risk level = f(is_protected, category, confidence, amount) — NOT a
second independent classification. This prevents the risk level from
ever disagreeing with the category in a way that could open a safety
gap (e.g. something categorized as insurance somehow ending up "Low" risk).

Amount escalation: a large-value "subscription" (e.g. a ₹6,499/month
plan) does not get Low/auto-cancel-eligible status just because its
category matched — high value can only ever push risk UP, never down.
"""

from data.mandate_schema import Mandate, Category, RiskLevel, Frequency

# Monthly-equivalent amount above which a subscription is downgraded
# from auto-cancel-eligible (Low) to recommend-only (Medium), regardless
# of classification confidence.
SUBSCRIPTION_AUTO_CANCEL_CAP_MONTHLY = 500.0

_FREQUENCY_TO_MONTHLY_MULTIPLIER = {
    Frequency.WEEKLY: 4.33,
    Frequency.MONTHLY: 1.0,
    Frequency.QUARTERLY: 1 / 3,
    Frequency.ANNUALLY: 1 / 12,
    Frequency.UNKNOWN: 1.0,  # conservative: treat unknown frequency as monthly (worst case for the cap check)
}


def monthly_equivalent(mandate: Mandate) -> float:
    multiplier = _FREQUENCY_TO_MONTHLY_MULTIPLIER[mandate.frequency]
    return mandate.amount * multiplier


def compute_risk_level(mandate: Mandate) -> RiskLevel:
    if mandate.is_protected:
        return RiskLevel.CRITICAL

    if mandate.category in (Category.INSURANCE, Category.LOAN, Category.INVESTMENT, Category.UTILITY):
        return RiskLevel.HIGH

    if mandate.category == Category.UNKNOWN:
        # Fail closed: unclassified mandates are never actionable.
        return RiskLevel.HIGH

    if mandate.category == Category.SUBSCRIPTION:
        if monthly_equivalent(mandate) > SUBSCRIPTION_AUTO_CANCEL_CAP_MONTHLY:
            return RiskLevel.MEDIUM  # correctly-categorized subscription, but too high-value to one-tap cancel
        return RiskLevel.LOW

    # Should be unreachable given the enum, but fail closed if it ever is.
    return RiskLevel.HIGH


def apply_risk_levels(mandates: list[Mandate]) -> list[Mandate]:
    for m in mandates:
        m.risk_level = compute_risk_level(m)
    return mandates
