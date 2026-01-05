from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import libcst as cst
import libcst.matchers as m
from libcst.metadata import MetadataWrapper, PositionProvider


@dataclass
class PatchResult:
    status: str  # "SUCCESS" / "FAILED"
    message: str
    old_locator: Optional[str]
    new_locator: Optional[str]
    healed_script_path: Optional[str]


class _LocatorArgReplacer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, failing_line: int, old_locator: str, new_locator: str, methods: set[str]):
        self.failing_line = failing_line
        self.old_locator = old_locator
        self.new_locator = new_locator
        self.methods = methods

        self.replaced = False
        self.replaced_at_line = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        # Only patch once
        if self.replaced:
            return updated_node

        # Match: <anything>.<method>(...)
        if not m.matches(
            updated_node.func,
            m.Attribute(
                attr=m.Name(),
            ),
        ):
            return updated_node

        func_attr: cst.Attribute = updated_node.func  # type: ignore
        method_name = func_attr.attr.value
        if method_name not in self.methods:
            return updated_node

        # Must have at least 1 arg
        if not updated_node.args:
            return updated_node

        # We patch only the FIRST argument if it's a string literal
        first_arg = updated_node.args[0].value

        # Check position line
        pos = self.get_metadata(PositionProvider, original_node, None)
        node_line = pos.start.line if pos else None

        # Target only failing line first
        if node_line != self.failing_line:
            return updated_node

        # Accept either '...' or "..." in source; we compare evaluated content carefully
        if isinstance(first_arg, cst.SimpleString):
            raw = first_arg.value  # includes quotes
            # Normalize content without quotes (best-effort)
            content = raw[1:-1] if len(raw) >= 2 else raw

            # We accept match if content equals old_locator OR raw equals old_locator
            if content == self.old_locator or raw == self.old_locator:
                new_string_node = cst.SimpleString(repr(self.new_locator))
                new_args = list(updated_node.args)
                new_args[0] = updated_node.args[0].with_changes(value=new_string_node)
                self.replaced = True
                self.replaced_at_line = True
                return updated_node.with_changes(args=new_args)

        return updated_node


class _GlobalLocatorStringReplacer(cst.CSTTransformer):
    """
    Fallback: replace exact string literal content anywhere in file.
    Preserves formatting; only changes the string literal value.
    """
    def __init__(self, old_locator: str, new_locator: str):
        self.old_locator = old_locator
        self.new_locator = new_locator
        self.replaced = False

    def leave_SimpleString(self, original_node: cst.SimpleString, updated_node: cst.SimpleString) -> cst.SimpleString:
        if self.replaced:
            return updated_node

        raw = original_node.value
        content = raw[1:-1] if len(raw) >= 2 else raw

        if content == self.old_locator or raw == self.old_locator:
            self.replaced = True
            return cst.SimpleString(repr(self.new_locator))
        return updated_node


class ScriptPatcher:
    """
    LibCST-based patcher that preserves formatting (blank lines, comments).
    Supports patching locator string in page.fill / page.click.
    """

    def patch_locator(
        self,
        script_path: str,
        output_path: str,
        failing_line: int,
        old_locator: str,
        new_locator: str,
        action: Optional[str] = None,  # "fill" / "click" / None => both
    ) -> PatchResult:
        in_path = Path(script_path)
        if not in_path.exists():
            return PatchResult(
                status="FAILED",
                message=f"Script not found: {script_path}",
                old_locator=old_locator,
                new_locator=new_locator,
                healed_script_path=None,
            )

        try:
            source = in_path.read_text(encoding="utf-8")
            module = cst.parse_module(source)
            wrapper = MetadataWrapper(module)

            # Decide which methods to patch
            if action == "fill":
                methods = {"fill"}
            elif action == "click":
                methods = {"click"}
            else:
                methods = {"fill", "click"}

            # 1) Try patch at failing line for action(s)
            tx = _LocatorArgReplacer(
                failing_line=failing_line,
                old_locator=old_locator,
                new_locator=new_locator,
                methods=methods,
            )
            updated = wrapper.visit(tx)

            if not tx.replaced:
                # 2) Fallback: global replace exact string literal
                updated = module.visit(_GlobalLocatorStringReplacer(old_locator, new_locator))

                # check if it replaced
                # (we cannot directly know; simplest: see if old locator still present as a quoted literal)
                if old_locator not in updated.code and f'"{old_locator}"' not in updated.code and f"'{old_locator}'" not in updated.code:
                    # Might still be okay if old_locator had different quote style; but generally:
                    # If no literal match changed, treat as failure.
                    pass

            # Determine success heuristics:
            # Success if new_locator appears in code AND old_locator literal is reduced.
            # (best-effort; your earlier logic is fine)
            if new_locator not in updated.code:
                return PatchResult(
                    status="FAILED",
                    message="LibCST patch failed: target call not found at failing line; global search may have failed.",
                    old_locator=old_locator,
                    new_locator=new_locator,
                    healed_script_path=None,
                )

            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(updated.code, encoding="utf-8")

            return PatchResult(
                status="SUCCESS",
                message="LibCST patch applied (format preserved).",
                old_locator=old_locator,
                new_locator=new_locator,
                healed_script_path=str(out_path),
            )

        except Exception as e:
            return PatchResult(
                status="FAILED",
                message=f"LibCST patch exception: {e}",
                old_locator=old_locator,
                new_locator=new_locator,
                healed_script_path=None,
            )
