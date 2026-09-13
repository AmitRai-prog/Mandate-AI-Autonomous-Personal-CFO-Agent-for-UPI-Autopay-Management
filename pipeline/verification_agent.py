"""
Verification Agent.

Deliberately distrustful: the Action Agent reporting ActionResult.CANCELLED
means "I clicked through to a page that said success" — it does NOT mean
the mandate is actually gone. Bank UIs lie, lag, or show a success page
that doesn't reflect the real backend state. This module independently
re-reads the mandate list (a fresh scrape, not reusing the action agent's
page object) and compares before/after state to determine the real outcome.
"""

from enum import Enum
from pipeline.action_agent import ActionResult


class VerificationStatus(str, Enum):
    CONFIRMED = "confirmed"        # re-read shows status actually changed to cancelled
    FAILED = "failed"              # re-read shows status unchanged — action did not take effect
    BLOCKED_ON_AUTH = "blocked_on_auth"  # action agent hit an OTP/auth wall it couldn't clear
    PENDING = "pending"            # ambiguous — e.g. site shows "processing", needs a follow-up check
    UNKNOWN = "unknown"            # couldn't determine — always routes back to the user, never retried blindly


def verify_cancellation(before_mandates: list, after_mandates: list, mandate_id: str, action_result: str) -> dict:
    """
    before_mandates / after_mandates: lists of {id, status, ...} dicts,
    each independently read (before = prior to action, after = fresh
    re-scrape following the action agent's run).

    Returns {"status": VerificationStatus, "detail": str}.
    """
    before = next((m for m in before_mandates if m["id"] == mandate_id), None)
    # Correlate by id, or match by merchant name from the before record
    after = next(
        (m for m in after_mandates if m["id"] == mandate_id or (before and m.get("merchant") == before.get("merchant"))),
        None
    )

    if action_result == ActionResult.BLOCKED_UNRECOGNIZED:
        return {"status": VerificationStatus.UNKNOWN,
                "detail": "Action agent hit an unrecognized page state and stopped before completing. No click was made blindly."}

    if action_result in (ActionResult.BLOCKED_MAX_STEPS, ActionResult.ERROR):
        return {"status": VerificationStatus.FAILED,
                "detail": f"Action agent halted before reaching terminal state ({action_result}). Cancellation not achieved."}

    if after is None:
        # Mandate disappeared from the list entirely rather than showing
        # status=cancelled — plausible on a real bank, worth its own state
        # rather than silently treating as success.
        return {"status": VerificationStatus.CONFIRMED,
                "detail": "Mandate no longer appears in the active mandate list."}

    if after["status"] == "cancelled" and (before is None or before["status"] == "active"):
        return {"status": VerificationStatus.CONFIRMED,
                "detail": "Re-read confirms status changed from active to cancelled."}

    if after["status"] == "active":
        if action_result == ActionResult.CANCELLED:
            # Action agent reported success, but the independent re-read
            # disagrees — treat the re-read as ground truth, not the
            # action agent's own claim.
            return {"status": VerificationStatus.FAILED,
                    "detail": "Action agent reported success, but mandate still shows active on re-read. Do not retry automatically — flag for the user."}
        return {"status": VerificationStatus.FAILED,
                "detail": "Mandate still active — cancellation did not take effect."}

    if after["status"] == "pending" or after["status"] == "processing":
        return {"status": VerificationStatus.PENDING,
                "detail": "Bank shows the cancellation as processing — recheck in a few minutes rather than retrying the action."}

    return {"status": VerificationStatus.UNKNOWN,
            "detail": f"Unrecognized status value on re-read: {after.get('status')!r}."}
