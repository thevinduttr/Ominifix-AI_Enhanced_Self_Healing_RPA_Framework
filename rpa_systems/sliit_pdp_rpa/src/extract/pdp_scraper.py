from playwright.sync_api import Page
from src.extract.parser import parse_programs_from_html

TAB_LABELS = [
    "Online Programs",
    "Regular Programs",
    "Workshops & Trainings",
    "Upcoming Programs",
]

def goto_professional_programmes(page: Page, base_url: str, target_url: str, logger, timeout_ms: int):
    logger.info(f"Navigate: {base_url}")
    page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(500)

    logger.info("Open Professional Programmes page")
    # Reliable: go directly to target URL (less flaky than menu click)
    page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)

def extract_all_tabs(page: Page, logger, timeout_ms: int) -> dict[str, list[dict]]:
    """
    Returns:
      {
        "Online Programs": [{Program Name, Starting Date, URL}, ...],
        ...
      }
    """
    results = {}

    # Wait for page section to load (tabs exist)
    page.wait_for_selector("ul.nav.hr-tabs-nav[role='tablist']", timeout=timeout_ms)

    # Get tab anchors
    tabs = page.query_selector_all("ul.nav.hr-tabs-nav[role='tablist'] li.hr-tabs-nav-item a[role='tab']")
    logger.info(f"Tabs detected: {len(tabs)}")

    for i, tab in enumerate(tabs):
        label = tab.inner_text().strip()
        logger.info(f"Open tab {i+1}: {label}")
        tab.click()
        page.wait_for_timeout(700)

        # The content is on the same page; best is to read current HTML and parse the section
        # We'll parse by finding the heading that matches the tab label and using the nearby container.
        html = page.content()

        # Parse full page, then pick the section by heading title
        # In practice the page includes the list under headings like <h3>Online Programs</h3>
        # We'll just parse all program links on the page and filter by heading proximity is hard;
        # so we use a safer method:
        # read the entire block for each heading via Playwright locator.
        section_locator = page.locator("div.pdp-course-col").filter(has=page.locator(f"h3:has-text('{label}')"))
        if section_locator.count() == 0:
            # fallback if heading is not h3
            section_locator = page.locator("div.pdp-course-col").filter(has=page.locator(f":text('{label}')"))

        if section_locator.count() == 0:
            logger.warning(f"Section not found for tab '{label}'. Skipping.")
            results[label] = []
            continue

        block_html = section_locator.first.inner_html()
        programs = parse_programs_from_html(block_html)
        logger.info(f"Extracted {len(programs)} programs from '{label}'")
        results[label] = programs

    # Ensure all expected labels exist
    for lbl in TAB_LABELS:
        results.setdefault(lbl, [])

    return results
