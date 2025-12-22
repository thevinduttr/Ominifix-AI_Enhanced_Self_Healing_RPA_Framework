from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import libcst as cst
import libcst.matchers as m


@dataclass
class PatchResult:
    status: str
    message: str
    old_locator: str | None = None
    new_locator: str | None = None
    healed_script_path: str | None = None


class _FillLocatorTransformer(cst.CSTTransformer):
    def __init__(self, failing_line: int | None, old_locator: str | None, new_locator: str):
        self.failing_line = failing_line
        self.old_locator = old_locator
        self.new_locator = new_locator

        self.patched = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """
        Patch page.fill(<locator>, ...) -> replace locator argument only.
        Preserve formatting by returning a modified CST node.
        """

        # Match ".fill(...)" call
        if not m.matches(updated_node.func, m.Attribute(attr=m.Name("fill"))):
            return updated_node

        if not updated_node.args:
            return updated_node

        # Best effort: locate node position (line) if failing_line provided
        # We will use metadata provider in wrapper function (see ScriptPatcher below)

        # Try match by old locator string value first (stable)
        first_arg = updated_node.args[0].value

        if self.old_locator is not None:
            # old locator could appear as "..." or '...'
            if isinstance(first_arg, cst.SimpleString):
                raw = first_arg.evaluated_value  # unquoted python string value
                if raw == self.old_locator:
                    new_str = cst.SimpleString(repr(self.new_locator))
                    self.patched = True
                    return updated_node.with_changes(
                        args=[updated_node.args[0].with_changes(value=new_str)] + list(updated_node.args[1:])
                    )

        # If no old_locator match, we patch the first fill() at failing_line (if line info is available)
        return updated_node


class ScriptPatcher:
    """
    LibCST patcher:
      - preserves blank lines, comments, spacing
      - patches the selector string literal without reformatting the file
    """

    def patch_locator(
        self,
        script_path: str,
        output_path: str,
        failing_line: int | None,
        old_locator: str | None,
        new_locator: str,
    ) -> PatchResult:
        sp = Path(script_path)
        if not sp.exists():
            return PatchResult("FAILED", f"Script not found: {script_path}")

        code = sp.read_text(encoding="utf-8")
        module = cst.parse_module(code)

        transformer = _FillLocatorTransformer(
            failing_line=failing_line,
            old_locator=old_locator,
            new_locator=new_locator,
        )

        # NOTE: Matching by old_locator is enough for now and preserves formatting perfectly.
        # We can add exact failing_line matching later using libcst.MetadataWrapper + PositionProvider.
        updated = module.visit(transformer)

        if not transformer.patched:
            return PatchResult(
                status="FAILED",
                message="LibCST patch failed: could not match page.fill() by old_locator.",
                old_locator=old_locator,
                new_locator=new_locator,
            )

        outp = Path(output_path)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(updated.code, encoding="utf-8")

        return PatchResult(
            status="SUCCESS",
            message="LibCST patch applied (format preserved).",
            old_locator=old_locator,
            new_locator=new_locator,
            healed_script_path=str(outp),
        )
