"""
Tests for FailureAnalyzer — Playwright traceback parsing.

Tests:
  - Parse a known Playwright TimeoutError traceback
  - Parse strict mode violation error
  - Parse element not visible error
  - Parse element not attached to DOM
  - Parse element not enabled
  - Unknown error type returns safe defaults
  - Empty input returns defaults
  - Locator extraction from various formats
"""

import pytest

from src.analyzer.failure_analyzer import FailureAnalyzer


@pytest.fixture
def analyzer():
    return FailureAnalyzer()


# ── TimeoutError ──

TIMEOUT_TRACE = """Traceback (most recent call last):
  File "data/scripts/broken/search_flow.py", line 12, in run
    page.fill("input[name='search_query_BROKEN']", "SLIIT")
playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.
Call log:
  - waiting for selector "input[name='search_query_BROKEN']"
"""


class TestTimeoutError:
    def test_parses_timeout_error_type(self, analyzer):
        ctx = analyzer.analyze(TIMEOUT_TRACE)
        assert ctx["error_type"] == "TIMEOUT_WAITING_FOR_SELECTOR"

    def test_extracts_locator(self, analyzer):
        ctx = analyzer.analyze(TIMEOUT_TRACE)
        assert ctx["old_locator"] == "input[name='search_query_BROKEN']"

    def test_extracts_failing_line(self, analyzer):
        ctx = analyzer.analyze(TIMEOUT_TRACE)
        assert ctx["failing_line"] == 12

    def test_extracts_action(self, analyzer):
        ctx = analyzer.analyze(TIMEOUT_TRACE)
        assert ctx["action"] == "fill"


# ── Strict Mode Violation ──

STRICT_TRACE = """playwright._impl._errors.Error: strict mode violation: locator("div.item") resolved to 5 elements:
    1) <div class="item">First</div>
    2) <div class="item">Second</div>
"""


class TestStrictMode:
    def test_parses_strict_mode(self, analyzer):
        ctx = analyzer.analyze(STRICT_TRACE)
        assert ctx["error_type"] == "STRICT_MODE_VIOLATION"


# ── Not Visible ──

NOT_VISIBLE_TRACE = """Error: Element is not visible
  waiting for selector "#hidden-btn"
  at Object.click (/node_modules/playwright-core/lib/frames.js:123:45)
"""


class TestNotVisible:
    def test_parses_not_visible(self, analyzer):
        ctx = analyzer.analyze(NOT_VISIBLE_TRACE)
        assert ctx["error_type"] == "NOT_VISIBLE"

    def test_extracts_locator_from_not_visible(self, analyzer):
        ctx = analyzer.analyze(NOT_VISIBLE_TRACE)
        assert ctx["old_locator"] == "#hidden-btn"


# ── Detached from DOM ──

DETACHED_TRACE = """Error: Element is not attached to the DOM
  at Object.fill (/node_modules/playwright-core/lib/frames.js:456:78)
  selector: input#dynamic_field
"""


class TestDetachedFromDOM:
    def test_parses_detached(self, analyzer):
        ctx = analyzer.analyze(DETACHED_TRACE)
        assert ctx["error_type"] == "DETACHED_FROM_DOM"


# ── Not Enabled ──

NOT_ENABLED_TRACE = """Error: Element is not enabled
  waiting for selector "button#disabled_btn"
"""


class TestNotEnabled:
    def test_parses_not_enabled(self, analyzer):
        ctx = analyzer.analyze(NOT_ENABLED_TRACE)
        assert ctx["error_type"] == "NOT_ENABLED"


# ── Safe Defaults ──

class TestSafeDefaults:
    def test_unknown_error_returns_element_not_found(self, analyzer):
        ctx = analyzer.analyze("Some random error message without known patterns")
        assert ctx["error_type"] == "ELEMENT_NOT_FOUND"

    def test_empty_input_returns_defaults(self, analyzer):
        ctx = analyzer.analyze("")
        assert isinstance(ctx, dict)
        assert ctx["error_type"] == "ELEMENT_NOT_FOUND"
        assert ctx["old_locator"] == ""
        assert ctx["failing_line"] == 0

    def test_none_handled_gracefully(self, analyzer):
        """Passing None should not crash."""
        ctx = analyzer.analyze(None)
        assert isinstance(ctx, dict)


# ── Locator Extraction Formats ──

class TestLocatorExtraction:
    def test_double_quoted_selector(self, analyzer):
        trace = 'waiting for selector "button#myBtn"'
        ctx = analyzer.analyze(trace)
        assert ctx["old_locator"] == "button#myBtn"

    def test_single_quoted_selector(self, analyzer):
        trace = "waiting for selector 'input[name=\"email\"]'"
        ctx = analyzer.analyze(trace)
        assert ctx["old_locator"] != ""

    def test_page_fill_locator_extraction(self, analyzer):
        trace = '''  File "script.py", line 15, in run
    page.fill("#search_box_old", "query")
playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.'''
        ctx = analyzer.analyze(trace)
        # Should extract locator from either call log or page.fill line
        assert ctx["failing_line"] == 15
        assert ctx["error_type"] == "TIMEOUT_WAITING_FOR_SELECTOR"


# ── to_dict (analyze already returns dict) ──

class TestToDict:
    def test_result_contains_all_fields(self, analyzer):
        ctx = analyzer.analyze(TIMEOUT_TRACE)
        assert "error_type" in ctx
        assert "old_locator" in ctx
        assert "failing_line" in ctx
        assert "action" in ctx
        assert "error_message" in ctx
        assert "script_path" in ctx
