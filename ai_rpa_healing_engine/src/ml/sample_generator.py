import json
from pathlib import Path
from datetime import datetime


class SampleGenerator:
    """
    Generates synthetic Element Locator Engine inputs + corresponding broken scripts.

    Output:
      - data/synthetic_inputs/batch/elr_input_<n>.json
      - data/scripts/broken/batch/broken_<n>.py
    """

    def __init__(self):
        self.inputs_dir = Path("data/synthetic_inputs/batch")
        self.scripts_dir = Path("data/scripts/broken/batch")
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        self.template_script = Path("data/scripts/broken/template_fill_script.py").read_text(encoding="utf-8")

    def generate(self, n: int = 60):
        samples = self._build_samples(n)

        for i, s in enumerate(samples, start=1):
            bot_id = f"BOT-SYN-{i:03d}"

            # Create broken script (valid Python because template uses single quotes)
            broken_script_path = self.scripts_dir / f"broken_{i:03d}.py"
            broken_code = self.template_script.replace("OLD_LOCATOR", s["old_locator"])
            broken_script_path.write_text(broken_code, encoding="utf-8")

            failing_line = self._find_failing_line(broken_code)

            payload = {
                "metadata": {
                    "report_id": f"ELR-SYN-{i:03d}",
                    "run_id": "RUN-BATCH-02",
                    "bot_id": bot_id,
                    "timestamp": datetime.now().isoformat(),
                    "source_component": "element_locator_engine",
                    "target_component": "code_healing_engine",
                },
                "failure_context": {
                    "script_path": str(broken_script_path).replace("\\", "/"),
                    "failing_line": failing_line,
                    "action": "fill",
                    "old_locator": s["old_locator"],
                    "error_type": s["error_type"],
                    "error_message": f"Timeout waiting for selector {s['old_locator']}",
                },
                "dom_context": {
                    "page_url": "https://example.com",
                    "page_name": "synthetic_page",
                    "new_element_html": s["new_element_html"],
                },
                "element_expectation": {
                    "expected_role": s["expected_role"],
                    "expected_text": s["expected_text"],
                },
            }

            json_path = self.inputs_dir / f"elr_input_{i:03d}.json"
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return len(samples)

    def _find_failing_line(self, code: str) -> int:
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            if "page.fill(" in line and "OLD_LOCATOR" not in line:
                return idx
        return 1

    def _build_samples(self, n: int):
        """
        Produce a MULTI-CLASS dataset:
          - Some good HTML -> heal works (LOCATOR_REGEN_LIBCST or FALLBACK_LOCATOR)
          - Some empty/bad HTML -> NO_FIX
        """

        base = []

        # --- Class: LOCATOR_REGEN_LIBCST (id-based) ---
        base.append({
            "new_element_html": '<input id="email" type="text" placeholder="Email Address" />',
            "old_locator": 'input[name="email_wrong"]',
            "error_type": "ELEMENT_NOT_FOUND",
            "expected_role": "input",
            "expected_text": "Email",
        })

        # --- Class: FALLBACK_LOCATOR (no id; must use aria-label/name/placeholder) ---
        base.append({
            "new_element_html": '<textarea class="gLFyf" name="q" aria-label="Search" rows="1"></textarea>',
            "old_locator": 'textarea[name="qqq"]',
            "error_type": "ELEMENT_NOT_FOUND",
            "expected_role": "search_box",
            "expected_text": "Search",
        })
        base.append({
            "new_element_html": '<input type="password" placeholder="Password" />',
            "old_locator": 'input[name="pass_wrong"]',
            "error_type": "ELEMENT_NOT_FOUND",
            "expected_role": "input",
            "expected_text": "Password",
        })
        base.append({
            "new_element_html": '<input type="text" aria-label="Username" />',
            "old_locator": 'input[id="user_wrong"]',
            "error_type": "ELEMENT_NOT_FOUND",
            "expected_role": "input",
            "expected_text": "Username",
        })

        # --- Class: NO_FIX (missing DOM snippet) ---
        base.append({
            "new_element_html": "",  # intentionally empty -> generator returns no candidates
            "old_locator": 'input[name="missing_dom"]',
            "error_type": "ELEMENT_NOT_FOUND",
            "expected_role": "input",
            "expected_text": "N/A",
        })
        base.append({
            "new_element_html": "   ",  # whitespace only
            "old_locator": 'textarea[name="missing_dom2"]',
            "error_type": "ELEMENT_NOT_FOUND",
            "expected_role": "input",
            "expected_text": "N/A",
        })

        samples = []
        k = 0
        while len(samples) < n:
            t = base[k % len(base)].copy()

            # add slight old_locator variation so rows aren't identical
            if len(samples) % 2 == 1:
                t["old_locator"] = t["old_locator"].replace("wrong", f"wrong{len(samples)}").replace("qqq", f"qqq{len(samples)}")

            samples.append(t)
            k += 1

        return samples
