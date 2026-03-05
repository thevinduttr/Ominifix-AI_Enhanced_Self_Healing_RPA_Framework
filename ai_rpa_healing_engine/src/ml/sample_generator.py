import json
from pathlib import Path
from datetime import datetime


class SampleGenerator:
    """
    Generates synthetic Element Locator Engine inputs + corresponding broken scripts.
    Now supports 5-class strategy dataset with 150 samples for research validation.

    Output:
      - data/synthetic_inputs/batch/elr_input_<n>.json
      - data/scripts/broken/batch/broken_<n>.py
    """

    def __init__(self):
        self.inputs_dir = Path("data/synthetic_inputs/batch")
        self.scripts_dir = Path("data/scripts/broken/batch")
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

    def _generate_script_for_action(self, action: str, old_locator: str) -> str:
        """Generate appropriate broken script based on action type.
        
        Uses double-quoted locator strings to avoid conflict with
        single-quoted CSS attribute selectors like [aria-label='...'].
        """
        # Escape double quotes in locator if any (rare, but defensive)
        safe_locator = old_locator.replace('"', '\\"')

        if action == "click":
            return f'''from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com")

        # TARGET_LINE: click action
        page.click("{safe_locator}")

        browser.close()


if __name__ == "__main__":
    run()
'''
        else:  # fill or other actions
            return f'''from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com")

        # TARGET_LINE: fill action
        page.fill("{safe_locator}", "test_value")

        browser.close()


if __name__ == "__main__":
    run()
'''

    def generate(self, n: int = 150) -> int:
        """
        Generate n synthetic failure scenarios with corresponding broken scripts.
        Default: 150 samples for research-grade evaluation.
        """
        samples = self._build_samples(n)

        for i, s in enumerate(samples, start=1):
            bot_id = f"BOT-SYN-{i:03d}"
            action = s.get("action", "fill")

            # Create broken script based on action type
            broken_script_path = self.scripts_dir / f"broken_{i:03d}.py"
            broken_code = self._generate_script_for_action(action, s["old_locator"])
            broken_script_path.write_text(broken_code, encoding="utf-8")

            failing_line = self._find_failing_line(broken_code, action)

            payload = {
                "metadata": {
                    "report_id": f"ELR-SYN-{i:03d}",
                    "run_id": "RUN-BATCH-RESEARCH-v2",
                    "bot_id": bot_id,
                    "timestamp": datetime.now().isoformat(),
                    "source_component": "element_locator_engine",
                    "target_component": "code_healing_engine",
                },
                "failure_context": {
                    "script_path": str(broken_script_path).replace("\\", "/"),
                    "failing_line": failing_line,
                    "action": action,
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

    def _find_failing_line(self, code: str, action: str = "fill") -> int:
        """Find the line number containing the target action."""
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            if f"page.{action}(" in line and "OLD_LOCATOR" not in line:
                return idx
        return 1

    def _build_samples(self, n: int) -> list:
        """
        Produce a 5-CLASS dataset with highly diverse broken locator patterns
        for research-grade ML evaluation.

        Classes:
          - LOCATOR_REGEN_LIBCST: ID-based selectors (score 100)
          - FALLBACK_LOCATOR: aria-label/placeholder/name-based (score 75-80)
          - FALLBACK_XPATH: Elements with no CSS-friendly attributes
          - CLICK_ONLY: Button/link click actions (specialized class)
          - NO_FIX: Empty DOM, unfixable failures

        Diversity strategy:
          - Multiple broken-locator STYLES per class (ID mangled, name renamed,
            suffix appended, class swapped, attribute removed)
          - Mixed error types per class
          - Realistic DOM fragments from production web applications
        """

        base = []

        # ═══════════════════════════════════════════════════
        # Class 1: LOCATOR_REGEN_LIBCST (target has usable id)
        # ═══════════════════════════════════════════════════
        base.extend([
            # Broken ID style: #old_id
            {"new_element_html": '<input id="email" type="email" placeholder="Email Address" />', "old_locator": '#email_old', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Email"},
            {"new_element_html": '<input id="username" type="text" name="username" placeholder="Enter your email" aria-label="Username" autocomplete="username" />', "old_locator": '#user_xyz', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "username_field", "expected_text": "Username"},
            {"new_element_html": '<input id="password" type="password" name="password" placeholder="Password" aria-label="Password" autocomplete="current-password" />', "old_locator": '#pass_old', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "password_field", "expected_text": "Password"},
            # Broken name style: input[name='xxx']
            {"new_element_html": '<input id="phone" type="tel" placeholder="Phone Number" />', "old_locator": "input[name='mobile_old']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Phone"},
            {"new_element_html": '<input id="address" type="text" placeholder="Street Address" />', "old_locator": "input[name='addr_old']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Address"},
            {"new_element_html": '<input type="email" id="email" name="email" placeholder="Enter your email address" aria-label="Email Address" required />', "old_locator": "input[placeholder='Enter emailAddr']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Email Address"},
            # Broken class style: input.class_old
            {"new_element_html": '<textarea id="comment" rows="4" cols="50"></textarea>', "old_locator": 'textarea.feedback-input-old', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "textarea", "expected_text": "Comment"},
            {"new_element_html": '<select id="country"><option>USA</option></select>', "old_locator": 'select.country-picker-v1', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "select", "expected_text": "Country"},
            # Broken compound selector
            {"new_element_html": '<input id="search" type="search" placeholder="Search..." />', "old_locator": 'input[type="search"][name="q_old"]', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "search_box", "expected_text": "Search"},
            {"new_element_html": '<input id="location" name="location" placeholder="Enter city" aria-label="Location" />', "old_locator": "input[name='location_OLD']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Location"},
            # Broken selector with version suffix
            {"new_element_html": '<select id="region" name="region" aria-label="Select Region" class="form-select"><option value="WP">Western Province</option></select>', "old_locator": "select[aria-label='Region_old']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "dropdown", "expected_text": "Select Region"},
            {"new_element_html": '<input id="zipcode" type="text" name="zip" />', "old_locator": '#zipcode_BROKEN', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "input", "expected_text": "Zip Code"},
        ])

        # ═══════════════════════════════════════════════════
        # Class 2: FALLBACK_LOCATOR (no id, but has name/placeholder/aria)
        # ═══════════════════════════════════════════════════
        base.extend([
            # Broken name → heal via name/aria-label
            {"new_element_html": '<textarea class="gLFyf" name="q" aria-label="Search" rows="1"></textarea>', "old_locator": "textarea[name='qqq']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "search_box", "expected_text": "Search"},
            {"new_element_html": '<input type="password" name="password" placeholder="Password" />', "old_locator": "input[name='passcode']", "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "input", "expected_text": "Password"},
            {"new_element_html": '<input type="text" aria-label="Username" autocomplete="username" />', "old_locator": 'input#user_wrong', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "input", "expected_text": "Username"},
            # Broken placeholder
            {"new_element_html": '<input type="email" placeholder="Enter your email" />', "old_locator": "input[placeholder='Enter your emailAddr']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Email"},
            {"new_element_html": '<input type="text" name="firstname" placeholder="First Name" />', "old_locator": "input[placeholder='First Name_v1']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "First Name"},
            # Broken class → heal via name
            {"new_element_html": '<textarea name="message" placeholder="Your message here"></textarea>', "old_locator": 'textarea.msg-input-v2', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "textarea", "expected_text": "Message"},
            # Broken aria-label
            {"new_element_html": '<input type="search" name="s" placeholder="Search SLIIT..." aria-label="Search" class="search-input" />', "old_locator": "input[name='search_query_BROKEN']", "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "search_input", "expected_text": "Search SLIIT"},
            {"new_element_html": '<input type="search" id="search-field" name="s" placeholder="Search SLIIT..." aria-label="Search" class="search-input" />', "old_locator": "input[name='search_query_BROKEN']", "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "search_input", "expected_text": "Search SLIIT"},
            {"new_element_html": '<input type="text" name="query" id="mainSearch" placeholder="Search..." />', "old_locator": "input[name='query_BROKEN']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "search_input", "expected_text": "Search"},
            {"new_element_html": '<input type="text" name="keyword" aria-label="Keyword Search" />', "old_locator": "input[name='keyword_BROKEN']", "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "search_input", "expected_text": "Keyword"},
            {"new_element_html": '<input type="text" name="filter" id="filterBox" placeholder="Filter results..." />', "old_locator": "input[name='filter_BROKEN']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Filter"},
            {"new_element_html": '<input type="text" name="company" aria-label="Company Name" />', "old_locator": "input[aria-label='Company_v1']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Company Name"},
            # Broken ID → heal via name (no id in target)
            {"new_element_html": '<input type="number" name="amount" placeholder="Enter amount" />', "old_locator": '#amount_field_old', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "Amount"},
            {"new_element_html": '<input type="date" name="dob" aria-label="Date of Birth" />', "old_locator": '#dob_input', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "fill", "expected_role": "input", "expected_text": "Date of Birth"},
            {"new_element_html": '<input type="text" name="city" placeholder="City" />', "old_locator": 'input.city-field-legacy', "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "City"},
            {"new_element_html": '<select name="department" aria-label="Department"><option>Engineering</option></select>', "old_locator": "select[name='dept_v1']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "select", "expected_text": "Department"},
        ])

        # ═══════════════════════════════════════════════════
        # Class 3: FALLBACK_XPATH (no id, no name/aria — class-only)
        # ═══════════════════════════════════════════════════
        base.extend([
            {"new_element_html": '<div class="x1 x2 x3"><span>Submit</span></div>', "old_locator": 'div.submit-btn-wrong', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "button", "expected_text": "Submit"},
            {"new_element_html": '<span class="icon-close"></span>', "old_locator": 'span.close-icon-v2', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "button", "expected_text": "Close"},
            {"new_element_html": '<li class="nav-item"><a>Home</a></li>', "old_locator": 'li.nav-home-old', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "link", "expected_text": "Home"},
            {"new_element_html": '<div class="card"><p>Content</p></div>', "old_locator": 'div.content-card-wrong', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "container", "expected_text": "Content"},
            {"new_element_html": '<td class="data-cell">Value</td>', "old_locator": 'td.cell-data-v1', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "table_cell", "expected_text": "Value"},
            {"new_element_html": '<p class="error-text">Something went wrong</p>', "old_locator": 'p.err-msg-old', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "text", "expected_text": "Error"},
        ])

        # ═══════════════════════════════════════════════════
        # Class 4: CLICK_ONLY (button/link with click action)
        # ═══════════════════════════════════════════════════
        base.extend([
            {"new_element_html": '<button type="submit" id="submitBtn" name="submit" class="btn btn-primary" aria-label="Submit Form">Submit</button>', "old_locator": '#submitBtn_old', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "submit_button", "expected_text": "Submit"},
            {"new_element_html": '<a id="loginLink" href="/login" aria-label="Login">Log In</a>', "old_locator": 'a.login-link-v1', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "link", "expected_text": "Login"},
            {"new_element_html": '<button id="cancelBtn" type="button">Cancel</button>', "old_locator": "button[name='cancel_wrong']", "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "button", "expected_text": "Cancel"},
            {"new_element_html": '<button id="saveBtn" aria-label="Save changes">Save</button>', "old_locator": 'button.save-btn-v1', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "click", "expected_role": "button", "expected_text": "Save"},
            {"new_element_html": '<a href="/reports" id="nav-reports" name="reports-link" aria-label="Reports" class="nav-link active">Reports</a>', "old_locator": "a[aria-label='Reports Section_v1']", "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "click", "expected_role": "navigation_link", "expected_text": "Reports"},
            {"new_element_html": '<a id="signupLink" href="/signup" role="button">Sign Up</a>', "old_locator": 'a[href="/register"]', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "link", "expected_text": "Sign Up"},
            {"new_element_html": '<button id="deleteBtn" class="danger">Delete</button>', "old_locator": 'button[data-action="remove"]', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "button", "expected_text": "Delete"},
            {"new_element_html": '<button id="nextBtn" class="btn-next" aria-label="Next Page">Next</button>', "old_locator": '#next_page_btn', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "button", "expected_text": "Next"},
            {"new_element_html": '<a id="dashboardLink" href="/dashboard" class="sidebar-link">Dashboard</a>', "old_locator": "a[href='/dash_old']", "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "link", "expected_text": "Dashboard"},
            {"new_element_html": '<button id="refreshBtn" class="btn" aria-label="Refresh Data">Refresh</button>', "old_locator": '#refresh_v1', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "click", "expected_role": "button", "expected_text": "Refresh"},
        ])

        # ═══════════════════════════════════════════════════
        # Class 5: NO_FIX (empty/invalid DOM — unhealable)
        # ═══════════════════════════════════════════════════
        base.extend([
            {"new_element_html": "", "old_locator": "input[name='missing_dom']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "N/A"},
            {"new_element_html": "   ", "old_locator": "textarea[name='missing_dom2']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "N/A"},
            {"new_element_html": "", "old_locator": '#action_btn_old', "error_type": "TIMEOUT_WAITING_FOR_SELECTOR", "action": "click", "expected_role": "button", "expected_text": "N/A"},
            {"new_element_html": "    \n\n  ", "old_locator": 'div.container-wrong', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "div", "expected_text": "N/A"},
            {"new_element_html": "", "old_locator": "input[name='vanished_field']", "error_type": "ELEMENT_NOT_FOUND", "action": "fill", "expected_role": "input", "expected_text": "N/A"},
            {"new_element_html": "", "old_locator": '#removed_element', "error_type": "ELEMENT_NOT_FOUND", "action": "click", "expected_role": "button", "expected_text": "N/A"},
        ])

        # ═══════════════════════════════════════════════════
        # Cycle through base patterns with variation injection
        # ═══════════════════════════════════════════════════
        samples = []
        k = 0
        variation_counter = 0

        while len(samples) < n:
            t = base[k % len(base)].copy()

            # Inject variations for dataset diversity
            if variation_counter % 4 == 1:
                loc = t["old_locator"]
                if "wrong" in loc:
                    t["old_locator"] = loc.replace("wrong", f"wrong{variation_counter}")
                elif "_old" in loc:
                    t["old_locator"] = loc.replace("_old", f"_old{variation_counter}")
                elif "_v1" in loc:
                    t["old_locator"] = loc.replace("_v1", f"_v{variation_counter}")
            elif variation_counter % 4 == 2:
                if t["error_type"] == "ELEMENT_NOT_FOUND":
                    t["error_type"] = "TIMEOUT_WAITING_FOR_SELECTOR"
                else:
                    t["error_type"] = "ELEMENT_NOT_FOUND"
            elif variation_counter % 4 == 3:
                loc = t["old_locator"]
                if "_BROKEN" not in loc and "BROKEN" not in loc:
                    t["old_locator"] = loc + f"_BROKEN_{variation_counter}"

            samples.append(t)
            k += 1
            variation_counter += 1

        return samples
