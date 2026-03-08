# Playwright RPA Bot (Python)

This bot fills the **Regional Bank Customer System** form automatically using Python + Playwright.

## What It Does

- Opens `http://localhost:5173`
- Fills customer fields
- Sets account type and KYC checkbox
- Clicks `Add Customer`
- Verifies success status and record presence in table

## 1. Start the React App

From project root:

```bash
npm install
npm run dev
```

Keep this terminal running.

## 2. Install Python Dependencies

From project root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r rpa/requirements.txt
python -m playwright install
```

## 3. Run the RPA Bot

```bash
python rpa/form_filler_bot.py
```

If successful, console prints:

`RPA bot finished: customer form submitted and record verified.`

## Notes

- If app URL changes, update `APP_URL` in `rpa/form_filler_bot.py`.
- To run headless, set `headless=True` in `browser.launch(...)`.
