from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://hr.algospring.com/login")

        # BROKEN: username input name attribute changed
        page.fill("input[name='usr_name_old']", "admin@algospring.com")

        # Password field (still works)
        page.fill("#password", "SecurePass123!")

        page.click("button[type='submit']")
        browser.close()


if __name__ == "__main__":
    run()
