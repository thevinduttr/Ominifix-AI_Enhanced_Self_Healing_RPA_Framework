from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.sliit.lk/professional-programmes/")

        # Wait for tab navigation to load
        page.wait_for_selector("ul.nav.hr-tabs-nav[role='tablist']", timeout=30000)

        # BROKEN: tab CSS class changed in website update
        page.click("#tab-online")

        page.wait_for_timeout(1000)
        browser.close()


if __name__ == "__main__":
    run()
