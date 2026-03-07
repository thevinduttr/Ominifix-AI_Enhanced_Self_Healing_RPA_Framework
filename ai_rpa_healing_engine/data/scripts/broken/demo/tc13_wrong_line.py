from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://portal.example.com/profile")

        page.fill("#display_name", "Thevindu R.")
        page.fill("#bio", "AI Researcher at SLIIT")

        # TC-13: Wrong failing_line — ELR points to line 10 but actual fill is line 14
        page.fill("input[name='location_OLD']", "Colombo, Sri Lanka")

        page.click("#save-profile")
        browser.close()


if __name__ == "__main__":
    run()
