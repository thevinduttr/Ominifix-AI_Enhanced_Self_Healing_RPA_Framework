from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com")

        # TARGET_LINE: fill action
        page.fill("input[placeholder='Enter your emailAddr']_BROKEN_115", "test_value")

        browser.close()


if __name__ == "__main__":
    run()
