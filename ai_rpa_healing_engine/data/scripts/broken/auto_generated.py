from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.sliit.lk/professional-programmes/")

        # TARGET_LINE: auto-generated for code healing engine
        page.locator(".nonExistentClass")

        browser.close()


if __name__ == "__main__":
    run()

