from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com")

        # Search box (this is the locator we will break later)
        page.fill("input[name='q']", "OpenAI")

        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        browser.close()


if __name__ == "__main__":
    run()
