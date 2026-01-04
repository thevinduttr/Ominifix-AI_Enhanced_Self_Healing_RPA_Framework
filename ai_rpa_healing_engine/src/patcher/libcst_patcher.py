from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, List, Tuple

import ast
import re
import libcst as cst
import libcst.metadata as meta


@dataclass
class PatchResult:
    status: str  # "SUCCESS" | "FAILED"
    message: str
    old_locator: Optional[str] = None
    new_locator: Optional[str] = None
    healed_script_path: Optional[str] = None


_ALLOWED_METHODS: Set[str] = {
    "click",
    "fill",
    "wait_for_selector",
    "query_selector_all",
    "locator",
}


def _get_call_method_name(call: cst.Call) -> Optional[str]:
    if isinstance(call.func, cst.Attribute):
        return call.func.attr.value
    return None


def _literal_string_value(node: cst.CSTNode) -> Optional[str]:
    if isinstance(node, cst.SimpleString):
        try:
            return cst.literal_eval(node.value)
        except Exception:
            return None
    return None


def _make_string_literal(s: str) -> cst.SimpleString:
    esc = s.replace("\\", "\\\\").replace('"', '\\"')
    return cst.SimpleString(f"\"{esc}\"")


class _CollectCandidatesVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (meta.PositionProvider,)

    def __init__(self, failing_line: int, action: str):
        self.failing_line = failing_line
        self.action = action
        self.candidates: List[Tuple[cst.Call, str]] = []  # (call_node, old_value)

    def visit_Call(self, node: cst.Call) -> Optional[bool]:
        method = _get_call_method_name(node)
        if method != self.action:
            return None

        pos = self.get_metadata(meta.PositionProvider, node, None)
        if pos is None:
            return None

        if not (pos.start.line <= self.failing_line <= pos.end.line):
            return None

        if not node.args:
            return None

        old_val = _literal_string_value(node.args[0].value)
        if old_val is None:
            return None

        self.candidates.append((node, old_val))
        return None


class _PatchSpecificCallTransformer(cst.CSTTransformer):
    def __init__(self, target_call: cst.Call, new_locator: str):
        self.target_call = target_call
        self.new_locator = new_locator
        self.did_patch = False
        self.found_old: Optional[str] = None

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if self.did_patch:
            return updated_node

        if original_node is not self.target_call:
            return updated_node

        if not updated_node.args:
            return updated_node

        old_val = _literal_string_value(updated_node.args[0].value)
        if old_val is None:
            return updated_node

        new_first = _make_string_literal(self.new_locator)
        new_args = list(updated_node.args)
        new_args[0] = new_args[0].with_changes(value=new_first)

        self.did_patch = True
        self.found_old = old_val
        return updated_node.with_changes(args=new_args)


class _ExactMatchPatchTransformer(cst.CSTTransformer):
    def __init__(self, action: str, old_locator: str, new_locator: str):
        self.action = action
        self.old_locator = old_locator
        self.new_locator = new_locator
        self.did_patch = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if self.did_patch:
            return updated_node

        method = _get_call_method_name(original_node)
        if method != self.action:
            return updated_node

        if not updated_node.args:
            return updated_node

        old_val = _literal_string_value(updated_node.args[0].value)
        if old_val is None or old_val != self.old_locator:
            return updated_node

        new_first = _make_string_literal(self.new_locator)
        new_args = list(updated_node.args)
        new_args[0] = new_args[0].with_changes(value=new_first)

        self.did_patch = True
        return updated_node.with_changes(args=new_args)


class ScriptPatcher:
    @staticmethod
    def _similarity(a: str, b: str) -> int:
        if not a or not b:
            return 0
        aset, bset = set(a), set(b)
        return len(aset.intersection(bset))

    @staticmethod
    def _line_fallback_patch(code: str, failing_line: int, action: str, new_locator: str) -> tuple[bool, Optional[str], str]:
        """
        Safe last-resort patch:
        - Only touches the single failing line.
        - Finds ".<action>(" on that line.
        - Replaces the FIRST string literal argument inside that call.
        Returns: (patched, found_old, new_code)
        """
        lines = code.splitlines(keepends=True)
        idx = failing_line - 1
        if idx < 0 or idx >= len(lines):
            return False, None, code

        line = lines[idx]

        # Must contain .action(
        marker = f".{action}("
        pos = line.find(marker)
        if pos == -1:
            return False, None, code

        # From after ".action(", find first quote
        start = pos + len(marker)
        m = re.search(r"""(['"])""", line[start:])
        if not m:
            return False, None, code

        q = m.group(1)
        qpos = start + m.start()

        # Find matching closing quote (simple, safe)
        # This assumes selector is a normal quoted string on the same line (true for your RPA file).
        end = qpos + 1
        escaped = False
        while end < len(line):
            ch = line[end]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == q:
                break
            end += 1

        if end >= len(line) or line[end] != q:
            return False, None, code

        literal = line[qpos:end + 1]  # includes quotes

        # Parse the literal to get old value safely
        try:
            found_old = ast.literal_eval(literal)
        except Exception:
            return False, None, code

        # Replace with a double-quoted literal
        new_lit = '"' + new_locator.replace("\\", "\\\\").replace('"', '\\"') + '"'
        new_line = line[:qpos] + new_lit + line[end + 1:]
        lines[idx] = new_line
        return True, str(found_old), "".join(lines)

    def patch_locator(
        self,
        script_path: str,
        output_path: str,
        failing_line: int,
        old_locator: str,
        new_locator: str,
        action: str,
    ) -> PatchResult:
        action = (action or "").strip().lower()

        if action not in _ALLOWED_METHODS:
            return PatchResult(
                status="FAILED",
                message=f"Unsupported action '{action}'. Allowed: {sorted(_ALLOWED_METHODS)}",
                old_locator=old_locator,
                new_locator=new_locator,
            )

        src_path = Path(script_path)
        if not src_path.exists():
            return PatchResult(
                status="FAILED",
                message=f"Original script not found: {script_path}",
                old_locator=old_locator,
                new_locator=new_locator,
            )

        code = src_path.read_text(encoding="utf-8")

        # ---- 1) LibCST failing_line candidates ----
        try:
            module = cst.parse_module(code)
            wrapper = cst.metadata.MetadataWrapper(module)

            collector = _CollectCandidatesVisitor(int(failing_line), action)
            wrapper.visit(collector)

            if collector.candidates:
                if len(collector.candidates) == 1:
                    target_call, found_old = collector.candidates[0]
                else:
                    scored = []
                    for call_node, found in collector.candidates:
                        scored.append((self._similarity(found, old_locator), call_node, found))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    _, target_call, found_old = scored[0]

                patch_tx = _PatchSpecificCallTransformer(target_call, new_locator)
                modified = wrapper.visit(patch_tx)

                if patch_tx.did_patch:
                    out_path = Path(output_path)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(modified.code, encoding="utf-8")
                    return PatchResult(
                        status="SUCCESS",
                        message="LibCST patch applied using failing_line candidate (format preserved).",
                        old_locator=patch_tx.found_old or found_old or old_locator,
                        new_locator=new_locator,
                        healed_script_path=str(out_path),
                    )

            # ---- 2) LibCST exact match fallback ----
            exact_tx = _ExactMatchPatchTransformer(action, old_locator, new_locator)
            modified2 = module.visit(exact_tx)
            if exact_tx.did_patch:
                out_path = Path(output_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(modified2.code, encoding="utf-8")
                return PatchResult(
                    status="SUCCESS",
                    message="LibCST patch applied using exact match (format preserved).",
                    old_locator=old_locator,
                    new_locator=new_locator,
                    healed_script_path=str(out_path),
                )

        except Exception:
            # If LibCST parsing/metadata fails for any reason, we still attempt line fallback below
            pass

        # ---- 3) Safe single-line fallback (guaranteed for your locator case) ----
        patched, found_old, new_code = self._line_fallback_patch(code, int(failing_line), action, new_locator)
        if patched:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(new_code, encoding="utf-8")
            return PatchResult(
                status="SUCCESS",
                message="Fallback line patch applied (single-line selector replaced).",
                old_locator=found_old or old_locator,
                new_locator=new_locator,
                healed_script_path=str(out_path),
            )

        return PatchResult(
            status="FAILED",
            message=(
                f"Patch failed: No patchable '.{action}(\"...\")' call located using failing_line={failing_line}, "
                f"no exact match for old_locator, and single-line fallback did not detect a selector string."
            ),
            old_locator=old_locator,
            new_locator=new_locator,
        )
