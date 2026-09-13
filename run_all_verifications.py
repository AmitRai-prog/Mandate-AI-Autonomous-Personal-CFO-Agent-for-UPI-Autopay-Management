"""
Full End-to-End Verification Suite for Mandate Autonomous Financial Agent.
Validates all items in the Definition of Done.
All browser resources are strictly orchestrated via SessionManager.
"""
import sys

from data.mock_mandates import get_mock_mandates, MOCK_USAGE_INPUT
from data.mandate_schema import RiskLevel, Category
from pipeline.classify import classify_all
from pipeline.risk_engine import apply_risk_levels
from pipeline.reasoning_engine import generate_all
from pipeline.read_mandates import read_mandates_from_dom
from pipeline.action_agent import run_step_loop, ActionResult
from pipeline.verification_agent import verify_cancellation, VerificationStatus
from pipeline.session_manager import session_manager

def verify_pipeline():
    print("\n--- 1. VERIFYING READ & REASON PIPELINE & SAFETY INVARIANTS ---")
    mandates = get_mock_mandates()
    classify_all(mandates)
    apply_risk_levels(mandates)
    generate_all(mandates, MOCK_USAGE_INPUT)

    # Invariant 1: Protected merchants MUST be CRITICAL risk
    for m in mandates:
        if m.is_protected:
            assert m.risk_level == RiskLevel.CRITICAL, f"Protected merchant {m.merchant_raw} must be CRITICAL"
            assert m.recommendation is None, f"Protected merchant {m.merchant_raw} must have no recommendation"
            print(f"[PASS] Invariant 1: {m.merchant_raw} -> CRITICAL (Protected, Read-Only)")

    # Invariant 2: Low-confidence/Ambiguous MUST fail-closed to HIGH risk (unknown)
    m9 = next(x for x in mandates if x.id == "m9")
    assert m9.category == Category.UNKNOWN, f"Ambiguous merchant m9 must be UNKNOWN, got {m9.category}"
    assert m9.risk_level == RiskLevel.HIGH, f"Ambiguous merchant m9 must be HIGH risk, got {m9.risk_level}"
    print(f"[PASS] Invariant 2: {m9.merchant_raw} -> UNKNOWN / HIGH risk (Failed closed)")

    # Invariant 3: Amount > 500 cap escalation
    m10 = next(x for x in mandates if x.id == "m10")
    assert m10.amount > 500, "m10 must be > 500"
    assert m10.risk_level == RiskLevel.MEDIUM, f"m10 must be escalated to MEDIUM risk, got {m10.risk_level}"
    print(f"[PASS] Invariant 3: {m10.merchant_raw} (Rs. {m10.amount}) -> MEDIUM risk (Escalated)")

    # Low risk actionable
    m1 = next(x for x in mandates if x.id == "m1")
    assert m1.risk_level == RiskLevel.LOW, "m1 must be LOW risk"
    assert m1.recommendation == "cancel", "m1 must be recommended to cancel"
    print("[PASS] Low risk actionable: m1 (Spotify unused 47 days) recommended to cancel")


def verify_agent_flow(mandate_id: str, flow_name: str):
    print(f"\n--- 2. VERIFYING AGENT FLOW: {mandate_id} ({flow_name}) ---")
    def _test():
        bank_url = session_manager.get_active_bank_url()
        page = session_manager.get_active_page(headless=True, demo_mode=False)
        target_url = f"{bank_url}?page=mandates"

        # Clean state for isolated verification
        page.goto(target_url)
        try:
            page.evaluate("localStorage.clear()")
            page.goto(target_url)
        except Exception:
            pass

        # Step 1: Read before
        before = read_mandates_from_dom(page, bank_url)
        assert len(before) >= 10, f"Expected at least 10 mandates, got {len(before)}"

        # Step 2: Act
        act_res = run_step_loop(page, mandate_id, bank_url, demo_mode=False)
        print(f"  Action Result: {act_res['result']}")
        assert act_res["result"] == ActionResult.CANCELLED, f"Expected CANCELLED, got {act_res['result']}"
        print(f"  Step Count: {len(act_res['log'])}")
        for step in act_res["log"]:
            print(f"    Step {step.get('step', '-')}: [{step['detected_state']}] -> {step['chosen_action']}")

        # Step 3: Verify
        page.goto(target_url)
        after = read_mandates_from_dom(page, bank_url)
        v_res = verify_cancellation(before, after, mandate_id, act_res["result"])
        print(f"  Verification Status: {v_res['status']}")
        print(f"  Verification Detail: {v_res['detail']}")
        assert v_res["status"] == VerificationStatus.CONFIRMED, f"Expected CONFIRMED, got {v_res['status']}"

    session_manager.execute(_test)
    print(f"[PASS] {mandate_id} ({flow_name}) successfully REACHED VERIFIED!")


if __name__ == "__main__":
    print("===================================================================")
    print(" MANDATE AGENT: COMPLETE DEFINITION OF DONE VALIDATION")
    print("===================================================================")
    try:
        verify_pipeline()
        verify_agent_flow("m1", "Retention Offer Path")
        verify_agent_flow("m10", "OTP Challenge Path")
        verify_agent_flow("m2", "Standard Path")
        print("\n===================================================================")
        print(" ALL DEFINITION OF DONE INVARIANTS SATISFIED & FULLY VERIFIED!")
        print("===================================================================\n")
    finally:
        session_manager.close_session()
