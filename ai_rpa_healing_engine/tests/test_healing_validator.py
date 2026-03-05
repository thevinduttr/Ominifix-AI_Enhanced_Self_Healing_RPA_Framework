"""
Tests for HealingValidator — syntax validation of healed scripts.

Tests:
  - Valid Python file → valid: True
  - File with SyntaxError → valid: False
  - Missing file → valid: False
  - Empty file → valid: True (empty is valid Python)
"""

import pytest
import tempfile
from pathlib import Path

from src.engine.healing_validator import HealingValidator


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


class TestValidScript:
    def test_valid_python_returns_true(self, tmp_dir):
        script = tmp_dir / "valid.py"
        script.write_text('print("hello world")\n', encoding="utf-8")

        result = HealingValidator.validate_script(str(script))
        assert result["valid"] is True
        assert result["reason"] == "OK"

    def test_valid_complex_script(self, tmp_dir):
        code = '''from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com")
        page.fill("#search", "test")
        browser.close()

if __name__ == "__main__":
    run()
'''
        script = tmp_dir / "complex.py"
        script.write_text(code, encoding="utf-8")

        result = HealingValidator.validate_script(str(script))
        assert result["valid"] is True

    def test_empty_file_is_valid(self, tmp_dir):
        script = tmp_dir / "empty.py"
        script.write_text("", encoding="utf-8")

        result = HealingValidator.validate_script(str(script))
        assert result["valid"] is True


class TestInvalidScript:
    def test_syntax_error_returns_false(self, tmp_dir):
        script = tmp_dir / "syntax_err.py"
        script.write_text('def broken(\n    print("unclosed"\n', encoding="utf-8")

        result = HealingValidator.validate_script(str(script))
        assert result["valid"] is False
        assert "SyntaxError" in result["reason"]

    def test_unclosed_paren_detected(self, tmp_dir):
        script = tmp_dir / "unclosed.py"
        script.write_text('page.fill("selector", "value"\n', encoding="utf-8")

        result = HealingValidator.validate_script(str(script))
        assert result["valid"] is False

    def test_indentation_error_detected(self, tmp_dir):
        script = tmp_dir / "indent.py"
        script.write_text('def foo():\nprint("bad indent")\n', encoding="utf-8")

        result = HealingValidator.validate_script(str(script))
        assert result["valid"] is False


class TestMissingFile:
    def test_missing_file_returns_false(self, tmp_dir):
        result = HealingValidator.validate_script(str(tmp_dir / "nonexistent.py"))
        assert result["valid"] is False
        assert "not found" in result["reason"]
