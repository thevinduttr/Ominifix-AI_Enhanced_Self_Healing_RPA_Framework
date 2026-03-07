from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://dashboard.example.com/")

        # TC-06: Navigation link click — broken aria-label (old label changed)
        page.click("#nav-reports")

        page.wait_for_timeout(2000)
        browser.close()


if __name__ == "__main__":
    run()
