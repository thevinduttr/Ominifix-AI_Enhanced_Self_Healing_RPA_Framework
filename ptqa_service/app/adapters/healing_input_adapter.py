# app/adapters/healing_input_adapter.py
"""
HealingInputAdapter
-------------------
Normalises incoming healing payloads from ANY team component
into the PTQA standard format, so the rest of the system never
needs to know which format arrived.

Supported formats
  1. PTQA native format          – passes through unchanged
  2. Code Healing Engine format  – Member 1's output structure
"""

from typing import Any, Dict


class HealingInputAdapter:

    # ------------------------------------------------------------------ #
    #  Public entry point                                                  #
    # ------------------------------------------------------------------ #

    def adapt(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-detect payload format and return PTQA standard payload.
        If the payload is already in PTQA format it is returned as-is.
        """
        if self._is_code_healing_engine_format(raw_payload):
            return self._adapt_from_code_healing_engine(raw_payload)

        # Already PTQA native — pass through untouched
        return raw_payload

    # ------------------------------------------------------------------ #
    #  Format detection                                                    #
    # ------------------------------------------------------------------ #

    def _is_code_healing_engine_format(self, payload: Dict[str, Any]) -> bool:
        """
        Detects the Code Healing Engine output by looking for fields
        that only appear in Member 1's format (bot_id, source_component,
        run_id, report_id).
        """
        metadata = payload.get("metadata", {}) or {}
        return any(
            key in metadata
            for key in ("bot_id", "source_component", "run_id", "report_id")
        )

    # ------------------------------------------------------------------ #
    #  Code Healing Engine → PTQA standard                                #
    # ------------------------------------------------------------------ #

    def _adapt_from_code_healing_engine(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Maps Member 1 (Code Healing Engine) output fields to the PTQA
        standard input format.

        Key differences handled:
          bot_id            → script_id
          model_info.confidence → model_info.model_confidence
          healing_summary.status uppercase → lowercase
          strategy_used verbose name → simplified name  (dom / xpath / css)
          last_n_failures  inferred from failure_context.error_type
          environment      defaults to "qa" if not present
        """
        metadata     = payload.get("metadata", {}) or {}
        healing_sum  = payload.get("healing_summary", {}) or {}
        model_info   = payload.get("model_info", {}) or {}
        script_out   = payload.get("script_output", {}) or {}
        failure_ctx  = payload.get("failure_context", {}) or {}
        element_cand = payload.get("element_candidate", {}) or {}

        # script_id  ←  bot_id  (Member 1 uses bot_id; we use script_id)
        script_id = (
            metadata.get("bot_id")
            or metadata.get("script_id")
            or "UNKNOWN_BOT"
        )

        # environment — Member 1 may or may not include this
        environment = metadata.get("environment", "qa")

        # last_n_failures — not in Member 1 output; infer from error_type
        last_n_failures = self._infer_last_n_failures(failure_ctx)

        # status — Member 1 sends uppercase ("SUCCESS"); we use lowercase
        status = healing_sum.get("status", "SUCCESS").lower()

        # strategy_used — Member 1 sends verbose names; map to our names
        # Also accept element_candidate.strategy as fallback
        raw_strategy = (
            healing_sum.get("strategy_used")
            or element_cand.get("strategy")
            or "dom"
        )
        strategy_used = self._normalize_strategy(raw_strategy)

        # model_confidence — Member 1 uses "confidence" key; we use "model_confidence"
        model_confidence = (
            model_info.get("confidence")
            or model_info.get("model_confidence")
            or healing_sum.get("confidence")
            or 0.0
        )

        return {
            "metadata": {
                "healing_id":      metadata.get("healing_id", "UNKNOWN"),
                "script_id":       script_id,
                "environment":     environment,
                "last_n_failures": last_n_failures,
                "headless":        metadata.get("headless", True),
            },
            "healing_summary": {
                "status":        status,
                "old_locator":   healing_sum.get("old_locator", ""),
                "new_locator":   healing_sum.get("new_locator", ""),
                "strategy_used": strategy_used,
            },
            "model_info": {
                "model_confidence": model_confidence,
            },
            "script_output": self._resolve_script_paths(
                # original — prefer script_output field, fallback to failure_context.script_path
                script_out.get("original_script_path")
                    or failure_ctx.get("script_path", ""),
                script_out.get("healed_script_path", ""),
            ),
        }

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _resolve_script_paths(
        self, original_path: str, healed_path: str
    ) -> Dict[str, str]:
        """
        Friend's system uses absolute paths on HIS machine
        (e.g. data/scripts/broken/e2e/bot1_ecommerce_checkout.py).
        Those files don't exist here, so we resolve them to real bots:

        Resolution order (for each path):
          1. Path exists as-is  → use it
          2. bots/<filename>    → use it  (just the bare filename)
          3. BOT_ID prefix match in bots/  → use closest match
          4. Hard fallback pair            → demo_add_remove bots
        """
        from pathlib import Path

        bots_dir = Path("bots")

        def resolve(path: str, fallback_name: str) -> str:
            if not path:
                return str(bots_dir / fallback_name)
            p = Path(path)
            # 1. exists as-is
            if p.exists():
                return str(p)
            # 2. just the filename inside bots/
            candidate = bots_dir / p.name
            if candidate.exists():
                return str(candidate)
            # 3. stem prefix match (e.g. bot1_ecommerce → demo_add_remove)
            stem = p.stem.lower()
            for bot_file in sorted(bots_dir.glob("*.py")):
                if bot_file.name.startswith("_"):
                    continue
                if stem[:6] in bot_file.stem.lower():
                    return str(bot_file)
            # 4. hard fallback
            return str(bots_dir / fallback_name)

        resolved_original = resolve(original_path, "demo_add_remove_original.py")
        resolved_healed   = resolve(healed_path,   "demo_add_remove.py")
        return {
            "original_script_path": resolved_original,
            "healed_script_path":   resolved_healed,
        }

    def _normalize_strategy(self, raw_strategy: str) -> str:
        """
        Map Member 1 verbose strategy names → PTQA simplified names.

        Member 1 values          PTQA value
        ─────────────────────────────────────
        LOCATOR_REGEN_LIBCST  →  dom
        attribute_match       →  dom
        XPATH_FALLBACK        →  xpath
        CSS_SELECTOR          →  css
        VISUAL_MATCH          →  visual
        (anything unknown)    →  dom   (safe default)
        """
        strategy_map = {
            "locator_regen_libcst": "dom",
            "attribute_match":      "dom",
            "xpath_fallback":       "xpath",
            "css_selector":         "css",
            "visual_match":         "visual",
            "dom":                  "dom",
            "xpath":                "xpath",
            "css":                  "css",
            "visual":               "visual",
        }
        return strategy_map.get(raw_strategy.lower(), "dom")

    def _infer_last_n_failures(self, failure_ctx: Dict[str, Any]) -> int:
        """
        Member 1 does not send last_n_failures.
        Infer a sensible value from the error_type field.

        error_type              inferred value
        ─────────────────────────────────────
        ELEMENT_NOT_FOUND   →  3
        TIMEOUT             →  2
        STALE_ELEMENT       →  2
        CLICK_FAILED        →  1
        (anything else)     →  1
        """
        error_type = (failure_ctx.get("error_type") or "").upper()
        inference_map = {
            "ELEMENT_NOT_FOUND": 3,
            "TIMEOUT":           2,
            "STALE_ELEMENT":     2,
            "CLICK_FAILED":      1,
        }
        return inference_map.get(error_type, 1)
