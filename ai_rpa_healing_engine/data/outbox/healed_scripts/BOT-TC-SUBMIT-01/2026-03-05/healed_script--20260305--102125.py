from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://portal.example.com/form")

        page.fill("#name", "Algospring Research Bot")
        page.fill("#email", "bot@algospring.com")

        # TC-05: Submit button click — broken ID (submitBtn_old instead of submitBtn)
        page.click("#submitBtn")

        page.wait_for_timeout(3000)
        browser.close()


if __name__ == "__main__":
    run()
