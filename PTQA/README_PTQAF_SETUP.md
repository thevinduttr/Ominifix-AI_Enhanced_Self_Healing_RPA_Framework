# PTQAF: Setup and quickstart

This README adds quick instructions to run the Predictive Testing & Quality Assessment prototype scripts.

1) Create and activate a virtual environment inside `PTQF/`:

```bash
cd PTQF
python3 -m venv venv
source venv/bin/activate
```

2) Install dependencies (we updated `requirements.txt` to include Playwright and Selenium):

```bash
pip install -r requirements.txt
pip install webdriver-manager
playwright install
```

3) Capture a small Playwright log:

```bash
python src/logging/playwright_logger.py https://example.com --out logs/playwright.jsonl --headless
```

4) Capture a small Selenium log (requires chromedriver download via webdriver-manager):

```bash
python src/logging/selenium_logger.py https://example.com --out logs/selenium.jsonl --headless
```

5) Convert logs to dataset:

```bash
python src/data/convert_logs.py --inputs logs/playwright.jsonl logs/selenium.jsonl --out-train dataset/train.jsonl --out-val dataset/val.jsonl
```

6) Train baseline model and produce predictions:

```bash
python src/train/train_baseline.py --train dataset/train.jsonl --val dataset/val.jsonl --model models/baseline.joblib --out-preds output/predictions.jsonl --out-metrics output/metrics.json
```

7) Run unit tests (requires `pytest`):

```bash
pip install pytest
pytest -q tests/test_pipeline.py
```

Notes:
- The scripts are minimal prototypes to get you started. They produce a tiny feature set (message length + is_error) for a baseline model.
- Later we will extend feature engineering (DOM volatility, visual diffs, healing action metadata) and add labelling tooling.
