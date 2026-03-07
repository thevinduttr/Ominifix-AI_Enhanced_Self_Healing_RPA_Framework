"""
Tests for ScriptPatcher (LibCST-based) — locator patching validation.

Tests:
  - Successful LibCST patch on a known fill() script
  - Successful patch on a click() script
  - Fallback line-patch when LibCST fails
  - Failure returns PatchResult(status="FAILED")
  - Unsupported action rejected
  - Missing script file returns FAILED
"""

import pytest
import tempfile
from pathlib import Path

from src.patcher.libcst_patcher import ScriptPatcher, PatchResult


@pytest.fixture
def patcher():
    return ScriptPatcher()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


def _write_script(tmp_dir: Path, name: str, code: str) -> Path:
    """Helper to write a script and return its path."""
    p = tmp_dir / name
    p.write_text(code, encoding="utf-8")
    return p


FILL_SCRIPT = '''from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com")

        # Fill the search box
        page.fill("input[name='search_old']", "test query")

        browser.close()


if __name__ == "__main__":
    run()
'''

CLICK_SCRIPT = '''from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com")

        # Click the submit button
        page.click("#submit_old")

        browser.close()


if __name__ == "__main__":
    run()
'''


class TestSuccessfulPatch:
    def test_fill_action_patched(self, patcher, tmp_dir):
        script = _write_script(tmp_dir, "fill_test.py", FILL_SCRIPT)
        output = tmp_dir / "fill_healed.py"

        result = patcher.patch_locator(
            script_path=str(script),
            output_path=str(output),
            failing_line=12,
            old_locator="input[name='search_old']",
            new_locator="#search",
            action="fill",
        )

        assert result.status == "SUCCESS"
        assert result.healed_script_path is not None
        healed = Path(result.healed_script_path).read_text(encoding="utf-8")
        assert "#search" in healed
        assert "search_old" not in healed

    def test_click_action_patched(self, patcher, tmp_dir):
        script = _write_script(tmp_dir, "click_test.py", CLICK_SCRIPT)
        output = tmp_dir / "click_healed.py"

        result = patcher.patch_locator(
            script_path=str(script),
            output_path=str(output),
            failing_line=12,
            old_locator="#submit_old",
            new_locator="#submitBtn",
            action="click",
        )

        assert result.status == "SUCCESS"
        healed = Path(result.healed_script_path).read_text(encoding="utf-8")
        assert "#submitBtn" in healed
        assert "#submit_old" not in healed

    def test_healed_script_is_valid_python(self, patcher, tmp_dir):
        script = _write_script(tmp_dir, "valid_test.py", FILL_SCRIPT)
        output = tmp_dir / "valid_healed.py"

        result = patcher.patch_locator(
            script_path=str(script),
            output_path=str(output),
            failing_line=12,
            old_locator="input[name='search_old']",
            new_locator='input[name="q"]',
            action="fill",
        )

        assert result.status == "SUCCESS"
        healed_code = Path(result.healed_script_path).read_text(encoding="utf-8")
        # Should compile without errors
        compile(healed_code, "<healed>", "exec")


class TestPatchFailures:
    def test_unsupported_action_returns_failed(self, patcher, tmp_dir):
        script = _write_script(tmp_dir, "unsupported.py", FILL_SCRIPT)
        output = tmp_dir / "unsupported_healed.py"

        result = patcher.patch_locator(
            script_path=str(script),
            output_path=str(output),
            failing_line=12,
            old_locator="input[name='search_old']",
            new_locator="#search",
            action="drag_and_drop",
        )

        assert result.status == "FAILED"
        assert "Unsupported action" in result.message

    def test_missing_script_returns_failed(self, patcher, tmp_dir):
        output = tmp_dir / "missing_healed.py"

        result = patcher.patch_locator(
            script_path=str(tmp_dir / "nonexistent.py"),
            output_path=str(output),
            failing_line=12,
            old_locator="#old",
            new_locator="#new",
            action="fill",
        )

        assert result.status == "FAILED"
        assert "not found" in result.message

    def test_wrong_failing_line_returns_failed(self, patcher, tmp_dir):
        script = _write_script(tmp_dir, "wrong_line.py", FILL_SCRIPT)
        output = tmp_dir / "wrong_line_healed.py"

        # Line 5 doesn't have a fill() call
        result = patcher.patch_locator(
            script_path=str(script),
            output_path=str(output),
            failing_line=5,
            old_locator="NONEXISTENT_LOCATOR",
            new_locator="#search",
            action="fill",
        )

        assert result.status == "FAILED"


class TestPatchResult:
    def test_patch_result_fields(self):
        pr = PatchResult(
            status="SUCCESS",
            message="Patched successfully",
            old_locator="#old",
            new_locator="#new",
            healed_script_path="/path/to/healed.py",
        )
        assert pr.status == "SUCCESS"
        assert pr.old_locator == "#old"
        assert pr.new_locator == "#new"

    def test_patch_result_defaults(self):
        pr = PatchResult(status="FAILED", message="error")
        assert pr.old_locator is None
        assert pr.new_locator is None
        assert pr.healed_script_path is None
