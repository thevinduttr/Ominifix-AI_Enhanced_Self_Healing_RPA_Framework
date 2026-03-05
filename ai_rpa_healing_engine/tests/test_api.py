"""
Tests for the Code Healing Engine REST API.

Uses FastAPI's TestClient (backed by httpx) — no real server needed.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


# ──────────────────────────────────────────────
# Fixtures — minimal & full ELR payloads
# ──────────────────────────────────────────────
MINIMAL_ELR = {
    "metadata": {
        "bot_id": "BOT-API-TEST-01",
        "run_id": "api-test-001",
    },
    "failure_context": {
        "script_path": "data/scripts/broken/search_flow.py",
        "failing_line": 12,
        "action": "click",
        "old_locator": "#old-btn",
        "error_type": "ELEMENT_NOT_FOUND",
    },
    "dom_context": {
        "new_element_html": '<button id="new-btn" class="btn">Click Me</button>',
    },
}

FULL_ELR = {
    "metadata": {
        "schema_version": "1.0",
        "report_id": "ELR-API-TEST-001",
        "run_id": "api-test-002",
        "bot_id": "BOT-API-TEST-02",
        "timestamp": "2026-03-05T14:00:00Z",
        "source_component": "element_locator_engine",
        "target_component": "code_healing_engine",
        "environment": "qa",
    },
    "failure_context": {
        "script_path": "data/scripts/broken/search_flow.py",
        "failing_line": 12,
        "action": "click",
        "old_locator": "#old-selector",
        "error_type": "ELEMENT_NOT_FOUND",
        "error_message": "Timeout 30000ms exceeded",
    },
    "dom_context": {
        "new_element_html": '<button id="submit-btn" class="btn primary" data-testid="submit">Submit</button>',
        "page_url": "https://example.com/form",
        "page_name": "Form Page",
    },
    "element_expectation": {
        "expected_role": "button",
        "expected_text": "Submit",
    },
    "element_candidate": {
        "css": "#submit-btn",
        "xpath": "//button[@id='submit-btn']",
        "full_xpath": "/html/body/div/button",
        "score": 85,
        "strategy": "attribute_match",
    },
}

# A mock healing output dict to return from heal_from_dict
MOCK_HEAL_OUTPUT = {
    "metadata": {
        "healing_id": "HEAL-mock-uuid",
        "report_id": "ELR-API-TEST-001",
        "run_id": "api-test-001",
        "bot_id": "BOT-API-TEST-01",
        "timestamp": "2026-03-05T14:00:05",
        "source_component": "code_healing_engine",
        "target_component": "predictive_testing_engine",
    },
    "failure_context": {
        "script_path": "data/scripts/broken/search_flow.py",
        "failing_line": 12,
        "action": "click",
        "old_locator": "#old-btn",
        "error_type": "ELEMENT_NOT_FOUND",
        "error_message": "",
    },
    "dom_context": {
        "page_url": "",
        "page_name": "",
        "new_element_html": '<button id="new-btn" class="btn">Click Me</button>',
    },
    "element_expectation": {
        "expected_role": "",
        "expected_text": "",
    },
    "element_candidate": None,
    "healing_summary": {
        "status": "SUCCESS",
        "strategy_used": "LOCATOR_REGEN_LIBCST",
        "action": "click",
        "old_locator": "#old-btn",
        "new_locator": "#new-btn",
        "confidence": 0.85,
        "patcher": "LibCST",
        "validation": {"valid": True, "reason": "OK"},
    },
    "script_output": {
        "original_script_path": "data/scripts/broken/search_flow.py",
        "healed_script_path": "data/scripts/healed/BOT-API-TEST-01/search_flow_healed.py",
    },
    "model_info": {
        "model": "strategy_selector_v1",
        "confidence": 0.85,
    },
}

MOCK_NOFIX_OUTPUT = {
    **MOCK_HEAL_OUTPUT,
    "healing_summary": {
        **MOCK_HEAL_OUTPUT["healing_summary"],
        "status": "NO_FIX",
        "strategy_used": "NO_FIX",
        "new_locator": "",
        "confidence": 0.0,
    },
}


# ══════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════
class TestHealthEndpoint:
    """GET /api/v1/health"""

    def test_health_returns_ok(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["component"] == "code_healing_engine"
        assert "version" in body

    def test_health_wrong_method(self):
        resp = client.post("/api/v1/health")
        assert resp.status_code == 405


# ══════════════════════════════════════════════
# Single Heal
# ══════════════════════════════════════════════
class TestHealSingleEndpoint:
    """POST /api/v1/heal"""

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_heal_success(self, mock_heal):
        resp = client.post("/api/v1/heal", json=MINIMAL_ELR)
        assert resp.status_code == 200
        body = resp.json()
        assert body["healing_summary"]["status"] == "SUCCESS"
        assert body["healing_summary"]["new_locator"] == "#new-btn"
        assert body["metadata"]["bot_id"] == "BOT-API-TEST-01"
        mock_heal.assert_called_once()

    @patch("src.api.app.heal_from_dict", return_value=MOCK_NOFIX_OUTPUT)
    def test_heal_nofix(self, mock_heal):
        resp = client.post("/api/v1/heal", json=MINIMAL_ELR)
        assert resp.status_code == 200
        body = resp.json()
        assert body["healing_summary"]["status"] == "NO_FIX"

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_heal_full_elr(self, mock_heal):
        resp = client.post("/api/v1/heal", json=FULL_ELR)
        assert resp.status_code == 200
        body = resp.json()
        assert body["healing_summary"]["status"] == "SUCCESS"

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_heal_with_element_candidate(self, mock_heal):
        resp = client.post("/api/v1/heal", json=FULL_ELR)
        assert resp.status_code == 200
        # Verify the dict passed to heal_from_dict includes element_candidate
        call_args = mock_heal.call_args[0][0]
        assert "element_candidate" in call_args

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_heal_without_element_candidate(self, mock_heal):
        """element_candidate is optional — should work without it."""
        resp = client.post("/api/v1/heal", json=MINIMAL_ELR)
        assert resp.status_code == 200

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_heal_null_element_candidate(self, mock_heal):
        """Null element_candidate should be handled gracefully."""
        elr = {**FULL_ELR, "element_candidate": None}
        resp = client.post("/api/v1/heal", json=elr)
        assert resp.status_code == 200

    def test_heal_missing_metadata(self):
        """Missing required field → 422."""
        bad_input = {"failure_context": MINIMAL_ELR["failure_context"]}
        resp = client.post("/api/v1/heal", json=bad_input)
        assert resp.status_code == 422

    def test_heal_missing_failure_context(self):
        bad_input = {"metadata": MINIMAL_ELR["metadata"]}
        resp = client.post("/api/v1/heal", json=bad_input)
        assert resp.status_code == 422

    def test_heal_missing_dom_context(self):
        bad_input = {
            "metadata": MINIMAL_ELR["metadata"],
            "failure_context": MINIMAL_ELR["failure_context"],
        }
        resp = client.post("/api/v1/heal", json=bad_input)
        assert resp.status_code == 422

    def test_heal_empty_body(self):
        resp = client.post("/api/v1/heal", json={})
        assert resp.status_code == 422

    def test_heal_no_body(self):
        resp = client.post("/api/v1/heal")
        assert resp.status_code == 422

    @patch("src.api.app.heal_from_dict", side_effect=RuntimeError("Engine crashed"))
    def test_heal_engine_error_returns_500(self, mock_heal):
        resp = client.post("/api/v1/heal", json=MINIMAL_ELR)
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"]["error"] == "HEALING_ENGINE_ERROR"
        assert "Engine crashed" in body["detail"]["message"]

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_response_has_all_sections(self, mock_heal):
        resp = client.post("/api/v1/heal", json=MINIMAL_ELR)
        body = resp.json()
        required_sections = [
            "metadata", "failure_context", "dom_context",
            "healing_summary", "script_output", "model_info",
        ]
        for section in required_sections:
            assert section in body, f"Missing section: {section}"

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_response_content_type_json(self, mock_heal):
        resp = client.post("/api/v1/heal", json=MINIMAL_ELR)
        assert resp.headers["content-type"] == "application/json"


# ══════════════════════════════════════════════
# Batch Heal
# ══════════════════════════════════════════════
class TestHealBatchEndpoint:
    """POST /api/v1/heal/batch"""

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_batch_single_item(self, mock_heal):
        resp = client.post("/api/v1/heal/batch", json={"inputs": [MINIMAL_ELR]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["success"] == 1
        assert len(body["results"]) == 1

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_batch_multiple_items(self, mock_heal):
        resp = client.post(
            "/api/v1/heal/batch",
            json={"inputs": [MINIMAL_ELR, FULL_ELR, MINIMAL_ELR]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["success"] == 3
        assert len(body["results"]) == 3

    @patch("src.api.app.heal_from_dict")
    def test_batch_mixed_results(self, mock_heal):
        mock_heal.side_effect = [MOCK_HEAL_OUTPUT, MOCK_NOFIX_OUTPUT]
        resp = client.post(
            "/api/v1/heal/batch",
            json={"inputs": [MINIMAL_ELR, MINIMAL_ELR]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["success"] == 1
        assert body["no_fix"] == 1

    def test_batch_empty_inputs(self):
        resp = client.post("/api/v1/heal/batch", json={"inputs": []})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["results"] == []

    @patch("src.api.app.heal_from_dict", side_effect=RuntimeError("boom"))
    def test_batch_engine_error_counted_as_failed(self, mock_heal):
        resp = client.post("/api/v1/heal/batch", json={"inputs": [MINIMAL_ELR]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["failed"] == 1

    def test_batch_no_inputs_field(self):
        resp = client.post("/api/v1/heal/batch", json={})
        assert resp.status_code == 422

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_batch_response_structure(self, mock_heal):
        resp = client.post("/api/v1/heal/batch", json={"inputs": [MINIMAL_ELR]})
        body = resp.json()
        assert "total" in body
        assert "success" in body
        assert "no_fix" in body
        assert "failed" in body
        assert "results" in body
        assert isinstance(body["results"], list)


# ══════════════════════════════════════════════
# Edge Cases & OpenAPI Docs
# ══════════════════════════════════════════════
class TestAPIEdgeCases:

    def test_404_unknown_route(self):
        resp = client.get("/api/v1/unknown")
        assert resp.status_code == 404

    def test_openapi_docs_accessible(self):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json_accessible(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/api/v1/heal" in schema["paths"]
        assert "/api/v1/heal/batch" in schema["paths"]
        assert "/api/v1/health" in schema["paths"]

    @patch("src.api.app.heal_from_dict", return_value=MOCK_HEAL_OUTPUT)
    def test_extra_fields_ignored(self, mock_heal):
        """Extra fields in input should not cause errors."""
        elr = {
            **MINIMAL_ELR,
            "custom_field": "should be ignored",
            "another_extra": 42,
        }
        resp = client.post("/api/v1/heal", json=elr)
        assert resp.status_code == 200
