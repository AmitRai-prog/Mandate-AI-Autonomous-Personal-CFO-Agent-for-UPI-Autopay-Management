# Anakin Forge Hackathon — Submission Readiness Checklist

## Project Information
* **Project Name**: Mandate
* **Track**: Autonomous Financial Agents / Browser Agency
* **Tagline**: Safety-First Autonomous Financial Agent (READ → REASON → ACT → VERIFY)
* **Deployed Mock Bank Target**: `http://localhost:8000/ui/mock-bank.html`

---

## 1. Judging Criteria & Architecture Alignment

| Judging Criteria | Mandate Implementation | Verification Evidence |
|---|---|---|
| **Autonomous Action** | Multi-step agent navigation through dynamic obstacles (retention offers, OTP walls, confirmation modals) without hardcoded DOM paths. | `pipeline/action_agent.py`, `test_local.py` runs for `m1` & `m10` |
| **Safety & Guardrails** | Deterministic Protected Merchant list, Confidence Gating (fail-closed), ₹500/mo amount escalation, Human-in-the-loop approval requirement. | `pipeline/protected_list.py`, `pipeline/risk_engine.py`, `test_backend.py` |
| **Independent Verification** | Distrustful Verification Agent re-reads DOM on independent page/session, confirming `active -> cancelled` state transition. | `pipeline/verification_agent.py`, `pipeline/read_mandates.py` |
| **Engineering Rigor** | Full separation of Evidence vs Inference; granular per-step audit logging (`current_url`, `state`, `available_actions`, `chosen_action`, `resulting_url`, `resulting_state`). | Step audit logs in terminal output & API response |
| **Real-World Feasibility** | Clean integration with netbanking environments via Playwright / CDP sessions; lightweight FastAPI backend bridge. | `server.py`, `ui/mandate.html` |

---

## 2. Core Submission Artifacts Checklist

- [x] **Single Source of Truth & SessionManager Exclusive Ownership**:
  - Exactly one Playwright instance, one Chromium process, and one BrowserContext across the entire application lifecycle.
  - Zero rogue Playwright calls across the codebase; `run.py --watch` attaches directly to the server session via `/api/watch`.
- [x] **Dual-Tab Live Agent Workspace**:
  - Tab 1: Dashboard (`/ui/mandate.html`) remains active and visible.
  - Tab 2: Live Agent Workspace executes against the bank portal synchronously.
- [x] **Real-Time Event Stream (SSE) & Central State Machine**:
  - Server-Sent Events endpoint `/api/events` pushes live state transitions (`IDLE`, `READING`, `CLASSIFYING`, `REASONING`, `WAITING_FOR_APPROVAL`, `EXECUTING`, `VERIFYING`, `COMPLETED`, `FAILED`).
  - Activity feed, audit timeline, and history update dynamically without page reloads.
- [x] **Dynamic Savings Engine & Explainable Reasoning**:
  - Potential savings dynamically recomputed as sum of remaining actionable recommendations.
  - Plain English FACTS & LOGIC cards; clean 5-second review modal without developer jargon.
- [x] **Working Autonomous Action Loop**:
  - `m1` (Retention offer path) reaches `ActionResult.CANCELLED` and `VerificationStatus.CONFIRMED`.
  - `m10` (OTP wall challenge path) reaches `ActionResult.CANCELLED` and `VerificationStatus.CONFIRMED`.
  - `m2` (Direct path) reaches `ActionResult.CANCELLED` and `VerificationStatus.CONFIRMED`.
- [x] **Safety Invariants Tested**:
  - `m4` (LIC) / `m5` (Groww) / `m6` (ICICI) / `m7` (HDFC EMI) / `m15` (Zerodha) / `m16` (SBI Auto Loan) locked as `CRITICAL` risk; cannot be cancelled via API (returns HTTP 403).
  - `m8` (BESCOM Electricity) and `m17` (Airtel Broadband) classified as `HIGH` risk utilities (returns HTTP 403).
  - `m9` (HDFC alone) confidence gated to `UNKNOWN` / `HIGH` risk (returns HTTP 403).
  - `m10` (Netflix ₹649) escalated to `MEDIUM` risk due to ₹500 cap; requires explicit human override.
- [x] **Step Audit Logging & Distrustful Verification Agent**:
  - Every action logs: `current_url`, `detected_state`, `available_actions`, `chosen_action`, `resulting_url`, `resulting_state`.
  - Distrustful Verification Agent never trusts Action Agent output; performs independent DOM scrape confirming `active -> cancelled`.
- [x] **Backend Bridge & UI**:
  - FastAPI server (`server.py`) serving `/api/mandates`, `/api/cancel`, `/api/status/{id}`, `/api/events`, `/api/history`, `/api/watch`, and static UI files.
  - Dashboard UI with One-Click Judge Demo Mode (`⚡ Run Autonomous Demo`).
- [x] **Demo Script**:
  - Completed in `DEMO_SCRIPT.md` (Personal CFO positioning: READ → REASON → ACT → VERIFY).

---

## 3. Demo Video Recording Checklist

- [ ] **Recording Length**: Between 3:00 and 5:00 minutes.
- [ ] **Audio Quality**: Clean voiceover without background noise.
- [ ] **Resolution**: 1080p (1920x1080) 60fps / 30fps.
- [ ] **Key Sequences to Show on Video**:
  1. Mandate Dashboard overview: 10 mandates ingested, spend graph, and breakdown across categories.
  2. Protected tab: Point out LIC, Groww SIP, and Loans locked with Red badge.
  3. Safety Gate in terminal/API: Attempting to cancel protected merchant returning `403 SAFETY VIOLATION`.
  4. Live Action Run on `m1` (Spotify): Show terminal or visual browser declining retention offer and reaching `CONFIRMED`.
  5. Live Action Run on `m10` (Netflix): Show agent entering OTP and clearing verification into `CONFIRMED`.
  6. Verification Agent proof: Show the after-table reflecting `cancelled` and the independent comparison check.

---

## 4. GitHub Repository Preparation Checklist

- [ ] **Visibility**: Set repository to **Public** before submission deadline.
- [ ] **README.md**: Includes:
  - Project Overview & Pitch ("Safety-first autonomous financial agent...")
  - High-level Architecture diagram (READ → REASON → ACT → VERIFY)
  - Quickstart instructions (`pip install -r requirements.txt`, `python test_local.py ...`)
  - Safety Engine documentation (The 4 Invariants)
  - Video demo link (YouTube / Loom)
- [ ] **Clean Git History & Branching**: Clean commits on `main`.
- [ ] **License**: Include standard MIT or Apache 2.0 license.

---

## 5. Verification Commands for Judges & Evaluators

Run these commands in the terminal to reproduce all results:

```bash
# 1. Run local test on retention flow (m1):
python test_local.py m1 --headless

# 2. Run local test on OTP flow (m10):
python test_local.py m10 --headless

# 3. Run local test on standard flow (m2):
python test_local.py m2 --headless

# 4. Verify all backend safety guardrails:
python test_backend.py

# 5. Start the full application with UI:
python -m uvicorn server:app --reload --port 8000
# Open http://localhost:8000/ui/mandate.html in browser
```
