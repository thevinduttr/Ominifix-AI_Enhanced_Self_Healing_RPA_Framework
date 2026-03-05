"""
Failure Analyzer — Parse Playwright Error Traces

Parses raw Playwright traceback / error log text into a structured
failure_context dict compatible with the ELR JSON schema.

Supported Playwright error patterns:
  - TimeoutError / Timeout 30000ms exceeded
  - strict mode violation (selector matched multiple elements)
  - Element is not attached to the DOM
  - Element is not visible
  - Element is not enabled
  - Generic selector-not-found errors

Usage:
    from src.analyzer.failure_analyzer import FailureAnalyzer
    fa = FailureAnalyzer()
    ctx = fa.analyze(traceback_text)
    # ctx → {"error_type": ..., "old_locator": ..., "failing_line": ..., ...}
"""

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────

@dataclass
class FailureContext:
    """Structured failure context produced by the analyzer."""
    error_type: str = "ELEMENT_NOT_FOUND"
    error_message: str = ""
    old_locator: str = ""
    failing_line: int = 0
    action: str = ""
    script_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ──────────────────────────────────────────────────────────
# Regex Patterns for Playwright Errors
# ──────────────────────────────────────────────────────────

# Error type classifiers (order matters — first match wins)
ERROR_PATTERNS = [
    # TimeoutError: Timeout 30000ms exceeded.
    (
        re.compile(r"TimeoutError|Timeout\s+\d+ms\s+exceeded", re.IGNORECASE),
        "TIMEOUT_WAITING_FOR_SELECTOR",
    ),
    # strict mode violation: locator resolved to N elements
    (
        re.compile(r"strict\s+mode\s+violation", re.IGNORECASE),
        "STRICT_MODE_VIOLATION",
    ),
    # Element is not attached to the DOM
    (
        re.compile(r"not\s+attached\s+to\s+the\s+DOM", re.IGNORECASE),
        "DETACHED_FROM_DOM",
    ),
    # Element is not visible
    (
        re.compile(r"element\s+is\s+not\s+visible|not\s+visible", re.IGNORECASE),
        "NOT_VISIBLE",
    ),
    # Element is not enabled
    (
        re.compile(r"element\s+is\s+not\s+enabled|not\s+enabled", re.IGNORECASE),
        "NOT_ENABLED",
    ),
    # Element click intercepted
    (
        re.compile(r"click\s+intercepted|intercept", re.IGNORECASE),
        "ELEMENT_CLICK_INTERCEPTED",
    ),
    # Generic element not found
    (
        re.compile(r"element[\s_]not[\s_]found|no\s+element|could\s+not\s+find", re.IGNORECASE),
        "ELEMENT_NOT_FOUND",
    ),
]

# Patterns to extract the locator string from Playwright logs
LOCATOR_PATTERNS = [
    # waiting for selector "#abc" / selector 'div.class'  (double-quoted context)
    re.compile(r'waiting\s+for\s+selector\s+"([^"]+)"', re.IGNORECASE),
    # waiting for selector 'abc' (single-quoted context — allows inner double quotes)
    re.compile(r"waiting\s+for\s+selector\s+'([^']+)'", re.IGNORECASE),
    # locator("selector")
    re.compile(r'locator\(\s*"([^"]+)"\s*\)', re.IGNORECASE),
    re.compile(r"locator\(\s*'([^']+)'\s*\)", re.IGNORECASE),
    # page\.(click|fill|...)\("selector"
    re.compile(r'page\.\w+\(\s*"([^"]+)"\s*', re.IGNORECASE),
    re.compile(r"page\.\w+\(\s*'([^']+)'\s*", re.IGNORECASE),
    # selector "#abc" / selector 'abc'
    re.compile(r'selector\s+"([^"]+)"', re.IGNORECASE),
    re.compile(r"selector\s+'([^']+)'", re.IGNORECASE),
    # query_selector_all("selector")
    re.compile(r'query_selector(?:_all)?\(\s*"([^"]+)"\s*\)', re.IGNORECASE),
    re.compile(r"query_selector(?:_all)?\(\s*'([^']+)'\s*\)", re.IGNORECASE),
    # locator resolved to N elements (captures the locator from full log)
    re.compile(r'locator\s*"([^"]+)"\s*resolved\s+to', re.IGNORECASE),
    re.compile(r"locator\s*'([^']+)'\s*resolved\s+to", re.IGNORECASE),
]

# Extract line number from Python traceback
LINE_PATTERNS = [
    # "at script.py:42" or "script.py:42"
    re.compile(r'(?:at\s+)?([^\s:]+\.py):(\d+)', re.IGNORECASE),
    # "line 42" or "Line 42" or "line=42"
    re.compile(r'line\s*[=:]?\s*(\d+)', re.IGNORECASE),
    # File "path.py", line 42
    re.compile(r'File\s+"([^"]+)",\s*line\s+(\d+)', re.IGNORECASE),
]

# Extract action from Playwright calls
ACTION_PATTERNS = [
    re.compile(r'page\.(click|fill|type|press|check|uncheck|select_option|wait_for_selector|hover|dblclick|focus|tap)\s*\(', re.IGNORECASE),
    re.compile(r'locator\([^)]+\)\.(click|fill|type|press|check|uncheck|select_option|hover|dblclick|focus|tap)\s*\(', re.IGNORECASE),
    re.compile(r'(click|fill|type|press)(?:ing|ed)?\s+on\s+', re.IGNORECASE),
]


# ──────────────────────────────────────────────────────────
# FailureAnalyzer Class
# ──────────────────────────────────────────────────────────

class FailureAnalyzer:
    """
    Parse raw Playwright traceback / error log text into a structured
    failure_context dict compatible with the ELR JSON schema.

    Example:
        >>> fa = FailureAnalyzer()
        >>> ctx = fa.analyze('''
        ...     playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.
        ...     =========================== logs ===========================
        ...     waiting for selector "#btn-login" to be visible
        ...       at main.py:42
        ... ''')
        >>> ctx["error_type"]
        'TIMEOUT_WAITING_FOR_SELECTOR'
        >>> ctx["old_locator"]
        '#btn-login'
        >>> ctx["failing_line"]
        42
    """

    def analyze(self, log_text: str) -> dict:
        """
        Parse a raw Playwright error trace into structured failure_context.

        Args:
            log_text: Raw traceback/error log string from Playwright execution.

        Returns:
            dict with keys: error_type, error_message, old_locator, failing_line,
            action, script_path  — all compatible with ELR JSON schema.
        """
        if not log_text or not log_text.strip():
            return FailureContext(
                error_type="ELEMENT_NOT_FOUND",
                error_message="Empty error log provided",
            ).to_dict()

        ctx = FailureContext()

        # 1. Classify error type
        ctx.error_type = self._classify_error(log_text)

        # 2. Extract error message (first meaningful line)
        ctx.error_message = self._extract_error_message(log_text)

        # 3. Extract locator
        ctx.old_locator = self._extract_locator(log_text)

        # 4. Extract line number and script path
        line_info = self._extract_line_info(log_text)
        ctx.failing_line = line_info["line"]
        ctx.script_path = line_info["script"]

        # 5. Extract action
        ctx.action = self._extract_action(log_text)

        return ctx.to_dict()

    def analyze_with_context(
        self,
        log_text: str,
        script_path: Optional[str] = None,
        action: Optional[str] = None,
        failing_line: Optional[int] = None,
    ) -> dict:
        """
        Analyze with optional overrides for known context.

        Use this when the caller already knows some fields (e.g., from the
        bot that caught the exception) and wants the analyzer to fill in
        the rest from the traceback.
        """
        result = self.analyze(log_text)

        if script_path:
            result["script_path"] = script_path
        if action:
            result["action"] = action
        if failing_line and failing_line > 0:
            result["failing_line"] = failing_line

        return result

    # ──────────────────────────────────────────────────────
    # Private Extraction Methods
    # ──────────────────────────────────────────────────────

    def _classify_error(self, text: str) -> str:
        """Match error type from known Playwright patterns."""
        for pattern, error_type in ERROR_PATTERNS:
            if pattern.search(text):
                return error_type
        return "ELEMENT_NOT_FOUND"  # safe default

    def _extract_error_message(self, text: str) -> str:
        """Extract the most informative error message line."""
        lines = text.strip().splitlines()

        # Look for common Playwright error prefixes
        prefixes = [
            "TimeoutError:",
            "Error:",
            "playwright._impl._errors.",
            "strict mode violation",
            "Element is not",
        ]
        for line in lines:
            stripped = line.strip()
            for prefix in prefixes:
                if prefix.lower() in stripped.lower():
                    # Clean up the line
                    return stripped[:500]  # cap at 500 chars

        # Fallback: use first non-empty, non-separator line
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("=") and not stripped.startswith("-"):
                return stripped[:500]

        return text.strip()[:500]

    def _extract_locator(self, text: str) -> str:
        """Extract the CSS/XPath selector from the error trace."""
        for pattern in LOCATOR_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_line_info(self, text: str) -> dict:
        """Extract line number and script path from traceback."""
        result = {"line": 0, "script": ""}

        # Try "File 'path', line N" first (standard Python traceback)
        file_line_pattern = re.compile(r'File\s+"([^"]+)",\s*line\s+(\d+)')
        matches = list(file_line_pattern.finditer(text))
        if matches:
            # Use the last match (deepest in traceback = most relevant)
            last = matches[-1]
            result["script"] = last.group(1)
            result["line"] = int(last.group(2))
            return result

        # Try "at script.py:42"
        at_pattern = re.compile(r'(?:at\s+)?([^\s:]+\.py)\s*:\s*(\d+)')
        match = at_pattern.search(text)
        if match:
            result["script"] = match.group(1)
            result["line"] = int(match.group(2))
            return result

        # Try bare "line 42"
        line_pattern = re.compile(r'line\s*[=:]?\s*(\d+)', re.IGNORECASE)
        match = line_pattern.search(text)
        if match:
            result["line"] = int(match.group(1))

        return result

    def _extract_action(self, text: str) -> str:
        """Extract the Playwright action (click, fill, etc.) from the trace."""
        for pattern in ACTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).lower()
        return ""


# ──────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────

def main():
    """CLI for testing the FailureAnalyzer with sample traces."""
    import json
    import sys

    sample_traces = [
        # 1. TimeoutError
        """
playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.
=========================== logs ===========================
waiting for selector "#btn-login" to be visible
  at main.py:42
============================================================
        """,
        # 2. Strict mode violation
        """
Error: strict mode violation: locator("div.item") resolved to 5 elements
  File "scraper.py", line 78
Call log:
  - waiting for locator("div.item")
        """,
        # 3. Detached from DOM
        """
Error: Element is not attached to the DOM
  at page.click("#dynamic-element")
  File "automation.py", line 15
        """,
        # 4. Not visible
        """
Error: Element is not visible
  waiting for selector "[name='email']"
  File "form_filler.py", line 33
        """,
        # 5. Generic / unknown
        """
  File "unknown_bot.py", line 99
    page.fill("input#missing", "test")
RuntimeError: Could not find element matching selector
        """,
    ]

    fa = FailureAnalyzer()

    logger.info("=" * 70)
    logger.info("FAILURE ANALYZER \u2014 PARSE DEMO")
    logger.info("=" * 70)

    for i, trace in enumerate(sample_traces, 1):
        logger.info("\u2500" * 70)
        logger.info("TRACE #%d", i)
        logger.info("\u2500" * 70)
        logger.info("%s", trace.strip())
        logger.info("PARSED RESULT:")
        result = fa.analyze(trace)
        logger.info("%s", json.dumps(result, indent=2))

    logger.info("=" * 70)
    logger.info("ALL TRACES PARSED SUCCESSFULLY")
    logger.info("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
