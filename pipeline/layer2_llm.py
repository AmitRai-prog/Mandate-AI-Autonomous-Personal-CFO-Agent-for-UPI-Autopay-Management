"""
Layer 2 — Anakin-Powered Fallback Classification.

Only invoked when Layer 1 keyword matching does not produce high confidence.
Uses Anakin's intelligence platform to classify recurring payees into:
  - insurance
  - loan
  - investment
  - utility
  - subscription
  - unknown

Safety Invariants (Strict):
  - Never guess.
  - If ambiguous, generic, or uncertain: return Category.UNKNOWN with low confidence.
  - Fail closed on any exception.
"""

import os
from data.mandate_schema import Category
from pipeline.anakin_client import AnakinClient

anakin_client = AnakinClient()


def classify_layer2(
    merchant_raw: str,
    amount: float,
    frequency: str,
    context: str = None
) -> tuple[Category, float, str]:
    """
    Returns (Category, confidence_float_0_to_1, reasoning_str).
    Falls back closed to (Category.UNKNOWN, 0.0, "...") on any uncertainty or failure.
    """
    try:
        res = anakin_client.classify_merchant(
            merchant_raw=merchant_raw,
            amount=amount,
            frequency=frequency,
            context=context
        )

        category_str = res.get("category", "unknown").lower()
        confidence = float(res.get("confidence", 0.0))
        # Support 0-100 scale normalization if returned as percentage
        if confidence > 1.0:
            confidence = confidence / 100.0

        reasoning = res.get("reasoning", "")

        try:
            cat_enum = Category(category_str)
        except ValueError:
            cat_enum = Category.UNKNOWN

        return cat_enum, confidence, reasoning

    except Exception as e:
        # Strict fail-closed policy
        return Category.UNKNOWN, 0.0, f"Anakin classification error, safely defaulted to unknown: {e}"
