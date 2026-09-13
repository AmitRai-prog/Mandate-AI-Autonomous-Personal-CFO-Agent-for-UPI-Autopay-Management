# Mandate: 3–5 Minute Live Demo Script
## Anakin Forge Hackathon

**Pitch Positioning**: *"Mandate is a safety-first autonomous financial agent capable of operating inside netbanking systems through layered safeguards and independently verified action."*

**Do NOT pitch as a subscription canceller.**
Pitch as an autonomous financial agent proving **READ → REASON → ACT → VERIFY** under strict safeguards.

---

## Timing & Stage Breakdown

| Section | Duration | Key Screen / Artifact | Core Message |
|---|---|---|---|
| 1. Problem | 0:00 – 0:40 | Real netbanking context / pain points | Dark patterns, unpredictable friction, high financial risk without safeguards. |
| 2. Read | 0:40 – 1:15 | Netbanking DOM extraction / Terminal / Dashboard | Live structured extraction of all 10 mandates across all asset classes. |
| 3. Reason | 1:15 – 2:00 | Mandate Dashboard Overview & Reasoning cards | Evidence vs Inference separation: Overlap detection, self-reported usage, savings calculation. |
| 4. Safety Controls | 2:00 – 2:50 | Locked tab / API Safety response | The 4 Invariants: Deterministic protected list, confidence gating, ₹500 cap escalation, human approval. |
| 5. Action | 2:50 – 3:45 | Live Playwright execution (`m1` retention & `m10` OTP) | Adaptive perception-action loop overcoming dynamic retention and OTP walls without hardcoded selectors. |
| 6. Verification | 3:45 – 4:20 | Verification Agent re-scrape log & state change | Zero-trust independent verification: DOM re-scrape confirms `active -> cancelled`. |
| 7. Impact | 4:20 – 5:00 | Architecture slide / Summary | Real autonomous agency in production finance through verified action and bounded blast radius. |

---

## Detailed Spoken Script & Actions

### 1. Problem (0:00 – 0:40)
* **Speaker**:
  > *"Every month, recurring auto-debits silently drain consumer accounts across subscriptions, insurance, loans, and utility mandates. But bringing autonomous AI agents into banking has remained an unsolved problem.*
  >
  > *Why? Because financial environments are unforgiving. If a rogue agent cancels an LIC life insurance policy or an HDFC home loan EMI, the consequences are catastrophic. Furthermore, banks deliberately design multi-step cancellation journeys with dark patterns—retention discount walls, mandatory OTP challenges, and deceptive prompts.*
  >
  > *Today, we present **Mandate**: a safety-first autonomous financial agent that proves an AI agent can execute multi-step financial actions with zero hardcoded sequences, bounded risk, and independent verification."*

### 2. Read (0:40 – 1:15)
* **Action**: Show live netbanking page `http://localhost:8000/ui/mock-bank.html` and dashboard scanning screen.
* **Speaker**:
  > *"Our pipeline starts with **READ**. Rather than relying on static APIs, Mandate extracts mandates directly from live netbanking interfaces using structured DOM scraping.*
  >
  > *Here, Mandate connects to our netbanking environment and ingests active mandates spanning subscriptions, SIP mutual funds, term life insurance, electricity bills, and loans.*
  >
  > *Notice that Mandate never sees or stores banking passwords; it operates over secure browser sessions."*

### 3. Reason (1:15 – 2:00)
* **Action**: Switch to Mandate Dashboard (`ui/mandate.html`). Hover over the spend overview bar and the "Ready for Approval" card for Spotify.
* **Speaker**:
  > *"Next is **REASON**. Mandate separates **evidence** from **inference**. Evidence consists of immutable facts: payee name, debit amount, frequency, and self-reported app usage.*
  >
  > *From this evidence, Mandate reasons:*
  > * *For Spotify (`m1`): It detects 47 days of non-usage and identifies an active overlap with YouTube Premium streaming. Net annual savings: ₹3,588.*
  > * *For Gemini Advanced (`m3`): It notes active usage 2 days ago, recommending retention.*
  > * *Crucially, Mandate never acts autonomously at this stage. It presents a human-in-the-loop recommendation."*

### 4. Safety Controls (2:00 – 2:50)
* **Action**: Click the "Locked" and "Needs Review" tabs on the dashboard. Trigger API call attempting to cancel `m4` (LIC) and show HTTP 403 response.
* **Speaker**:
  > *"Before any action is allowed, our 4-layer Safety Engine enforces strict, non-probabilistic invariants:*
  >
  > 1. * **Layer 0: Deterministic Protected Merchant List**: Payees like LIC of India, Groww SIP, ICICI Pru, and HDFC Loan are locked as **CRITICAL**. No LLM, prompt, or user override can ever touch them. Notice our API instantly blocks an attempted action on LIC with a 403 Safety Violation.*
  > 2. * **Layer 1 & 2: Confidence Gating**: Ambiguous payees like 'HDFC' alone fail closed to **HIGH RISK (Unknown)** rather than hallucinating a category.*
  > 3. * **Amount Escalation**: High-value plans, such as Netflix Premium (`m10`), are automatically escalated to **MEDIUM RISK** regardless of confidence, disabling one-tap actions.*
  > 4. * **Mandatory Human Approval**: No debit is ever modified without explicit user authorization."*

### 5. Action (2:50 – 3:45)
* **Action**: Click "Run Autonomous Demo" on dashboard or run `python run.py --watch` to execute against the active session.
* **Speaker**:
  > *"Now watch the **ACT** phase in action. Real banks use dynamic obstacle courses. Mandate doesn't use brittle script coordinates; it runs an adaptive perceive-decide-act loop.*
  >
  > *Watch `m1`:*
  > * *It enters the manage screen and clicks 'Cancel autopay'.*
  > * *The bank attempts a retention trap: 'Get 3 months free before you go'. Mandate detects the retention state and deliberately chooses to decline.*
  > * *It lands on the confirmation modal, verifies the context, and clicks 'Yes, cancel'.*
  >
  > *Now look at `m10`:*
  > * *Here the bank presents an OTP challenge. Mandate classifies the OTP screen, inputs the verification code, targets the verify action, and clears the wall into confirmation.*
  > * *At every single step, Mandate logs: current URL, detected state, available actions, chosen action, and resulting URL."*

### 6. Verification (3:45 – 4:20)
* **Action**: Point to the `[3. VERIFY]` section of terminal output and dashboard badge update.
* **Speaker**:
  > *"Here is what makes Mandate truly production-grade: **VERIFY**.*
  >
  > *In high-stakes banking, 'the button was clicked' is NOT success. A bank UI can drop requests, lag, or fail silently.*
  >
  > *Our Verification Agent is deliberately distrustful. It completely discards the Action Agent's page context, opens an independent session, re-scrapes the mandate table, and checks the database.*
  >
  > *Only when the independent re-read proves the status transitioned from `ACTIVE` to `CANCELLED` does it issue `VerificationStatus.CONFIRMED`. If state remained active, it would immediately raise an alert rather than retrying blindly."*

### 7. Impact & Closing (4:20 – 5:00)
* **Speaker**:
  > *"To summarize: Mandate is not a toy subscription canceller.*
  >
  > *It is an architectural blueprint for safe, verified autonomous financial action. By combining deterministic safety boundaries with adaptive perception and zero-trust independent verification, Mandate proves that AI agents can be trusted with high-stakes execution in real financial systems.*
  >
  > *Thank you, and we look forward to your questions."*
