from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://legacy.example.com/form")

        # TC-12: Minimal DOM with no usable attributes — only bare <div> with no id/name/aria
        page.click("//div")

        browser.close()


if __name__ == "__main__":
    run()
