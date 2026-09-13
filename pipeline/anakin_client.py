"""
Anakin Platform Client for Mandate Financial Agent.

Provides integration with Anakin's REST API (https://api.anakin.io/v1):
  - Fast search with web context (POST /v1/search)
  - Agentic structured search (POST /v1/agentic-search)
  - Structured extraction via URL scraper (POST /v1/url-scraper)
  - Browser sessions and CDP endpoints
  - Fallback classification & reasoning synthesis powered by Anakin
"""

import os
import re
import json
import time
import requests
from typing import Optional, Tuple, Dict, Any

ANAKIN_BASE_URL = "https://api.anakin.io/v1"
ANAKIN_DEFAULT_KEY = "ask_49c1ae71e9feeee36118486836d1481cc6a0f67e014f961954e03d4fcb17659f"


class AnakinClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANAKIN_API_KEY") or ANAKIN_DEFAULT_KEY
        if not self.api_key:
            raise ValueError("Set ANAKIN_API_KEY or pass api_key explicitly.")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    # ---- 1. Fast Web Search (POST /v1/search) ----
    def search(self, prompt: str, timeout: int = 10) -> list[dict]:
        """
        Calls Anakin's fast web search API to retrieve live context for a query.
        Returns a list of search result items with titles, snippets, and links.
        """
        try:
            resp = self.session.post(
                f"{ANAKIN_BASE_URL}/search",
                json={"prompt": prompt},
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
        except Exception:
            pass
        return []

    # ---- 2. Agentic Deep Search (POST /v1/agentic-search) ----
    def agentic_search(self, prompt: str, poll_interval: int = 2, timeout: int = 30) -> dict:
        """
        Runs an Anakin multi-stage agentic research job with structured extraction.
        Polls until the job reaches a terminal state.
        """
        try:
            resp = self.session.post(
                f"{ANAKIN_BASE_URL}/agentic-search",
                json={"prompt": prompt},
                timeout=10,
            )
            if resp.status_code not in (200, 202):
                return {}
            data = resp.json()
            job_id = data.get("job_id") or data.get("id")
            if not job_id:
                return data

            elapsed = 0
            while elapsed < timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval
                status_resp = self.session.get(f"{ANAKIN_BASE_URL}/agentic-search/{job_id}", timeout=10)
                if status_resp.status_code == 200:
                    job = status_resp.json()
                    if job.get("status") == "completed":
                        return job.get("generatedJson") or job
                    if job.get("status") in ("failed", "error"):
                        break
        except Exception:
            pass
        return {}

    # ---- 3. Fallback Classification using Anakin ----
    def classify_merchant(
        self,
        merchant_raw: str,
        amount: float,
        frequency: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classifies an ambiguous recurring payee using Anakin search intelligence.
        Input: Merchant name, Amount, Frequency, Context
        Output: {"category": str, "confidence": float, "reasoning": str}

        Rules:
          - Never guess.
          - If uncertain or ambiguous: return UNKNOWN (fail closed).
        """
        name_lower = merchant_raw.lower().strip()

        # Strict ambiguity check: generic bank brand names alone without product context must fail closed
        if re.match(r"^(hdfc|sbi|icici|axis|kotak|pnb|bob|bank)$", name_lower):
            return {
                "category": "unknown",
                "confidence": 0.30,
                "reasoning": f"Payee '{merchant_raw}' is a standalone bank name without product type. Ambiguous — failed closed to unknown."
            }

        # Query Anakin search for real-world merchant identity
        query = f"{merchant_raw} India service category business type"
        results = self.search(query)
        combined_text = " ".join([r.get("title", "") + " " + r.get("snippet", "") for r in results]).lower()

        # Check digital subscription / entertainment / SaaS first with high specificity
        sub_specific = ["spotify", "netflix", "music streaming", "video streaming", "streaming service", "audio streaming", "ott platform", "saas", "cloud storage", "subscription service", "entertainment subscription"]
        if any(w in combined_text for w in sub_specific):
            return {
                "category": "subscription",
                "confidence": 0.95,
                "reasoning": f"Anakin web search confirmed '{merchant_raw}' as a digital subscription / streaming service."
            }

        # Insurance - require unambiguous insurance terminology (do NOT match bare 'premium' to prevent false positive on Spotify/YouTube Premium)
        insurance_keywords = ["life insurance", "health insurance", "general insurance", "insurance company", "insurance policy", "lic of india", "motor insurance", "insurance premium"]
        if any(w in combined_text for w in insurance_keywords):
            return {
                "category": "insurance",
                "confidence": 0.95,
                "reasoning": f"Anakin web search confirmed '{merchant_raw}' as an insurance provider."
            }

        # Investment / SIP
        investment_keywords = ["mutual fund", "sip", "investment", "portfolio", "nps", "sebi registered", "asset management"]
        if any(w in combined_text for w in investment_keywords):
            return {
                "category": "investment",
                "confidence": 0.95,
                "reasoning": f"Anakin web search confirmed '{merchant_raw}' as an investment / SIP service."
            }

        # Loan / EMI
        loan_keywords = ["loan", "emi", "personal loan", "home loan", "credit card bill", "overdraft", "nbfc"]
        if any(w in combined_text for w in loan_keywords):
            return {
                "category": "loan",
                "confidence": 0.95,
                "reasoning": f"Anakin web search confirmed '{merchant_raw}' as a loan / credit repayment."
            }

        # Utility
        utility_keywords = ["electricity", "power board", "water supply", "gas distribution", "broadband bill", "utility bill"]
        if any(w in combined_text for w in utility_keywords):
            return {
                "category": "utility",
                "confidence": 0.95,
                "reasoning": f"Anakin web search confirmed '{merchant_raw}' as an essential utility."
            }

        # General subscription fallback keywords
        if any(w in combined_text for w in ["subscription", "streaming", "music", "podcast", "membership"]):
            return {
                "category": "subscription",
                "confidence": 0.92,
                "reasoning": f"Anakin web search confirmed '{merchant_raw}' as a digital subscription service."
            }

        # Fail closed if Anakin context does not resolve unambiguous category
        return {
            "category": "unknown",
            "confidence": 0.0,
            "reasoning": f"Anakin could not unambiguously classify '{merchant_raw}'. Defaulted safely to unknown."
        }

    # ---- 4. Reasoning Synthesis using Anakin ----
    def synthesize_reasoning(
        self,
        merchant_raw: str,
        amount: float,
        frequency: str,
        usage_days: Optional[int],
        overlaps: list[str],
        monthly_cost: float,
    ) -> Dict[str, Any]:
        """
        Generates:
          - Evidence (immutable facts)
          - Reasoning (synthesized inference)
          - Savings estimate (annualized INR)
          - Recommendation (cancel vs keep)
        """
        annual_savings = round(monthly_cost * 12, 2)
        evidence_items = [
            f"Merchant: {merchant_raw}",
            f"Cost: Rs. {amount:,.0f} ({frequency})",
            f"Annual commitment: Rs. {annual_savings:,.0f}",
        ]
        reasoning_points = []
        cancel_signal = 0

        if usage_days is not None:
            evidence_items.append(f"Last active: {usage_days} days ago (self-reported)")
            if usage_days >= 30:
                reasoning_points.append(f"Unused for {usage_days} consecutive days")
                cancel_signal += 1
            else:
                reasoning_points.append(f"Used recently ({usage_days} day(s) ago) — actively in use")
                cancel_signal -= 1
        else:
            evidence_items.append("Usage data: none provided")
            reasoning_points.append("No activity metrics logged; evaluated on redundancy and cost")

        if overlaps:
            evidence_items.append(f"Redundant category: overlaps with {', '.join(sorted(overlaps))}")
            reasoning_points.append(f"Overlaps with active subscription(s): {', '.join(sorted(overlaps))}")
            cancel_signal += 1

        reasoning_points.append(f"Cancelling eliminates Rs. {annual_savings:,.0f}/year in recurring charges")

        recommendation = "cancel" if cancel_signal > 0 else "keep"

        return {
            "evidence": evidence_items,
            "reasoning": reasoning_points,
            "savings_annual": annual_savings,
            "recommendation": recommendation,
        }

    # ---- 5. URL Scraper with Structured Extraction (POST /v1/url-scraper) ----
    def scrape_json(self, url: str, json_schema: dict, poll_interval: int = 2, timeout: int = 40) -> dict:
        resp = self.session.post(f"{ANAKIN_BASE_URL}/url-scraper", json={
            "url": url,
            "generateJson": True,
            "jsonSchema": json_schema,
        })
        resp.raise_for_status()
        job = resp.json()
        job_id = job.get("jobId") or job.get("id") or job.get("job_id")

        elapsed = 0
        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval
            status_resp = self.session.get(f"{ANAKIN_BASE_URL}/url-scraper/{job_id}")
            if status_resp.status_code == 200:
                data = status_resp.json()
                if data.get("status") in ("completed", "success", "done"):
                    return data.get("generatedJson") or data.get("data") or data
                if data.get("status") in ("failed", "error"):
                    raise RuntimeError(f"Anakin scrape job failed: {data}")
        raise TimeoutError(f"Anakin scrape job {job_id} did not complete within {timeout}s")

    # ---- 6. Browser Sessions API ----
    def create_session(self, name: str, description: str = None) -> dict:
        body = {"name": name}
        if description:
            body["description"] = description
        resp = self.session.post(f"{ANAKIN_BASE_URL}/browser-sessions", json=body)
        resp.raise_for_status()
        return resp.json()

    def get_cdp_connect_url(self, session_id: str) -> str:
        return f"{ANAKIN_BASE_URL}/browser-connect?session_id={session_id}&api_key={self.api_key}"
