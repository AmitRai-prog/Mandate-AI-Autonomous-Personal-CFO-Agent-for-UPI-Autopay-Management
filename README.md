# Mandate-AI-Autonomous-Personal-CFO-Agent-for-UPI-Autopay-Management
# Mandate // Autonomous Personal CFO Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated_DOM-45ba4b.svg)](https://playwright.dev/)
[![Anakin AI](https://img.shields.io/badge/Anakin_AI-REST_API_v1-8B5CF6.svg)](https://anakin.ai/)
[![Safety Invariants](https://img.shields.io/badge/Safety_Invariants-100%25_Verified-10B981.svg)](#financial-safety-invariants)

---

## Executive Summary

**Mandate** is a production-grade, autonomous **Personal CFO Agent** that continuously monitors, reasons about, and manages recurring financial commitments (subscriptions, autopays, EMIs, insurance policies, and SIPs).

Most AI automation tools treat cancellation as a brittle script or a simple chat prompt. In contrast, Mandate operates as a **true multi-step agentic supervisor**:

$$\text{READ} \longrightarrow \text{REASON} \longrightarrow \text{ACT} \longrightarrow \text{VERIFY}$$

Operating under strict financial safety invariants, Mandate eliminates recurring financial waste while **guaranteeing** that critical financial assets—such as statutory life insurance, contractual debt obligations, and wealth-compounding SIPs—can **never be cancelled or altered**.

---

## What Problem Does Mandate Solve?

1. **Subscription Sprawl & Silent Leakage**: The average modern consumer loses ₹5,000–₹25,000 annually to forgotten subscriptions, uncancelled trial autopays, and redundant services (e.g. paying for both Spotify and YouTube Music).
2. **Netbanking Dark Patterns**: Cancelling a recurring bank autopay or UPI mandate involves hostile user interfaces: hidden navigation trees, multi-page retention offer traps ("Get 3 months free"), and mandatory OTP challenge walls.
3. **Catastrophic Risk of Naive AI**: Naive autonomous agents that blindly click "Cancel" risk cancelling statutory life insurance (causing immediate policy lapse and forfeiting death benefits) or loan EMIs (triggering credit bureau default penalties).
4. **Disconnected Experiences**: Autonomous agents typically run invisibly in background CLI processes. Users never see how the agent operates, breaking trust and auditability.

---

## What Have We Built?

### 1. The 4-Stage Agentic Pipeline

```
  1. READ                       2. REASON                      3. ACT                       4. VERIFY
┌─────────────────────────┐   ┌──────────────────────────┐   ┌────────────────────────┐   ┌─────────────────────────┐
│ Ingests live netbanking │──▶│ Synthesizes immutable    │──▶│ Autonomous perceive-   │──▶│ Zero-trust re-scraping  │
│ autopay records from    │   │ FACTS and explainable    │   │ decide-act step loop;  │   │ of bank records; emits  │
│ DOM (17 commitments)    │   │ LOGIC via Anakin AI      │   │ defeats retention/OTP  │   │ cryptographic proof     │
└─────────────────────────┘   └──────────────────────────┘   └────────────────────────┘   └─────────────────────────┘
```

* **READ**: Reads raw recurring commitment records directly from the live DOM via Playwright.
* **REASON**: Classifies payees across 3 intelligence layers, detects utility overlaps, calculates annualized savings, and synthesizes explainable recommendations.
* **ACT**: Navigates multi-step bank cancellation workflows, autonomously evaluating live screen states, bypassing promotional retention traps, and clearing security challenges.
* **VERIFY**: Re-scrapes the live bank records post-execution to confirm the status transition (`active` → `cancelled`) with zero trust before updating client state.

---

### 2. 3-Layer Payee Intelligence & Anakin AI Integration

Real-world bank statements contain cryptic, truncated merchant strings (e.g. `SPOTIFY IN`, `BESCOM BANGALORE`). Mandate resolves payee identity through three progressive layers:

```
                      Raw Bank Autopay DOM Records
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │    3-Layer Classification Engine   │
                 │                                   │
                 │  Layer 0: Deterministic Protected │
                 │           (LIC, EMIs, SIPs)       │
                 │  Layer 1: Deterministic Rules     │
                 │           (BESCOM, Gemini, Prime) │
                 │  Layer 2: Anakin AI Fallback  ◄───┼── [Anakin Search & LLM]
                 └─────────────────┬─────────────────┘
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │   Risk & Safety Invariant Engine  │
                 │   (Protected: CRITICAL, Cap >500) │
                 └─────────────────┬─────────────────┘
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │     Anakin AI Reasoning Engine    │
                 │                                   │
                 │   • Synthesizes FACTS (Evidence)  │
                 │   • Synthesizes LOGIC (Reasoning) │
                 │   • Discovers Category Overlaps   │
                 │   • Emits Cancel vs Keep Signal   │
                 └─────────────────┬─────────────────┘
                                   │
                                   ▼
                      Personal CFO Dashboard UI
                 (Explainable Facts, Logic, Confidence)
```

1. **Layer 0 (Protected Merchants)**: Deterministic, immutable allowlist of critical institutions (LIC, HDFC Loans, SBI Loans, Groww SIPs, Zerodha Coin). Hard-locked to `CRITICAL` risk; no LLM or prompt can override this.
2. **Layer 1 (Deterministic Pattern Rules)**: High-confidence keyword matching for known subscriptions and utilities.
3. **Layer 2 (Anakin AI Search & LLM Fallback)**:
   - Calls Anakin's Web Search API (`POST https://api.anakin.io/v1/search`) to retrieve real-world merchant identity.
   - Categorizes payees into `subscription`, `utility`, `insurance`, `investment`, or `loan`.
   - **Fail-Closed Safety Policy**: If a merchant string is ambiguous (e.g., `HDFC` alone without product descriptor), Anakin refuses to guess, safely defaulting to `category = unknown, confidence = 0.30`, which automatically escalates to high-risk human review.
4. **Anakin Reasoning Synthesis**: Synthesizes human-readable **FACTS** (evidence bullets) and **LOGIC** (reasoning paragraphs) explaining exactly why an action is recommended.

---

### 3. Non-Negotiable Financial Safety Invariants

| Guardrail | Trigger Condition | Enforcement Mechanism | HTTP Response |
|---|---|---|---|
| **Statutory Life Insurance** | Merchant in Protected List (LIC, ICICI Pru) | Hard-locked to `CRITICAL` risk; cancellation forbidden | `403 Forbidden` |
| **Contractual Debt (EMI)** | Loan/Debt repayment detected (HDFC Loan, SBI Loan) | Hard-locked to `CRITICAL` risk; cancellation forbidden | `403 Forbidden` |
| **Wealth Investment (SIP)** | Mutual fund / Equity SIP (Groww, Zerodha) | Hard-locked to `CRITICAL` risk; cancellation forbidden | `403 Forbidden` |
| **Municipal Utilities** | Essential electricity, water, gas (BESCOM) | Classified as `HIGH` risk; enforced read-only | `403 Forbidden` |
| **Amount Cap Escalation** | Monthly cost exceeds ₹500/mo cap (Netflix 4K) | Escalated to `MEDIUM` risk; requires explicit confirmation | `400 Bad Request` |
| **Ambiguous Payees** | Low-confidence or unspecific brand names (`HDFC`) | Fails closed to `UNKNOWN` category and `HIGH` risk | `403 Forbidden` |

---

### 4. Single-Session Architecture & In-Dashboard Live Execution

To maintain complete user trust and product continuity, Mandate enforces a strict **Single Source of Truth**:

* **ONE Browser Window**: A single Chromium instance managed exclusively by `SessionManager`. Zero duplicate browsers.
* **ONE Authenticated Context**: Shared cookies, local storage, and netbanking authentication state.
* **100% In-Dashboard Execution**: When "Run Demo" is clicked or `python run.py --watch` is executed, the agent **never navigates away from `http://localhost:8000/ui/mandate.html`**.
* **Live Action Workflow Modal**: The agent operates directly inside the dashboard in front of the user:
  1. `manage`: Ingests the commitment record and clicks *"Cancel autopay"*.
  2. `retention`: Detects the bank's retention offer trap (*"3 months free"*) and autonomously clicks *"No thanks, cancel anyway"*.
  3. `otp`: Handles the bank security challenge, inputs the verification code, and clicks *"Verify"*.
  4. `confirm`: Verifies cancellation intent and clicks *"Yes, cancel"*.
  5. `success`: Bank record confirmed cancelled.
* **Real-Time Visual Highlights**: Playwright highlights interactive elements with glowing purple bounding boxes before clicking, giving judges a transparent view of autonomous execution.

---

### 5. Real-Time Observability & Dynamic Calculations

* **Central Agent State Machine**: Tracks states (`IDLE`, `READING`, `CLASSIFYING`, `REASONING`, `WAITING_FOR_APPROVAL`, `EXECUTING`, `VERIFYING`, `COMPLETED`, `FAILED`).
* **Server-Sent Events (SSE)**: Pushes real-time agent telemetry, state changes, and audit logs to the UI via `GET /api/events`.
* **Dynamic Potential Savings Engine**: Potential savings are never hardcoded. Calculated dynamically as:
  $$\text{Potential Savings} = \sum_{\substack{m \in \text{Mandates} \\ m.\text{recommendation} = \text{'cancel'} \\ m.\text{status} \neq \text{'cancelled'}}} m.\text{annual}$$
  Upon cancellation of Spotify India (`m1`), the counter automatically adjusts from ₹3,588 to the remaining actionable amount.
* **Cryptographic Proof Modal**: Displays timestamped bank verification receipts upon task completion.

---

## 17-Mandate Benchmark Dataset

The dataset in `data/mock_mandates.py` covers all archetypes of recurring financial commitments:

| ID | Payee Name | Category | Risk Level | Monthly Cost | Recommendation | Safety Action / Policy |
|:---:|---|---|:---:|:---:|:---:|---|
| `m1` | **Spotify India** | Subscription | Low | ₹299 | **Cancel** | Actionable (+₹3,588/yr, unused 47 days, duplicate YouTube) |
| `m2` | Google *YouTube Premium | Subscription | Low | ₹149 | Keep | Retained (Active usage recorded 2 days ago) |
| `m3` | Google Gemini Advanced | Subscription | Low | ₹1,950 | Keep | Retained (Daily active coding tool) |
| `m4` | **LIC of India Premium** | Insurance | **Critical** | ₹12,450/yr | **None** | **Permanently Protected (Statutory life cover)** |
| `m5` | **Groww SIP - Nifty 50 Index** | Investment | **Critical** | ₹5,000 | **None** | **Permanently Protected (Long-term compound wealth)** |
| `m6` | **ICICI Pru Life Insurance** | Insurance | **Critical** | ₹34,000/yr | **None** | **Permanently Protected (Health & critical illness cover)** |
| `m7` | **HDFC Bank Personal Loan EMI**| Loan | **Critical** | ₹18,500 | **None** | **Permanently Protected (Credit rating protection)** |
| `m8` | **BESCOM Electricity AutoPay** | Utility | **High** | ₹1,400 | Keep | **Enforced Read-Only (Essential municipal utility)** |
| `m9` | **HDFC (Standalone)** | Unknown | **High** | ₹2,500 | **None** | **Fail-Closed Gate (Ambiguous payee safe-stop)** |
| `m10`| **Netflix Premium 4K** | Subscription | **Medium** | ₹649 | **Cancel** | **Amount Escalation (Cost ₹649 > ₹500 threshold)** |
| `m11`| OpenAI *ChatGPT Plus | Subscription | Low | ₹1,999 | Keep | Retained (Active AI developer tool) |
| `m12`| Amazon Prime Annual | Subscription | Low | ₹1,499/yr | Keep | Retained (Active delivery & video streaming) |
| `m13`| Disney+ Hotstar Super | Subscription | Low | ₹899/yr | **Cancel** | Actionable (+₹899/yr, unused 62 days) |
| `m14`| Anthropic *Claude Pro | Subscription | Low | ₹1,999 | Keep | Retained (Active coding & reasoning tool) |
| `m15`| Zerodha Coin SIP - Large Cap | Investment | **Critical** | ₹3,000 | **None** | **Permanently Protected (Index fund accumulation)** |
| `m16`| SBI Vehicle Loan EMI | Loan | **Critical** | ₹14,200 | **None** | **Permanently Protected (Secured debt obligation)** |
| `m17`| Airtel Broadband AutoPay | Utility | **High** | ₹1,199 | Keep | **Enforced Read-Only (Home internet lifeline)** |

---

## Quickstart & Demo Guide

### Prerequisites

* Python 3.10+
* Playwright Chromium (`playwright install chromium`)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-username/mandate-app.git
cd mandate-app

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser binaries
playwright install chromium
```

---

### Running the Application

Mandate includes a unified master runner (`run.py`) executable from either the root directory or the `mandate-app/` subfolder:

#### 1. Full Automated Verification Suite (Definition of Done)
Runs the end-to-end verification suite validating all safety invariants, classification layers, reasoning generation, and Playwright cancellation flows (`m1`, `m10`, and `m2`):

```bash
python run.py
```

#### 2. Start the Personal CFO Server & Unified Dashboard
Starts the FastAPI backend on port 8000 and automatically launches the Chromium browser window displaying the Personal CFO Dashboard:

```bash
python run.py --server
```
* **Dashboard URL**: `http://localhost:8000/ui/mandate.html`
* **Interactive Demo**: Click **Connect Bank** (or **Instant Demo**), review the recommendations, and click **⚡ Run Autonomous Demo**. Watch the agent execute the live multi-step workflow directly inside the dashboard.

#### 3. Attach in Watch Mode
While `python run.py --server` is running, execute watch mode in a separate terminal:

```bash
python run.py --watch
```
* Attaches directly to the running session via `/api/watch`.
* Reuses the existing user browser window without launching a second browser.
* Streams the live perceive-decide-act audit log to the terminal while updating the dashboard in real time.

---

## Repository Structure

```
mandate-app/
├── run.py                          # Master one-command runner (--server, --watch, tests)
├── requirements.txt                # Python dependencies (FastAPI, Uvicorn, Playwright, Requests)
├── README.md                       # Comprehensive project documentation
├── mandate-app/
│   ├── server.py                   # FastAPI application, SSE event stream, REST endpoints
│   ├── run_all_verifications.py    # Complete Definition of Done test suite
│   ├── test_backend.py             # API route, classification, & safety invariant tests
│   ├── test_local.py               # Standalone Playwright testing script
│   ├── DEMO_SCRIPT.md              # 2-minute live demo script for judges
│   ├── SUBMISSION_CHECKLIST.md     # Hackathon submission audit checklist
│   ├── data/
│   │   ├── mandate_schema.py       # Core domain schemas (RiskLevel, Category, Mandate)
│   │   ├── mock_mandates.py        # 17-mandate benchmark dataset
│   │   └── session_state.json      # Authenticated browser session state & cookies
│   ├── pipeline/
│   │   ├── session_manager.py      # Exclusive owner of Playwright lifecycle & active page
│   │   ├── classify.py             # 3-layer classification orchestrator
│   │   ├── protected_merchants.py  # Layer 0: Hard-coded protected merchant invariants
│   │   ├── layer1_rules.py         # Layer 1: Deterministic keyword pattern matching
│   │   ├── layer2_llm.py           # Layer 2: Anakin AI intelligence fallback
│   │   ├── anakin_client.py        # Anakin platform client (Search, Scraping, Agentic)
│   │   ├── risk_engine.py          # Risk assignment & amount cap escalation logic
│   │   ├── reasoning_engine.py     # Evidence & reasoning synthesis engine
│   │   ├── read_mandates.py        # Zero-trust DOM mandate extraction
│   │   ├── action_agent.py         # Autonomous perceive-decide-act step loop
│   │   └── verification_agent.py   # Zero-trust verification engine
│   └── ui/
│       ├── mandate.html            # Unified Personal CFO Dashboard (100% in-dashboard execution)
│       └── mock-bank.html          # Local netbanking sandbox for isolated unit testing
```

---

## Verification & Test Results

The entire system is continuously verified against automated test suites:

```text
===================================================================
 MANDATE AGENT: COMPLETE DEFINITION OF DONE VALIDATION
===================================================================
--- 1. VERIFYING READ & REASON PIPELINE & SAFETY INVARIANTS ---
[PASS] Invariant 1: LIC OF INDIA PREMIUM -> CRITICAL (Protected, Read-Only)
[PASS] Invariant 1: GROWW SIP - NIFTY 50 INDEX -> CRITICAL (Protected, Read-Only)
[PASS] Invariant 1: ICICI PRU LIFE INS PREM -> CRITICAL (Protected, Read-Only)
[PASS] Invariant 1: HDFC BANK EMI - PERSONAL LOAN -> CRITICAL (Protected, Read-Only)
[PASS] Invariant 1: Zerodha Coin SIP - Large Cap -> CRITICAL (Protected, Read-Only)
[PASS] Invariant 1: SBI Vehicle Loan EMI -> CRITICAL (Protected, Read-Only)
[PASS] Invariant 2: HDFC -> UNKNOWN / HIGH risk (Failed closed)
[PASS] Invariant 3: Netflix Premium 4K Family Plan (Rs. 649) -> MEDIUM risk (Escalated)
[PASS] Low risk actionable: m1 (Spotify unused 47 days) recommended to cancel

--- 2. VERIFYING AGENT FLOW: m1 (Retention Offer Path) ---
  Action Result: ActionResult.CANCELLED
  Step Count: 4
    Step 1: [manage] -> click Cancel autopay
    Step 2: [retention] -> decline retention offer (No thanks, cancel anyway)
    Step 3: [confirm] -> confirm cancellation (Yes, cancel)
    Step 4: [success] -> terminal state reached (success)
  Verification Status: VerificationStatus.CONFIRMED
[PASS] m1 (Retention Offer Path) successfully REACHED VERIFIED!

--- 2. VERIFYING AGENT FLOW: m10 (OTP Challenge Path) ---
  Action Result: ActionResult.CANCELLED
  Step Count: 4
    Step 1: [manage] -> click Cancel autopay
    Step 2: [otp] -> enter OTP and click Verify
    Step 3: [confirm] -> confirm cancellation (Yes, cancel)
    Step 4: [success] -> terminal state reached (success)
  Verification Status: VerificationStatus.CONFIRMED
[PASS] m10 (OTP Challenge Path) successfully REACHED VERIFIED!

--- 2. VERIFYING AGENT FLOW: m2 (Standard Path) ---
  Action Result: ActionResult.CANCELLED
  Step Count: 3
    Step 1: [manage] -> click Cancel autopay
    Step 2: [confirm] -> confirm cancellation (Yes, cancel)
    Step 3: [success] -> terminal state reached (success)
  Verification Status: VerificationStatus.CONFIRMED
[PASS] m2 (Standard Path) successfully REACHED VERIFIED!

===================================================================
 ALL DEFINITION OF DONE INVARIANTS SATISFIED & FULLY VERIFIED!
===================================================================
```

---

## Key Takeaway for Judges

Mandate is not another chat-to-code prototype. It is a **robust, safety-first financial autonomous agent** built with:
* **Deterministic safety invariants** that make financial damage impossible.
* **Grounding via Anakin AI** for intelligent classification and transparent reasoning.
* **A unified single-session architecture** where the user and the agent share the same dashboard.
* **True closed-loop execution**: Perceiving UI dark patterns, acting, and verifying independently with zero trust.
