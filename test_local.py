"""
Run the full action + verification loop against your deployed mock bank,
using a plain local Playwright browser — no Anakin API key needed for
this. This proves the agent's actual decision-making works before you
add Anakin's session layer on top.

Setup (run once):
    pip install playwright
    playwright install chromium

Usage:
    python test_local.py https://your-mock-bank.vercel.app m1
    python test_local.py https://your-mock-bank.vercel.app m10

Try m1 (Spotify — hits a retention offer) and m10 (Netflix — hits an
OTP wall) to see the agent handle both branches. Try m2 for the
straightforward path with neither.
"""

import sys
from pipeline.action_agent import run_step_loop
from pipeline.read_mandates import read_mandates_from_dom
from pipeline.verification_agent import verify_cancellation
from pipeline.session_manager import session_manager


def main():
    if len(sys.argv) >= 3:
        base_url = sys.argv[1].rstrip("/")
        mandate_id = sys.argv[2]
    elif len(sys.argv) == 2 and not sys.argv[1].startswith("--"):
        base_url = session_manager.get_active_bank_url()
        mandate_id = sys.argv[1]
    else:
        base_url = session_manager.get_active_bank_url()
        mandate_id = "m1"

    headless = "--headless" in sys.argv or "--headful" not in sys.argv
    demo_mode = "--demo" in sys.argv or "--headful" in sys.argv

    # 1. Connect and initialize primary authenticated bank session
    session_manager.connect_bank_session(
        bank_name="Demo Bank",
        base_url=base_url,
        headless=headless,
        demo_mode=demo_mode
    )

    print(f"\n========================================================")
    print(f" READ -> REASON -> ACT -> VERIFY AUTONOMOUS AGENT RUN")
    print(f" Target Mandate: {mandate_id} | Base URL: {base_url}")
    print(f" Demo Mode:     {'ENABLED (slow_mo=1000ms, decision highlights)' if demo_mode else 'DISABLED'}")
    print(f" Session:       REUSED AUTHENTICATED BANK CONTEXT")
    print(f"========================================================")

    def _execute():
        # Retrieve primary authenticated page (reusing open page/context)
        page = session_manager.get_or_create_page(base_url=base_url, headless=headless, demo_mode=demo_mode)

        print(f"\n[1. READ] Reading initial mandate list from {base_url}...")
        before = read_mandates_from_dom(page, base_url)
        target_before = next((m for m in before if m["id"] == mandate_id or m["merchant"].lower() == mandate_id.lower()), None)
        for m in before:
            marker = " -> [TARGET]" if m == target_before else ""
            print(f"  {m['id']:>6}  {m['merchant']:<38} {m['status']:<10}{marker}")

        print(f"\n[2. ACT] Autonomous action agent executing cancellation for {mandate_id}...")
        action_result = run_step_loop(page, mandate_id, base_url, demo_mode=demo_mode)
        print(f"  Action Result: {action_result['result']}")
        print(f"\n  --- STEP AUDIT LOG ---")
        for step in action_result["log"]:
            step_num = step.get("step", "-")
            url = step.get("current_url", "")
            state = step.get("detected_state", step.get("state"))
            actions = ", ".join(step.get("available_actions", []))
            chosen = step.get("chosen_action", step.get("action"))
            res_url = step.get("resulting_url", "")
            res_state = step.get("resulting_state", "")
            print(f"  Step {step_num}:")
            print(f"    URL:             {url}")
            print(f"    Detected State:  {state}")
            print(f"    Available Acts:  [{actions}]")
            print(f"    Chosen Action:   {chosen}")
            print(f"    Resulting URL:   {res_url}")
            print(f"    Resulting State: {res_state}")

        print(f"\n[3. VERIFY] Verification agent independently re-reading DOM...")
        # Fresh verification page inside authenticated session (preserves primary page view)
        verify_page = session_manager.get_verification_page(base_url)
        after = read_mandates_from_dom(verify_page, base_url)
        try:
            verify_page.close()
        except Exception:
            pass
        target_after = next((m for m in after if m["id"] == mandate_id or (target_before and m["merchant"] == target_before["merchant"])), None)
        for m in after:
            marker = " -> [TARGET]" if m == target_after else ""
            print(f"  {m['id']:>6}  {m['merchant']:<38} {m['status']:<10}{marker}")

        verification = verify_cancellation(before, after, mandate_id, action_result["result"])
        return action_result, verification

    action_result, verification = session_manager.execute(_execute)

    print(f"\n[4. OUTCOME]")
    print(f"  ActionResult:       {action_result['result']}")
    print(f"  VerificationStatus: {verification['status']}")
    print(f"  VerificationDetail: {verification['detail']}")

    session_manager.close_session()


if __name__ == "__main__":
    main()
