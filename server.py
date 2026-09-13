"""
FastAPI Backend Server & Bridge for Mandate Personal CFO Agent.

Implements:
  - Central Agent State Machine & Real-Time SSE Stream (/api/events)
  - Dual-Tab Live Agent Workspace (Dashboard Tab + Bank Execution Tab)
  - Single-session ownership with SessionManager (server and watch mode share exact same session)
  - Canonical REST endpoints & strict safety invariants:
      GET  /mandates, GET /api/mandates
      POST /cancel, POST /api/cancel
      POST /api/watch
      GET  /api/agent/state
      GET  /api/history
      GET  /session/status
"""

import os
import sys
import time
import json
import queue
import logging
import asyncio
import threading
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from data.mandate_schema import RiskLevel, MandateStatus
from data.mock_mandates import get_mock_mandates, MOCK_USAGE_INPUT
from pipeline.classify import classify_all
from pipeline.risk_engine import apply_risk_levels, monthly_equivalent
from pipeline.reasoning_engine import generate_all
from pipeline.read_mandates import read_mandates_from_dom
from pipeline.action_agent import run_step_loop, ActionResult
from pipeline.verification_agent import verify_cancellation, VerificationStatus
from pipeline.session_manager import session_manager, AgentState

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MANDATE-SERVER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mandate_server")

app = FastAPI(
    title="Mandate Personal CFO Agent API",
    description="Safety-first autonomous financial agent with READ -> REASON -> ACT -> VERIFY pipeline.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_BANK_URL = session_manager.get_active_dashboard_url()
DASHBOARD_URL = session_manager.get_active_dashboard_url()


def get_enriched_mandates():
    """Runs the full READ -> REASON pipeline and applies dynamic cancellation states."""
    cancelled = session_manager.get_cancelled_mandates()
    mandates = get_mock_mandates()
    classify_all(mandates)
    apply_risk_levels(mandates)
    generate_all(mandates, MOCK_USAGE_INPUT)

    # Dynamic status sync: reflect cancelled mandates
    for m in mandates:
        if m.id in cancelled:
            m.status = MandateStatus.CANCELLED
            m.recommendation = None
            if m.reasoning:
                m.reasoning = ["Subscription has been cancelled and independently verified with live bank records."]

    return mandates


class CancelRequest(BaseModel):
    mandate_id: str
    base_url: Optional[str] = DEFAULT_BANK_URL
    headless: Optional[bool] = False
    force_medium: Optional[bool] = False
    demo_mode: Optional[bool] = True


class SessionConnectRequest(BaseModel):
    bank_name: Optional[str] = "Demo Bank"
    base_url: Optional[str] = DEFAULT_BANK_URL
    headless: Optional[bool] = False
    demo_mode: Optional[bool] = True


def format_mandates_response():
    mandates = get_enriched_mandates()
    results = []
    total_potential_savings = 0.0

    for m in mandates:
        annual_cost = monthly_equivalent(m) * 12
        if m.recommendation == "cancel" and m.status != MandateStatus.CANCELLED:
            total_potential_savings += annual_cost

        results.append({
            "id": m.id,
            "merchant": m.merchant_raw,
            "merchant_normalized": m.merchant_normalized,
            "amount": m.amount,
            "currency": m.currency,
            "frequency": m.frequency.value,
            "annual_cost": round(annual_cost, 2),
            "next_debit_date": m.next_debit_date.isoformat() if m.next_debit_date else None,
            "status": m.status.value,
            "is_protected": m.is_protected,
            "category": m.category.value if m.category else None,
            "category_confidence": m.category_confidence,
            "classification_source": m.classification_source,
            "risk_level": m.risk_level.value if m.risk_level else None,
            "evidence": m.evidence,
            "reasoning": m.reasoning,
            "recommendation": m.recommendation,
        })

    return {
        "mandates": results,
        "potential_savings": round(total_potential_savings, 2),
        "agent_state": session_manager.get_state()
    }


def execute_cancellation_pipeline(mandate_id: str, base_url: str = DEFAULT_BANK_URL,
                                  headless: bool = False, demo_mode: bool = True) -> Dict[str, Any]:
    """
    Executes the cancellation workflow inside Tab 2 (Live Agent Workspace)
    while Tab 1 (Dashboard) stays open and updates live via SSE.
    """
    base_url = base_url.rstrip("/")
    mandates = get_enriched_mandates()
    target = next((m for m in mandates if m.id == mandate_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Mandate '{mandate_id}' not found.")

    # Strict Safety Checks
    if target.risk_level == RiskLevel.CRITICAL or target.is_protected:
        session_manager.set_state(AgentState.FAILED, f"Safety violation: '{target.merchant_raw}' is protected", mandate_id)
        session_manager.log_agent_activity(f"Safety Violation Block: '{target.merchant_raw}' is locked as PROTECTED", level="error")
        raise HTTPException(status_code=403, detail=f"SAFETY VIOLATION: '{target.merchant_raw}' is a PROTECTED merchant.")

    if target.risk_level == RiskLevel.HIGH:
        session_manager.set_state(AgentState.FAILED, f"Safety violation: '{target.merchant_raw}' is high risk", mandate_id)
        session_manager.log_agent_activity(f"Safety Violation Block: '{target.merchant_raw}' is HIGH RISK", level="error")
        raise HTTPException(status_code=403, detail=f"SAFETY VIOLATION: '{target.merchant_raw}' is HIGH RISK.")

    def _run():
        dash_url = session_manager.get_active_dashboard_url()
        page = session_manager.get_active_page(headless=headless, demo_mode=demo_mode)

        # Ensure page is on the Personal CFO Dashboard
        if "mandate.html" not in page.url.lower():
            logger.info(f"[SESSION] Opening active page on Dashboard: {dash_url}")
            page.goto(dash_url)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass
            time.sleep(0.5)

        # 1. READ: Inspect visible recurring commitments on the dashboard
        session_manager.set_state(AgentState.READING, f"Auditing recurring commitments on dashboard for {mandate_id}", mandate_id)
        session_manager.log_agent_activity(f"[READ] Inspecting live dashboard commitments for {target.merchant_raw}...")

        before_mandates = read_mandates_from_dom(page, dash_url)
        logger.info(f"[READ-BEFORE CONFIRMED] Ingested {len(before_mandates)} mandates from live dashboard.")

        # 2. ACT: Execute perceived step loop inside the same user-visible dashboard session
        session_manager.set_state(AgentState.EXECUTING, f"Executing cancellation within dashboard session for {mandate_id}", mandate_id)
        action_result = run_step_loop(page, mandate_id, dash_url, demo_mode=demo_mode)
        logger.info(f"[ACTION LOOP FINISHED] Result: {action_result['result']}")

        # 3. VERIFY: Zero-trust re-scraping live dashboard DOM to verify status change
        session_manager.set_state(AgentState.VERIFYING, f"Zero-trust re-scraping dashboard DOM to verify status change", mandate_id)
        session_manager.log_agent_activity(f"[VERIFY] Re-checking live dashboard records to verify cancellation...")

        time.sleep(0.6)
        after_mandates = read_mandates_from_dom(page, dash_url)

        verification = verify_cancellation(
            before_mandates,
            after_mandates,
            mandate_id,
            action_result["result"],
        )
        logger.info(f"[VERIFICATION RESULT] {verification['status']}: {verification['detail']}")

        # 4. OUTCOME & SYNCHRONIZATION
        if verification["status"] == VerificationStatus.CONFIRMED:
            session_manager.mark_mandate_cancelled(mandate_id)
            session_manager.set_state(AgentState.COMPLETED, f"Successfully cancelled and verified {target.merchant_raw}", mandate_id)
            session_manager.log_agent_activity(f"✓ VERIFIED: {target.merchant_raw} status changed to CANCELLED", highlight=True)
            session_manager.record_history_event(
                title=f"{target.merchant_raw} Cancelled",
                desc=f"Autonomous cancellation executed and verified on live dashboard. Status confirmed CANCELLED.",
                tag="CANCELLED",
                tag_color="emerald"
            )
        else:
            session_manager.set_state(AgentState.FAILED, f"Verification failed: {verification['detail']}", mandate_id)
            session_manager.log_agent_activity(f"Verification alert: {verification['detail']}", level="error")

        # Emit updated savings
        enriched = get_enriched_mandates()
        pot_sav = sum(monthly_equivalent(m) * 12 for m in enriched if m.recommendation == "cancel" and m.status != MandateStatus.CANCELLED)
        session_manager.emit_event("savings_updated", {"potential_savings": round(pot_sav, 2)})

        return {
            "mandate_id": mandate_id,
            "merchant": target.merchant_raw,
            "action_result": action_result["result"],
            "verification": verification,
            "log": action_result["log"],
            "potential_savings": round(pot_sav, 2)
        }

    return session_manager.execute(_run)


def process_cancellation(req: CancelRequest):
    logger.info(f"[REQUEST: CANCEL] Mandate ID: '{req.mandate_id}'")
    mandates = get_enriched_mandates()
    target = next((m for m in mandates if m.id == req.mandate_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Mandate '{req.mandate_id}' not found.")

    if target.risk_level == RiskLevel.MEDIUM and not req.force_medium:
        logger.warning(f"[AMOUNT ESCALATION] Mandate '{target.merchant_raw}' exceeds monthly cap of Rs. 500.")
        raise HTTPException(
            status_code=400,
            detail=f"AMOUNT ESCALATION: '{target.merchant_raw}' exceeds monthly cap of Rs. 500. Explicit user confirmation required."
        )

    return execute_cancellation_pipeline(
        mandate_id=req.mandate_id,
        base_url=req.base_url or DEFAULT_BANK_URL,
        headless=bool(req.headless),
        demo_mode=bool(req.demo_mode)
    )


# ================= REAL-TIME SERVER-SENT EVENTS (SSE) =================

@app.get("/api/events")
async def sse_events(request: Request):
    """
    Real-time Server-Sent Events stream for the Mandate Dashboard.
    Pushes state changes, live activity logs, audit steps, and savings updates.
    """
    q = session_manager.subscribe_events()

    async def event_generator():
        try:
            # Send initial snapshot on connect
            init_payload = {
                "type": "init_state",
                "data": {
                    "state": session_manager.get_state(),
                    "history": session_manager.get_history(),
                    "cancelled": list(session_manager.get_cancelled_mandates()),
                },
                "time": ""
            }
            yield f"data: {json.dumps(init_payload)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = q.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.5)
                    yield ": keepalive\n\n"
        finally:
            session_manager.unsubscribe_events(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ================= REST & API ENDPOINTS =================

@app.get("/mandates")
def get_mandates_canonical():
    return format_mandates_response()


@app.get("/api/mandates")
def get_mandates_api():
    return format_mandates_response()


@app.post("/cancel")
def cancel_canonical(req: CancelRequest):
    return process_cancellation(req)


@app.post("/api/cancel")
def cancel_api(req: CancelRequest):
    return process_cancellation(req)


@app.post("/api/watch")
def trigger_watch_mode(base_url: Optional[str] = None):
    """
    Allows `python run.py --watch` to attach directly to this running session.
    Reuses the existing browser and active dashboard page, executing the
    autonomous agent workflow directly inside the user-visible dashboard.
    """
    target = base_url or session_manager.get_active_dashboard_url()
    logger.info(f"[WATCH MODE ATTACHED] Triggering execution on active dashboard session ({target})...")
    results = []

    # Run m1 (Retention Offer Path) directly inside the dashboard
    res_m1 = execute_cancellation_pipeline(
        mandate_id="m1",
        base_url=target,
        headless=False,
        demo_mode=True
    )
    results.append(res_m1)

    return {"status": "success", "results": results}


@app.get("/api/agent/state")
def get_agent_state():
    return session_manager.get_state()


@app.get("/api/history")
def get_agent_history():
    hist = session_manager.get_history()
    return {"events": hist, "history": hist}


@app.get("/status/{mandate_id}")
def get_mandate_status(mandate_id: str):
    mandates = get_enriched_mandates()
    m = next((item for item in mandates if item.id == mandate_id), None)
    if not m:
        return {"found": False, "mandate_id": mandate_id}
    cancelled_ids = session_manager.get_cancelled_mandates()
    current_status = MandateStatus.CANCELLED.value if mandate_id in cancelled_ids else m.status.value
    return {
        "found": True,
        "mandate_id": m.id,
        "merchant": m.merchant_raw,
        "status": current_status,
        "risk_level": m.risk_level.value if hasattr(m, 'risk_level') and m.risk_level else "low",
        "recommendation": m.recommendation if hasattr(m, 'recommendation') else None,
        "is_protected": m.is_protected if hasattr(m, 'is_protected') else False,
    }


@app.get("/api/status/{mandate_id}")
def get_mandate_status_api(mandate_id: str):
    return get_mandate_status(mandate_id)


@app.post("/session/connect")
def connect_session(req: SessionConnectRequest):
    return session_manager.connect_bank_session(
        bank_name=req.bank_name or "Demo Bank",
        base_url=req.base_url or DEFAULT_BANK_URL,
        headless=bool(req.headless),
        demo_mode=bool(req.demo_mode)
    )


@app.post("/api/session/connect")
def connect_session_api(req: SessionConnectRequest):
    return connect_session(req)


@app.get("/session/status")
def get_session_status():
    return session_manager.get_auth_state()


@app.get("/api/session/status")
def get_session_status_api():
    return session_manager.get_auth_state()


# Mount Static UI Files
ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.isdir(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")


@app.get("/")
def index():
    mandate_html = os.path.join(ui_dir, "mandate.html")
    if os.path.exists(mandate_html):
        return FileResponse(mandate_html)
    return {"status": "ok", "service": "Mandate Personal CFO Agent API"}


# Automatic Browser Startup in Background
@app.on_event("startup")
def on_startup():
    def _start_browser():
        time.sleep(1.5)
        try:
            logger.info("[STARTUP] Opening Mandate Personal CFO Dashboard in unified browser session...")
            session_manager.get_or_create_dashboard_page(DASHBOARD_URL, headless=False, demo_mode=True)
        except Exception as e:
            logger.warning(f"[STARTUP] Could not open initial browser page: {e}")

    threading.Thread(target=_start_browser, daemon=True).start()
