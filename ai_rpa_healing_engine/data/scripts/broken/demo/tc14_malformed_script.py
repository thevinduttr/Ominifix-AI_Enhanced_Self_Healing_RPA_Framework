from playwright.sync_api import sync_playwright


# TC-14: Malformed script — missing closing parenthesis causes patcher to fail
def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://example.com/broken-form")

        # This line has a syntax issue the patcher cannot handle
        page.fill("input[name='field_BROKEN']",
                   "some value"
        page.click("#submit")

        browser.close()


if __name__ == "__main__":
    run()
