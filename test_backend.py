"""
Comprehensive automated tests for Mandate AI Agent backend & pipeline.
Validates canonical and API routes, Anakin fallback classification, and safety invariants.
"""
from fastapi.testclient import TestClient
from server import app
from pipeline.layer2_llm import classify_layer2
from data.mandate_schema import Category

client = TestClient(app)


def test_anakin_classification():
    print("\n--- TEST: ANAKIN LAYER 2 FALLBACK CLASSIFICATION ---")
    # Test unambiguous merchant
    cat, conf, reason = classify_layer2("Spotify India", 299, "monthly")
    print(f"  Spotify -> Cat: {cat.value}, Conf: {conf}, Reason: {reason}")
    assert cat in (Category.SUBSCRIPTION, Category.UNKNOWN)

    # Test ambiguous merchant: "HDFC" alone must fail closed to UNKNOWN
    cat_amb, conf_amb, reason_amb = classify_layer2("HDFC", 2500, "monthly")
    print(f"  HDFC -> Cat: {cat_amb.value}, Conf: {conf_amb}, Reason: {reason_amb}")
    assert cat_amb == Category.UNKNOWN
    assert conf_amb < 0.90
    print("[PASS] Anakin fallback classification adheres to fail-closed safety policy")


def test_api_mandates():
    print("\n--- TEST: MANDATES ENDPOINTS (Canonical /mandates and /api/mandates) ---")
    for endpoint in ["/mandates", "/api/mandates"]:
        resp = client.get(endpoint)
        assert resp.status_code == 200
        mandates = resp.json()["mandates"]
        assert len(mandates) >= 10
        print(f"[PASS] GET {endpoint} returned {len(mandates)} mandates")

    # Inspect enriched fields on mandates
    m1 = next(m for m in mandates if m["id"] == "m1")
    assert m1["risk_level"] == "low"
    assert m1["recommendation"] == "cancel"
    assert "Unused for 47 consecutive days" in str(m1["reasoning"])
    print("[PASS] m1 (Spotify) contains Anakin reasoning and cancel recommendation")

    # Check protected
    m4 = next(m for m in mandates if m["id"] == "m4")
    assert m4["is_protected"] is True
    assert m4["risk_level"] == "critical"
    assert m4["recommendation"] is None
    print("[PASS] m4 (LIC) locked as CRITICAL risk with null recommendation")

    # Check high risk utility
    m8 = next(m for m in mandates if m["id"] == "m8")
    assert m8["risk_level"] == "high"
    assert m8["category"] == "utility"
    print("[PASS] m8 (Electricity) classified as HIGH risk utility")

    # Check ambiguous merchant
    m9 = next(m for m in mandates if m["id"] == "m9")
    assert m9["risk_level"] == "high"
    assert m9["category"] == "unknown"
    print("[PASS] m9 (HDFC alone) confidence gated to HIGH risk unknown")

    # Check amount escalation
    m10 = next(m for m in mandates if m["id"] == "m10")
    assert m10["risk_level"] == "medium"
    assert "High value subscription" in str(m10["reasoning"])
    print("[PASS] m10 (Netflix) escalated to MEDIUM risk")


def test_safety_guardrails():
    print("\n--- TEST: PRE-FLIGHT SAFETY GUARDRAILS (/cancel and /api/cancel) ---")
    for endpoint in ["/cancel", "/api/cancel"]:
        # 1. Protected merchant cancellation must fail with 403
        r_m4 = client.post(endpoint, json={"mandate_id": "m4"})
        assert r_m4.status_code == 403
        assert "PROTECTED" in r_m4.json()["detail"]
        print(f"[PASS] {endpoint}: Blocked protected merchant m4 -> {r_m4.json()['detail']}")

        # 2. High risk merchant cancellation must fail with 403
        r_m8 = client.post(endpoint, json={"mandate_id": "m8"})
        assert r_m8.status_code == 403
        assert "HIGH RISK" in r_m8.json()["detail"]
        print(f"[PASS] {endpoint}: Blocked high-risk merchant m8 -> {r_m8.json()['detail']}")

        # 3. Medium risk amount escalation requires explicit override
        r_m10_no_force = client.post(endpoint, json={"mandate_id": "m10", "force_medium": False})
        assert r_m10_no_force.status_code == 400
        assert "AMOUNT ESCALATION" in r_m10_no_force.json()["detail"]
        print(f"[PASS] {endpoint}: Blocked high-value subscription m10 without override -> {r_m10_no_force.json()['detail']}")


def test_status_endpoint():
    print("\n--- TEST: STATUS ENDPOINTS (/status/{id} and /api/status/{id}) ---")
    for endpoint in ["/status/m1", "/api/status/m1"]:
        r = client.get(endpoint)
        assert r.status_code == 200
        d = r.json()
        assert d.get("found") is True
        print(f"[PASS] GET {endpoint} returned status for '{d.get('merchant')}'")


if __name__ == "__main__":
    print("==========================================================")
    print(" MANDATE SERVER & PIPELINE INTEGRATION TEST SUITE")
    print("==========================================================")
    test_anakin_classification()
    test_api_mandates()
    test_safety_guardrails()
    test_status_endpoint()
    print("\n==========================================================")
    print(" ALL BACKEND, ROUTE & SAFETY INVARIANTS VERIFIED!")
    print("==========================================================\n")
