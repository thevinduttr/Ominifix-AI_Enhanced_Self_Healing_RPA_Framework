from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com/unknown")

        # TC-09: No DOM context available — element was removed from page entirely
        page.fill("input[name='vanished_field']", "data")

        browser.close()


if __name__ == "__main__":
    run()
