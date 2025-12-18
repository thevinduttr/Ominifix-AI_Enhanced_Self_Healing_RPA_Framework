from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatchResult:
    status: str  # "SUCCESS" | "FAILED"
    message: str
    old_locator: str | None = None
    new_locator: str | None = None
    healed_script_path: str | None = None


class ScriptPatcher:
    """
    v1 patcher: Safe string replacement with a line-number guard.
    - Reads script file
    - Checks failing line contains old_locator (guard)
    - Replaces old_locator -> new_locator (first occurrence in that line; fallback: whole file)
    - Writes healed script to output_path
    """

    def patch_locator(
        self,
        script_path: str,
        output_path: str,
        failing_line: int,
        old_locator: str,
        new_locator: str,
    ) -> PatchResult:
        sp = Path(script_path)
        if not sp.exists():
            return PatchResult(status="FAILED", message=f"Script not found: {script_path}")

        text = sp.read_text(encoding="utf-8")
        lines = text.splitlines()

        if failing_line <= 0 or failing_line > len(lines):
            return PatchResult(
                status="FAILED",
                message=f"Invalid failing_line={failing_line}. Script has {len(lines)} lines.",
                old_locator=old_locator,
                new_locator=new_locator,
            )

        idx = failing_line - 1
        target = lines[idx]

        # Guard: ensure line contains the old locator
        if old_locator not in target:
            # Fallback: try replacing in entire file (still safe but less precise)
            if old_locator not in text:
                return PatchResult(
                    status="FAILED",
                    message="Old locator not found in script (line guard and global search failed).",
                    old_locator=old_locator,
                    new_locator=new_locator,
                )

            safe_locator = self._safe_python_string(new_locator)
            healed_text = text.replace(old_locator, safe_locator, 1)
        else:
            # Replace only in the failing line first
            safe_locator = self._safe_python_string(new_locator)
            lines[idx] = target.replace(old_locator, safe_locator, 1)

            healed_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")

        outp = Path(output_path)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(healed_text, encoding="utf-8")

        return PatchResult(
            status="SUCCESS",
            message="Locator patched successfully.",
            old_locator=old_locator,
            new_locator=new_locator,
            healed_script_path=str(outp),
        )

    def _safe_python_string(self, s: str) -> str:
        """
        Convert a raw locator string into a valid Python string literal.
        If already quoted, return as-is.
        """
        s = s.strip()

        # Already a Python string literal
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            return s

        # Wrap using single quotes, escape inner single quotes
        return "'" + s.replace("'", "\\'") + "'"


