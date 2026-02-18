from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://reports.algospring.com/monthly")

        # Select date range
        page.fill("#date-from", "2026-01-01")
        page.fill("#date-to", "2026-01-31")

        # BROKEN: download button class changed after UI redesign
        page.click("#export-csv")

        page.wait_for_timeout(5000)
        browser.close()


if __name__ == "__main__":
    run()
