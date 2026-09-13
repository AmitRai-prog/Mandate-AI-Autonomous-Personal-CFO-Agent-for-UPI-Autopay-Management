"""
Classification pipeline orchestrator.

Flow (exact order matters):
  Protected Merchant? -> YES -> LOCKED (Critical, no further processing)
                       -> NO
  Layer 1 (keywords)  -> confident? -> use it
                       -> not confident -> Layer 2 (LLM)
  Confidence Gate      -> below threshold -> forced to Unknown
  -> final category + confidence + classification_source recorded on the Mandate
"""

from data.mandate_schema import Mandate, Category
from pipeline.protected_list import is_protected, normalize_merchant
from pipeline.layer1_keywords import classify_layer1
from pipeline.layer2_llm import classify_layer2

# Layer 2 (LLM) gets a stricter threshold than Layer 1 (keywords) because
# it's inherently the less reliable / more overconfident classifier.
LAYER1_CONFIDENCE_THRESHOLD = 0.90
LAYER2_CONFIDENCE_THRESHOLD = 0.95


def classify_mandate(mandate: Mandate) -> Mandate:
    """
    Mutates and returns the mandate with classification fields populated:
    merchant_normalized, is_protected, category, category_confidence,
    classification_source.
    """
    mandate.merchant_normalized = normalize_merchant(mandate.merchant_raw)

    # --- Step 1: Protected merchant check — deterministic, runs first, cannot be overridden ---
    if is_protected(mandate.merchant_raw):
        mandate.is_protected = True
        mandate.category = Category.UNKNOWN  # category doesn't matter once locked — risk engine reads is_protected first
        mandate.category_confidence = 1.0
        mandate.classification_source = "protected_list"
        return mandate

    # --- Step 2: Layer 1 keyword match ---
    l1_category, l1_confidence = classify_layer1(mandate.merchant_raw)

    if l1_category != Category.UNKNOWN and l1_confidence >= LAYER1_CONFIDENCE_THRESHOLD:
        mandate.category = l1_category
        mandate.category_confidence = l1_confidence
        mandate.classification_source = "layer1_keyword"
        return mandate

    # --- Step 3: Layer 2 LLM fallback (only reached if Layer 1 wasn't confident) ---
    l2_category, l2_confidence, l2_reason = classify_layer2(
        mandate.merchant_raw, mandate.amount, mandate.frequency.value
    )

    # --- Step 4: Confidence gate ---
    if l2_category != Category.UNKNOWN and l2_confidence >= LAYER2_CONFIDENCE_THRESHOLD:
        mandate.category = l2_category
        mandate.category_confidence = l2_confidence
        mandate.classification_source = "layer2_llm"
    else:
        # Below threshold, or Layer 2 also returned Unknown -> fail closed
        mandate.category = Category.UNKNOWN
        mandate.category_confidence = max(l1_confidence, l2_confidence)
        mandate.classification_source = "layer2_llm" if l2_confidence > 0 else "layer1_keyword"

    return mandate


def classify_all(mandates: list[Mandate]) -> list[Mandate]:
    return [classify_mandate(m) for m in mandates]
