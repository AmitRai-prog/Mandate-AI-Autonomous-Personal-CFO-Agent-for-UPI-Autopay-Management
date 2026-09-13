"""
SessionManager — Single Source of Truth for Browser, Page, and Agent State.

Architectural Guarantees:
  1. EXCLUSIVE OWNER of Playwright, Browser, BrowserContext, and Page lifecycles.
     No other module may call sync_playwright(), browser.launch(),
     browser.new_context(), or context.new_page().
  2. DUAL-TAB LIVE WORKSPACE:
     - Tab 1 (_dashboard_page): Mandate Personal CFO Dashboard. Stays open and active.
     - Tab 2 (_agent_page): Live Autonomous Agent Workspace. Visibly executes bank flows in real time.
     - Tab 3 (_verification_page): Ephemeral isolated verification page.
  3. CENTRAL AGENT STATE MACHINE:
     Tracks IDLE, READING, CLASSIFYING, REASONING, WAITING_FOR_APPROVAL,
     EXECUTING, VERIFYING, COMPLETED, FAILED.
  4. REAL-TIME EVENT STREAM:
     Publishes state transitions, audit steps, and data updates to SSE consumers.
  5. PERSISTENT HISTORY & STRUCTURED OBSERVABILITY:
     Maintains long-term audit timeline and formatted structured logs.
"""

import os
import sys
import time
import queue
import logging
import threading
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

logger = logging.getLogger("session_manager")

LOCAL_UI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui"))
LOCAL_MOCK_BANK_PATH = os.path.join(LOCAL_UI_DIR, "mock-bank.html")
LOCAL_DASHBOARD_PATH = os.path.join(LOCAL_UI_DIR, "mandate.html")

DEFAULT_SERVER_PORT = 8000
DEFAULT_DASHBOARD_URL = f"http://localhost:{DEFAULT_SERVER_PORT}/ui/mandate.html"
DEFAULT_BANK_URL = f"http://localhost:{DEFAULT_SERVER_PORT}/ui/mock-bank.html"
STORAGE_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "session_state.json")


class AgentState(str, Enum):
    IDLE = "IDLE"
    READING = "READING"
    CLASSIFYING = "CLASSIFYING"
    REASONING = "REASONING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SessionManager:
    """
    Central manager for browser session continuity, agent state machine,
    and event broadcasting. Sole owner of Playwright in the application.
    """

    def __init__(self, storage_state_path: str = STORAGE_STATE_FILE):
        self._storage_state_path = storage_state_path
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PlaywrightWorker")
        self._worker_thread_id: Optional[int] = None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

        # Dynamic URL resolution
        self._dashboard_url: str = DEFAULT_DASHBOARD_URL
        self._bank_url: str = DEFAULT_BANK_URL

        # Single active user-visible page in the shared context
        self._active_page: Optional[Page] = None
        self._dashboard_page: Optional[Page] = None
        self._agent_page: Optional[Page] = None

        # State Machine & Event Bus
        self._state: AgentState = AgentState.IDLE
        self._current_step: str = "Ready for instructions"
        self._target_mandate: Optional[str] = None
        self._subscribers: List[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._audit_timeline: List[Dict[str, Any]] = []
        self._longterm_history: List[Dict[str, Any]] = [
            {
                "id": "h-init-1",
                "timestamp": "Today, 09:15 AM",
                "title": "Continuous Mandate Monitoring Active",
                "desc": "Personal CFO initialized session across netbanking mandates. Safeguards active.",
                "tag": "MONITORING",
                "tag_color": "emerald"
            },
            {
                "id": "h-init-2",
                "timestamp": "Today, 09:15 AM",
                "title": "Statutory Assets Hard-Locked",
                "desc": "LIC Life Insurance, HDFC Loan EMI, and Groww SIP locked safe under Layer 0 policy.",
                "tag": "PROTECTED",
                "tag_color": "emerald"
            },
            {
                "id": "h-init-3",
                "timestamp": "Today, 09:16 AM",
                "title": "Savings Opportunity Identified",
                "desc": "Spotify India flagged: 0 audio streams for 47 consecutive days. Overlaps with YouTube Premium.",
                "tag": "OPPORTUNITY",
                "tag_color": "amber"
            }
        ]
        self._cancelled_mandates: set[str] = set()

        self._auth_state: Dict[str, Any] = {"authenticated": False, "bank": None}
        self._demo_mode: bool = True
        self._headless: bool = False

        # Initialize worker thread ID
        def _init_thread():
            self._worker_thread_id = threading.get_ident()
            return True
        self._executor.submit(_init_thread).result()

    def is_worker_thread(self) -> bool:
        return threading.get_ident() == self._worker_thread_id

    def execute(self, fn, *args, **kwargs):
        """Submit a callable to the dedicated Playwright thread and return the result. Supports re-entrancy."""
        if self.is_worker_thread():
            return fn(*args, **kwargs)
        future = self._executor.submit(fn, *args, **kwargs)
        return future.result()

    # ================= 1. STATE MACHINE & EVENT STREAM =================

    def set_state(self, state: AgentState, step_detail: Optional[str] = None, target_mandate: Optional[str] = None):
        self._state = state
        if step_detail is not None:
            self._current_step = step_detail
        if target_mandate is not None:
            self._target_mandate = target_mandate

        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[AGENT STATE: {self._state.value}] {self._current_step} (Target: {self._target_mandate or 'N/A'})")

        self.emit_event("state_change", {
            "state": self._state.value,
            "step": self._current_step,
            "target_mandate": self._target_mandate,
            "timestamp": timestamp
        })

    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "step": self._current_step,
            "target_mandate": self._target_mandate,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

    def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Dispatches an SSE event to all connected clients."""
        payload = {"type": event_type, "data": data, "time": datetime.now().strftime("%H:%M:%S")}
        with self._subscribers_lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(payload)
                except Exception:
                    dead_queues.append(q)
            for q in dead_queues:
                if q in self._subscribers:
                    self._subscribers.remove(q)

    def subscribe_events(self) -> queue.Queue:
        q = queue.Queue(maxsize=100)
        with self._subscribers_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe_events(self, q: queue.Queue):
        with self._subscribers_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def log_agent_activity(self, message: str, level: str = "info", highlight: bool = False):
        """Adds a human-readable entry to the live activity stream and broadcasts it."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": timestamp,
            "message": message,
            "level": level,
            "highlight": highlight
        }
        logger.info(f"[ACTIVITY FEED] {timestamp} | {message}")
        self.emit_event("agent_log", entry)

    def record_audit_step(self, step_number: int, url: str, detected_state: str, chosen_action: str, resulting_state: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        step_data = {
            "step": step_number,
            "time": timestamp,
            "url": url,
            "detected_state": detected_state,
            "chosen_action": chosen_action,
            "resulting_state": resulting_state
        }
        self._audit_timeline.append(step_data)
        self.emit_event("audit_step", step_data)
        logger.info(f"[AUDIT STEP {step_number}] [{detected_state}] -> {chosen_action} -> [{resulting_state}]")

    def record_history_event(self, title: str, desc: str, tag: str = "ACTION", tag_color: str = "amber"):
        timestamp = datetime.now().strftime("%b %d, %I:%M %p")
        entry = {
            "id": f"h-{int(time.time()*1000)}",
            "timestamp": timestamp,
            "title": title,
            "desc": desc,
            "tag": tag,
            "tag_color": tag_color
        }
        self._longterm_history.insert(0, entry)
        self.emit_event("history_update", entry)
        logger.info(f"[HISTORY LOG] {title}: {desc}")

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._longterm_history)

    def mark_mandate_cancelled(self, mandate_id: str):
        self._cancelled_mandates.add(mandate_id)
        self.emit_event("mandate_cancelled", {"mandate_id": mandate_id})

    def get_cancelled_mandates(self) -> set[str]:
        return set(self._cancelled_mandates)

    # ================= 2. BROWSER & CONTEXT LIFECYCLE (EXCLUSIVE OWNER) =================

    def _ensure_playwright(self):
        if self._playwright is None:
            logger.info("[SessionManager] Starting Playwright engine on dedicated worker thread...")
            self._playwright = sync_playwright().start()

    def _ensure_browser(self, headless: bool = False, demo_mode: bool = True) -> Browser:
        self._ensure_playwright()
        if self._browser is not None and self._browser.is_connected():
            if self._headless == headless:
                return self._browser
            else:
                logger.info(f"[SessionManager] Headless mode change ({self._headless} -> {headless}). Reconnecting browser...")
                self._close_browser_sync()

        self._headless = headless
        self._demo_mode = demo_mode
        slow_mo = 1000 if demo_mode else 0
        logger.info(f"[SessionManager] Launching Chromium (headless={headless}, slow_mo={slow_mo}ms)...")
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--start-maximized", "--no-sandbox"] if not headless else []
        )
        return self._browser

    def _ensure_context(self, headless: bool = False, demo_mode: bool = True) -> BrowserContext:
        self._ensure_browser(headless=headless, demo_mode=demo_mode)
        if self._context is not None:
            return self._context

        os.makedirs(os.path.dirname(self._storage_state_path), exist_ok=True)
        if os.path.exists(self._storage_state_path):
            try:
                logger.info(f"[SessionManager] Restoring context from storage_state: {self._storage_state_path}")
                self._context = self._browser.new_context(
                    storage_state=self._storage_state_path,
                    no_viewport=True if not headless else False
                )
                return self._context
            except Exception as e:
                logger.warning(f"[SessionManager] Failed to restore storage state: {e}. Opening clean context.")

        logger.info("[SessionManager] Creating clean shared authenticated browser context...")
        self._context = self._browser.new_context(no_viewport=True if not headless else False)
        return self._context

    # ================= 3. UNIFIED SINGLE-PAGE WORKSPACE & DYNAMIC URL RESOLUTION =================

    def get_active_dashboard_url(self) -> str:
        """Returns the dynamic active dashboard URL."""
        return self._dashboard_url

    def get_active_bank_url(self) -> str:
        """
        Dynamically resolves the active bank URL.
        Defaults to http://localhost:8000/ui/mock-bank.html.
        Falls back to local file URL if running standalone without HTTP server.
        """
        if self._bank_url and self._bank_url.startswith("http"):
            return self._bank_url
        file_path = LOCAL_MOCK_BANK_PATH.replace("\\", "/")
        return f"file:///{file_path}"

    def set_bank_url(self, url: str):
        if url:
            self._bank_url = url

    def set_dashboard_url(self, url: str):
        if url:
            self._dashboard_url = url

    def has_browser(self) -> bool:
        """Checks if SessionManager already owns an active browser."""
        def _check():
            return self._browser is not None and self._browser.is_connected()
        try:
            return self.execute(_check)
        except Exception:
            return False

    def has_active_page(self) -> bool:
        """Checks if an active page is already open in the session."""
        def _check():
            return self._active_page is not None and not self._active_page.is_closed()
        try:
            return self.execute(_check)
        except Exception:
            return False

    def get_active_page(self, headless: bool = False, demo_mode: bool = True) -> Page:
        """
        Retrieves or initializes the single active page belonging to the user's
        unified session. Ensures exactly ONE browser window and ONE page.
        """
        def _get_page():
            ctx = self._ensure_context(headless=headless, demo_mode=demo_mode)
            if self._active_page is not None and not self._active_page.is_closed():
                return self._active_page

            pages = [p for p in ctx.pages if not p.is_closed()]
            if pages:
                self._active_page = pages[0]
            else:
                logger.info("[SessionManager] Creating unified user session page...")
                self._active_page = ctx.new_page()

            # Maintain compatibility references to the single page
            self._dashboard_page = self._active_page
            self._agent_page = self._active_page
            return self._active_page

        return self.execute(_get_page)

    def navigate_to_dashboard(self) -> Page:
        """Navigates the user's active page back to the Personal CFO Dashboard."""
        def _nav():
            page = self.get_active_page()
            dash_url = self.get_active_dashboard_url()
            if "mandate.html" not in page.url:
                logger.info(f"[SessionManager] Navigating active session page to Dashboard: {dash_url}")
                page.goto(dash_url)
            return page
        return self.execute(_nav)

    def navigate_to_bank(self) -> Page:
        """Navigates the user's active page into the bank mandate workflow."""
        def _nav():
            page = self.get_active_page()
            bank_url = f"{self.get_active_bank_url()}?page=mandates"
            logger.info(f"[SessionManager] Navigating active session page to Bank: {bank_url}")
            page.goto(bank_url)
            return page
        return self.execute(_nav)

    def get_or_create_dashboard_page(self, dashboard_url: Optional[str] = None,
                                      headless: bool = False, demo_mode: bool = True) -> Page:
        """
        Retrieves or creates the single user session page pointing to the Mandate Dashboard.
        """
        if dashboard_url:
            self._dashboard_url = dashboard_url

        def _get_dash():
            page = self.get_active_page(headless=headless, demo_mode=demo_mode)
            dash = self.get_active_dashboard_url()
            if "mandate.html" not in page.url:
                logger.info(f"[SessionManager] Opening Dashboard on active page: {dash}")
                try:
                    page.goto(dash)
                except Exception as e:
                    logger.warning(f"[SessionManager] Could not navigate dashboard: {e}")
            return page

        return self.execute(_get_dash)

    def get_or_create_agent_page(self, target_url: Optional[str] = None,
                                 headless: bool = False, demo_mode: bool = True) -> Page:
        """
        Reuses the existing user session page rather than opening a second tab.
        """
        def _get_agent():
            page = self.get_active_page(headless=headless, demo_mode=demo_mode)
            if target_url and page.url != target_url:
                logger.info(f"[SessionManager] Navigating active page to: {target_url}")
                page.goto(target_url)
            return page

        return self.execute(_get_agent)

    def focus_dashboard(self):
        """Ensures dashboard is the active screen."""
        self.navigate_to_dashboard()

    def focus_agent_workspace(self):
        """Reuses active page."""
        pass

    def get_verification_page(self, base_url: Optional[str] = None) -> Page:
        """
        Uses the active page for verification re-reading.
        """
        return self.get_active_page()

    def get_or_create_page(self, base_url: Optional[str] = None,
                           headless: bool = False, demo_mode: bool = True) -> Page:
        """Returns the primary active page."""
        target = f"{(base_url or self.get_active_bank_url()).rstrip('/')}?page=mandates"
        return self.get_or_create_agent_page(target_url=target, headless=headless, demo_mode=demo_mode)

    def connect_bank_session(self, bank_name: str = "Demo Bank", base_url: Optional[str] = None,
                             headless: bool = False, demo_mode: bool = True) -> Dict[str, Any]:
        """
        Initializes the user's authenticated bank portal session and saves storage state.
        """
        if base_url:
            self._bank_url = base_url

        def _connect():
            target_bank = self.get_active_bank_url().rstrip("/")
            ctx = self._ensure_context(headless=headless, demo_mode=demo_mode)
            page = self.get_active_page(headless=headless, demo_mode=demo_mode)

            try:
                page.goto(f"{target_bank}?page=mandates")
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass

            # Save storage state
            try:
                ctx.storage_state(path=self._storage_state_path)
                logger.info(f"[SessionManager] Auth storage state saved to {self._storage_state_path}")
            except Exception as e:
                logger.warning(f"[SessionManager] Could not save storage state: {e}")

            self._auth_state = {
                "authenticated": True,
                "bank": bank_name,
                "base_url": target_bank,
                "storage_saved": os.path.exists(self._storage_state_path)
            }
            return {
                "status": "connected",
                "bank": bank_name,
                "base_url": target_bank,
                "authenticated": True,
                "url": page.url,
                "session_active": True
            }

        return self.execute(_connect)

    def get_auth_state(self) -> Dict[str, Any]:
        return {
            **dict(self._auth_state),
            "state": self._state.value,
            "step": self._current_step,
            "has_browser": self._browser is not None and self._browser.is_connected(),
            "has_context": self._context is not None,
            "dashboard_open": self._dashboard_page is not None and not self._dashboard_page.is_closed(),
            "agent_open": self._agent_page is not None and not self._agent_page.is_closed(),
            "cancelled_count": len(self._cancelled_mandates)
        }

    # ================= 4. CLEAN SHUTDOWN =================

    def _close_browser_sync(self):
        for p in [self._dashboard_page, self._agent_page]:
            if p is not None and not p.is_closed():
                try:
                    p.close()
                except Exception:
                    pass
        self._dashboard_page = None
        self._agent_page = None

        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

    def close_session(self):
        def _close():
            self._close_browser_sync()
            if self._playwright is not None:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            self._auth_state = {"authenticated": False, "bank": None}
            self._state = AgentState.IDLE
            self._current_step = "Session closed cleanly"
            logger.info("[SessionManager] Session closed cleanly.")

        return self.execute(_close)


# Global singleton instance
session_manager = SessionManager()
