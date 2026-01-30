from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.sliit.lk/")

        # TC-08: Traceback scenario — broken text input with raw error trace available
        page.fill("input[name='search_query_BROKEN']", "Computer Science")

        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        browser.close()


if __name__ == "__main__":
    run()
