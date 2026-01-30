from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://api.example.com/status")

        # TC-11: Non-healable error type — network error is not locator-related
        page.click("#refresh-btn")

        browser.close()


if __name__ == "__main__":
    run()
