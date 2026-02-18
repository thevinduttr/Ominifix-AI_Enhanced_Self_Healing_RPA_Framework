from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://signup.example.com/register")

        page.fill("#first_name", "Thevindu")
        page.fill("#last_name", "Rathnaweera")

        # TC-04: Email field fill — broken placeholder attr (emailAddr instead of email)
        page.fill("#email", "thevindu@algospring.com")

        page.fill("#phone", "+94771234567")
        page.click("#btn-register")

        browser.close()


if __name__ == "__main__":
    run()
