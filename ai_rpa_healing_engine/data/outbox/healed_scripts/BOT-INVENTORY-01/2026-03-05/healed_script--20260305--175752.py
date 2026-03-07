from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://inventory.algospring.com/dashboard")

        # BROKEN: search box ID was renamed in latest deployment
        page.fill("#search-input", "laptop")

        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        browser.close()


if __name__ == "__main__":
    run()
