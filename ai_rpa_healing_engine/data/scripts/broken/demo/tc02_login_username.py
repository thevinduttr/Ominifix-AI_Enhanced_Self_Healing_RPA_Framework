from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://accounts.example.com/login")

        # TC-02: Login username fill — broken ID (user_xyz instead of username)
        page.fill("#user_xyz", "admin@algospring.com")

        page.fill("#password", "SecurePass123!")
        page.click("button[type='submit']")

        browser.close()


if __name__ == "__main__":
    run()
