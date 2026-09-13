"""
Action Agent — navigates the actual multi-step cancellation flow.

The core design principle: this does NOT hardcode a click sequence like
"click X, then click Y, then click Z." Real bank cancellation flows are
unpredictable — a retention offer might appear, an OTP wall might appear,
neither might appear, or something entirely unexpected might appear. So
every step:
  1. reads what's actually on the page right now
  2. classifies which known state it's in (or flags "unrecognized")
  3. decides the next action based on that state
  4. acts, then loops

If the page doesn't match any known state, the agent STOPS and reports
"blocked" rather than guessing — a wrong guess here could be an
irreversible bank action, so unrecognized state is a hard stop, not a
retry-with-a-different-click situation.

Architecture Guarantee:
All browser lifecycle is strictly managed by SessionManager. No direct
playwright.chromium.launch() or sync_playwright() is invoked here.
"""

from enum import Enum

MAX_STEPS = 8  # hard cap — if we haven't reached a terminal state by then, stop and flag rather than loop forever


class ActionResult(str, Enum):
    CANCELLED = "cancelled"        # reached the success page
    KEPT_BY_RETENTION = "kept_by_retention"  # hit a retention offer and it was accepted (should not happen — we always decline)
    BLOCKED_UNRECOGNIZED = "blocked_unrecognized"  # page didn't match any known state — stopped, needs human
    BLOCKED_MAX_STEPS = "blocked_max_steps"  # too many steps without reaching a terminal state
    ERROR = "error"


def classify_page_state(page) -> str:
    """
    Reads the live page and returns one of: 'manage', 'retention', 'otp',
    'confirm', 'success', 'mandates', 'cancel_start', 'unrecognized'.

    Evaluates terminal and specific flow states FIRST to avoid false
    positives from broad substring collisions (e.g. 'confirm' page text
    contains 'cancel autopay').
    """
    url = page.url.lower()

    # If the Agent Live Flow modal is open on the dashboard, scope text classification to that container
    live_flow = page.locator("#modal-agent-live-flow.open")
    if live_flow.count() > 0:
        text = live_flow.inner_text().lower()
    else:
        text = page.inner_text("body").lower()

    # 1. Success (terminal)
    if "has been cancelled" in text or "autopay cancelled" in text or "page=success" in url:
        return "success"

    # 2. Confirm cancellation (must precede 'manage' because confirm text asks "Are you sure you want to cancel autopay...")
    if "are you sure you want to cancel" in text or "confirm cancellation" in text or "page=confirm" in url:
        return "confirm"

    # 3. Retention offer
    if ("wait" in text and ("3 months free" in text or "before you go" in text)) or "page=retention" in url:
        return "retention"

    # 4. OTP verification
    if "verify it's you" in text or ("otp" in text and "enter the 6-digit" in text) or page.locator("#otp-input:visible").count() > 0 or "page=otp" in url:
        return "otp"

    # 5. Intermediate redirect
    if "page=cancel_start" in url:
        return "cancel_start"

    # 6. Manage mandate
    if "cancel autopay" in text or ("status:" in text and "page=manage" in url):
        return "manage"

    # 7. Mandate list
    if "manage upi autopay" in text or "page=mandates" in url:
        return "mandates"

    return "unrecognized"


def run_step_loop(page, mandate_id: str, base_url: str, demo_mode: bool = False) -> dict:
    """
    The actual perceive-decide-act loop with navigation reliability,
    observable decision highlighting (DEMO_MODE), and step-by-step auditing.

    At each step:
      current URL -> classify state -> available actions -> choose action
      -> execute -> wait -> re-read URL -> re-classify -> record log
    """
    # Import session_manager lazily to avoid circular dependencies
    from pipeline.session_manager import session_manager, AgentState

    log = []

    # Auto-accept any unexpected browser dialogs/alerts so they never block execution
    try:
        page.on("dialog", lambda dialog: dialog.accept())
    except Exception:
        pass

    def wait_for_settled(timeout_ms=5000):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            pass

    def highlight_and_click(btn_locator, action_label: str = ""):
        if demo_mode:
            try:
                btn_locator.evaluate("""el => {
                    el.style.outline = '4px solid #8B5CF6';
                    el.style.boxShadow = '0 0 24px rgba(139, 92, 246, 0.9)';
                    el.style.borderRadius = '8px';
                    el.style.transition = 'all 0.3s ease';
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }""")
                page.wait_for_timeout(1000)
            except Exception:
                pass
        try:
            btn_locator.click(timeout=8000)
        except Exception:
            try:
                btn_locator.evaluate("el => el.click()")
            except Exception:
                btn_locator.click(force=True)

    session_manager.set_state(AgentState.EXECUTING, f"Navigating to manage screen for {mandate_id}", mandate_id)
    session_manager.log_agent_activity(f"Navigating to manage screen for mandate '{mandate_id}'", highlight=True)

    url_lower = page.url.lower()
    base_lower = (base_url or "").lower()

    if "mandate.html" in url_lower or "mandate.html" in base_lower:
        # Open live flow directly inside the user-visible Personal CFO dashboard
        page.evaluate(f"window.openAgentLiveFlow && window.openAgentLiveFlow('{mandate_id}')")
        page.wait_for_timeout(600)
    else:
        page.goto(f"{base_url}?page=manage&id={mandate_id}")
        wait_for_settled()
        if demo_mode:
            page.wait_for_timeout(600)

    for step_num in range(MAX_STEPS):
        # If landed on intermediate redirect page, wait for redirect to settle
        if "page=cancel_start" in page.url.lower():
            page.wait_for_timeout(300)
            wait_for_settled()

        current_url = page.url
        state = classify_page_state(page)

        if state == "manage":
            session_manager.set_state(AgentState.EXECUTING, f"Detected Manage screen — Initiating cancellation", mandate_id)
            session_manager.log_agent_activity("Manage screen loaded — Clicking 'Cancel autopay'")
            if demo_mode:
                page.wait_for_timeout(800)
            available_actions = ["click Cancel autopay", "back to mandates"]
            chosen_action = "click Cancel autopay"
            btn = page.get_by_role("button", name="Cancel autopay")
            if not btn.is_visible():
                btn = page.locator("button:has-text('Cancel autopay')")
            highlight_and_click(btn, chosen_action)

        elif state == "retention":
            session_manager.set_state(AgentState.EXECUTING, f"Retention offer detected — Declining promotional discount", mandate_id)
            session_manager.log_agent_activity("Retention trap detected ('3 months free') — Deliberately declining", highlight=True)
            if demo_mode:
                page.wait_for_timeout(1000)
            available_actions = ["Accept offer, keep autopay", "No thanks, cancel anyway"]
            chosen_action = "decline retention offer (No thanks, cancel anyway)"
            btn = page.get_by_role("button", name="No thanks, cancel anyway")
            if not btn.is_visible():
                btn = page.locator("button:has-text('No thanks, cancel anyway')")
            highlight_and_click(btn, chosen_action)

        elif state == "otp":
            session_manager.set_state(AgentState.EXECUTING, f"OTP Verification challenge detected — Submitting authentication", mandate_id)
            session_manager.log_agent_activity("Two-Factor Auth OTP wall detected — Entering 6-digit verification code", highlight=True)
            if demo_mode:
                page.wait_for_timeout(1000)
            available_actions = ["enter 6-digit OTP", "click Verify button"]
            chosen_action = "enter OTP and click Verify"
            page.locator("#otp-input").fill("123456")
            page.evaluate("() => { const el = document.getElementById('otp-input'); if(el) { el.value = '123456'; el.dispatchEvent(new Event('input')); } }")
            if demo_mode:
                page.wait_for_timeout(600)
            btn = page.get_by_role("button", name="Verify")
            if not btn.is_visible():
                btn = page.locator("button.btn-primary:has-text('Verify')")
            highlight_and_click(btn, chosen_action)

        elif state == "confirm":
            session_manager.set_state(AgentState.EXECUTING, f"Confirmation modal reached — Confirming cancellation intent", mandate_id)
            session_manager.log_agent_activity("Final confirmation dialog reached — Confirming cancellation")
            if demo_mode:
                page.wait_for_timeout(1000)
            available_actions = ["Yes, cancel", "No, go back"]
            chosen_action = "confirm cancellation (Yes, cancel)"
            btn = page.get_by_role("button", name="Yes, cancel")
            if not btn.is_visible():
                btn = page.locator("button:has-text('Yes, cancel')")
            highlight_and_click(btn, chosen_action)

        elif state == "success":
            if demo_mode:
                page.wait_for_timeout(1000)
            available_actions = ["Back to mandates"]
            chosen_action = "terminal state reached (success)"
            session_manager.log_agent_activity(f"Cancellation confirmed by bank portal for '{mandate_id}'", highlight=True)
            step_record = {
                "step": step_num + 1,
                "state": state,
                "action": chosen_action,
                "current_url": current_url,
                "detected_state": state,
                "available_actions": available_actions,
                "chosen_action": chosen_action,
                "resulting_url": current_url,
                "resulting_state": state,
            }
            log.append(step_record)
            session_manager.record_audit_step(step_num + 1, current_url, state, chosen_action, state)
            return {"result": ActionResult.CANCELLED, "log": log}

        elif state == "cancel_start":
            # In flight redirect, wait a moment and re-classify
            page.wait_for_timeout(300)
            wait_for_settled()
            continue

        else:
            available_actions = []
            chosen_action = "STOPPED — unrecognized page state"
            session_manager.set_state(AgentState.FAILED, f"Blocked on unrecognized state: {state}", mandate_id)
            session_manager.log_agent_activity(f"Safety Brake Engaged: Unrecognized page state '{state}' at {current_url}. Stopped blindly clicking.", level="error")
            step_record = {
                "step": step_num + 1,
                "state": state,
                "action": chosen_action,
                "current_url": current_url,
                "detected_state": state,
                "available_actions": available_actions,
                "chosen_action": chosen_action,
                "resulting_url": page.url,
                "resulting_state": classify_page_state(page),
            }
            log.append(step_record)
            session_manager.record_audit_step(step_num + 1, current_url, state, chosen_action, classify_page_state(page))
            return {"result": ActionResult.BLOCKED_UNRECOGNIZED, "log": log}

        # Wait for navigation and allow any instant client redirects to execute
        wait_for_settled()
        if "page=cancel_start" in page.url.lower():
            page.wait_for_timeout(300)
            wait_for_settled()

        resulting_url = page.url
        resulting_state = classify_page_state(page)

        step_record = {
            "step": step_num + 1,
            "state": state,
            "action": chosen_action,
            "current_url": current_url,
            "detected_state": state,
            "available_actions": available_actions,
            "chosen_action": chosen_action,
            "resulting_url": resulting_url,
            "resulting_state": resulting_state,
        }
        log.append(step_record)
        session_manager.record_audit_step(step_num + 1, current_url, state, chosen_action, resulting_state)

    return {"result": ActionResult.BLOCKED_MAX_STEPS, "log": log}


def read_mandate_state(cdp_url: str, base_url: str) -> list:
    """Delegates to session_manager to read current mandate list."""
    from pipeline.session_manager import session_manager
    def _read(page):
        page.goto(f"{base_url}?page=mandates")
        return page.evaluate("() => JSON.parse(localStorage.getItem('bank_mandates') || '[]')")
    return session_manager.execute(lambda: _read(session_manager.get_or_create_page(base_url=base_url)))


def run_cancellation(mandate_id: str, base_url: str, cdp_url: str = None) -> dict:
    """Delegates to session_manager to execute the cancellation loop."""
    from pipeline.session_manager import session_manager
    def _run(page):
        return run_step_loop(page, mandate_id, base_url)
    return session_manager.execute(lambda: _run(session_manager.get_or_create_page(base_url=base_url)))
