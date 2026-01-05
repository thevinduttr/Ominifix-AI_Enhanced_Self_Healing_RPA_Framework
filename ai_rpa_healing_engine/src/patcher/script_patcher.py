from __future__ import annotations
import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatchResult:
    status: str
    message: str
    old_locator: str | None = None
    new_locator: str | None = None
    healed_script_path: str | None = None
    patched_line: int | None = None


class FillCallPatcher(ast.NodeTransformer):
    def __init__(self, failing_line: int | None, old_locator: str | None, new_locator: str):
        self.failing_line = failing_line
        self.old_locator = old_locator
        self.new_locator = new_locator

        self.patched = False
        self.patched_line = None
        self.match_reason = None

    def visit_Call(self, node: ast.Call):
        # Match page.fill(...)
        is_fill = isinstance(node.func, ast.Attribute) and node.func.attr == "fill" and len(node.args) >= 1
        if not is_fill:
            return self.generic_visit(node)

        node_line = getattr(node, "lineno", None)

        # Helper: read the current locator arg if it's a string literal
        current_locator = None
        if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            current_locator = node.args[0].value

        # 1) Best: exact failing line match
        if self.failing_line and node_line == self.failing_line:
            node.args[0] = ast.Constant(value=self.new_locator)
            self.patched = True
            self.patched_line = node_line
            self.match_reason = "MATCH_FAILING_LINE"
            return node

        # 2) Next best: match by old locator value (if provided)
        if self.old_locator and current_locator:
            # old_locator might be raw selector; current_locator is raw content without quotes in AST
            if current_locator == self.old_locator:
                node.args[0] = ast.Constant(value=self.new_locator)
                self.patched = True
                self.patched_line = node_line
                self.match_reason = "MATCH_OLD_LOCATOR"
                return node

        return self.generic_visit(node)


class ScriptPatcher:
    """
    AST-based patcher (robust).
    Matches in this order:
      1) page.fill(...) at failing_line
      2) page.fill(...) where first arg == old_locator
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
        tree = ast.parse(code)

        patcher = FillCallPatcher(failing_line=failing_line, old_locator=old_locator, new_locator=new_locator)
        patcher.visit(tree)

        if not patcher.patched:
            return PatchResult(
                status="FAILED",
                message="AST patch failed: page.fill not found (by failing_line or old_locator).",
                old_locator=old_locator,
                new_locator=new_locator,
                healed_script_path=None,
            )

        ast.fix_missing_locations(tree)
        healed_code = ast.unparse(tree)

        outp = Path(output_path)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(healed_code, encoding="utf-8")

        return PatchResult(
            status="SUCCESS",
            message=f"AST patch applied ({patcher.match_reason})",
            old_locator=old_locator,
            new_locator=new_locator,
            healed_script_path=str(outp),
            patched_line=patcher.patched_line,
        )
