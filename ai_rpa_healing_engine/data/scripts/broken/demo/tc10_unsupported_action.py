from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com/canvas")

        # TC-10: Unsupported action — drag is not a healable action
        page.drag_and_drop("#source_element", "#target_zone")

        browser.close()


if __name__ == "__main__":
    run()
