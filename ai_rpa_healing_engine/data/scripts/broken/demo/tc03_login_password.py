from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://accounts.example.com/login")

        page.fill("#username", "admin@algospring.com")

        # TC-03: Login password fill — broken name (passcode instead of password)
        page.fill("input[name='passcode']", "SecurePass123!")

        page.click("button[type='submit']")

        browser.close()


if __name__ == "__main__":
    run()
