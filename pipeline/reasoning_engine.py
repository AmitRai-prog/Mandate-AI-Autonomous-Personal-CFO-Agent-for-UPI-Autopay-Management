"""
Evidence / Reasoning / Recommendation Generator powered by Anakin AI.

Operates with strict safety guardrails:
  - Critical risk (Protected merchants: LIC, SIP, Loans, EMIs) are deterministically
    locked as READ-ONLY. Anakin recommendations are ignored if they suggest cancellation.
  - High risk (Utilities, Loans, Insurance, Unclassified) are strictly READ-ONLY.
  - Low and Medium risk subscriptions use Anakin AI reasoning to synthesize evidence,
    redundancy overlaps, annual savings, and recommendation justifications.
"""

from typing import Optional
from data.mandate_schema import Mandate, Category, RiskLevel
from pipeline.risk_engine import monthly_equivalent
from pipeline.anakin_client import AnakinClient

anakin_client = AnakinClient()

OVERLAP_GROUPS = {
    "music_or_video_streaming": ["spotify", "youtube premium", "netflix", "hotstar", "prime video"],
    "ai_assistant": ["gemini", "chatgpt", "claude"],
}

UNUSED_THRESHOLD_DAYS = 30


def _find_overlaps(mandate: Mandate, all_active_normalized_names: set[str]) -> list[str]:
    """Returns names of OTHER active merchants in the same overlap group as this one."""
    normalized = mandate.merchant_normalized or ""
    overlaps = []
    for group_name, members in OVERLAP_GROUPS.items():
        if any(member in normalized for member in members):
            for other_name in all_active_normalized_names:
                if other_name == normalized:
                    continue
                if any(member in other_name for member in members):
                    overlaps.append(other_name)
    return overlaps


def generate_evidence_and_reasoning(
    mandate: Mandate,
    usage_input: dict,
    all_mandates: list[Mandate],
) -> Mandate:
    """
    Populates mandate.evidence, mandate.reasoning, mandate.recommendation.
    Safety invariants are strictly enforced before any recommendation is rendered.
    """
    # --- 1. CRITICAL RISK (Protected Merchants) — Deterministic, Anakin can NEVER touch ---
    if mandate.risk_level == RiskLevel.CRITICAL or mandate.is_protected:
        mandate.evidence = {
            "merchant": mandate.merchant_raw,
            "amount": mandate.amount,
            "frequency": mandate.frequency.value,
        }
        mandate.reasoning = ["Protected financial merchant — locked by policy before classification. Never eligible for any action."]
        mandate.recommendation = None
        return mandate

    # --- 2. HIGH RISK (Loans, Insurance, Utilities, Unknown) — Strict Read-Only ---
    if mandate.risk_level == RiskLevel.HIGH:
        mandate.evidence = {
            "merchant": mandate.merchant_raw,
            "amount": mandate.amount,
            "frequency": mandate.frequency.value,
            "category": mandate.category.value if mandate.category else "unknown",
            "confidence": mandate.category_confidence or 0.0,
        }
        if mandate.category == Category.UNKNOWN:
            mandate.reasoning = ["Could not classify with sufficient confidence — shown read-only, no automated action allowed."]
        else:
            mandate.reasoning = [f"Classified as {mandate.category.value} — essential/contractual spend, read-only by policy."]
        mandate.recommendation = None
        return mandate

    # --- 3. LOW & MEDIUM RISK (Subscriptions) — Anakin AI Reasoning Synthesis ---
    active_names = {
        m.merchant_normalized for m in all_mandates
        if m.merchant_normalized and m.category == Category.SUBSCRIPTION
    }
    overlaps = _find_overlaps(mandate, active_names)
    usage = usage_input.get(mandate.id, {})
    last_used_days = usage.get("last_used_days_ago")
    monthly_cost = monthly_equivalent(mandate)

    # Invoke Anakin reasoning synthesis
    synth = anakin_client.synthesize_reasoning(
        merchant_raw=mandate.merchant_raw,
        amount=mandate.amount,
        frequency=mandate.frequency.value,
        usage_days=last_used_days,
        overlaps=overlaps,
        monthly_cost=monthly_cost,
    )

    mandate.evidence = {
        "merchant": mandate.merchant_raw,
        "amount": mandate.amount,
        "frequency": mandate.frequency.value,
        "category": mandate.category.value,
        "confidence": mandate.category_confidence,
        "usage_days_ago": last_used_days,
        "overlaps": overlaps,
        "annual_cost_inr": synth["savings_annual"],
    }

    reasoning = synth["reasoning"]

    # Amount escalation constraint (₹500/month cap)
    if mandate.risk_level == RiskLevel.MEDIUM:
        reasoning.append("High value subscription (> Rs. 500/mo) — recommend-only; automated one-tap cancel disabled by policy")
        mandate.recommendation = "cancel" if synth["recommendation"] == "cancel" else "keep"
    else:
        mandate.recommendation = synth["recommendation"]

    mandate.reasoning = reasoning
    return mandate


def generate_all(mandates: list[Mandate], usage_input: dict) -> list[Mandate]:
    for m in mandates:
        generate_evidence_and_reasoning(m, usage_input, mandates)
    return mandates
