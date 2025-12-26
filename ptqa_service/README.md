# PTQA Service – Predictive Testing & Quality Assessment Framework
### Self-Healing RPA Framework

## Predictive Testing & Quality Assessment (PTQA) Microservice

---

## 1. Overview

This microservice implements the Predictive Testing & Quality Assessment (PTQA) component of the AI-Enhanced Self-Healing RPA Framework.

PTQA is responsible for:

- predicting failure risk of healed RPA scripts
- auto-generating and executing regression tests
- detecting performance regressions
- computing reliability and quality metrics
- approving or blocking healing attempts
- enforcing CI/CD quality gates
- storing evaluation results and reports
- executing real Playwright and Selenium automation bots
- recording execution videos for evidence

Technologies used:

- FastAPI microservice
- Python 3.10+
- Machine Learning ensembles
- SQLite + SQLAlchemy ORM
- Playwright & Selenium browser automation
- Python AST-based test generation
- REST APIs, interactive UI, dashboard

---

## 2. Architecture Positioning

Within the Self-Healing RPA Framework:

- Element Locator repairs damaged locators
- Code Healing rewrites RPA scripts
- **PTQA validates whether the healing is safe**
- Orchestrator deploys or rejects based on PTQA decision

Pipeline:

Healed Script
→ Test Generation
→ Playwright/Selenium Execution
→ ML Failure Prediction
→ Metrics & Regression Analysis
→ Quality Gate Decision
→ Persist & Report

---

## 3. Major Functional Components Implemented

### ✔ ML-Based Failure Prediction

Implemented:

- industrial-style dataset of 10,000+ healing events
- class imbalance (~53% failed vs 47% success)
- engineered features:
  - strategy (DOM, OCR, hybrid, vision)
  - execution time before/after healing
  - locator change indicator
  - prior failure history
  - model confidence
- full training pipeline
- persisted trained model artifact

Models implemented:

- RandomForest
- GradientBoosting
- Soft-Voting Ensemble

Outputs:

- p_fail
- will_work_probability
- risk_level
- model_name

---

### 📊 Model Performance

Dataset: 10,000 events  
Validation split: 20% (2,000 samples)

Overall Accuracy: 0.883 (88.3%)

Per-class results:

- Class 0 (stable healing) – Precision 0.87, Recall 0.89
- Class 1 (risky healing) – Precision 0.90, Recall 0.88

Conclusion:

- balanced precision/recall
- robust to imbalance
- no signs of overfitting

---

### ✔ Automated Test Generation

- Python AST based
- discovers entry functions
- generates regression scenarios:
  - smoke flow
  - locator validation flow
- measures execution time

Executable entrypoint:

def run_main_flow(context=None)

---

### ✔ Quality Metrics Engine

Metrics include:

- healing_accuracy
- recovery_latency
- reliability score

Regression impact classes:

- NONE
- MINOR
- MAJOR

Boolean flag:

- has_regression

---

### ✔ Quality Gate Decision Logic

Decisions:

- APPROVE_HEALING
- WARN
- BLOCK_HEALING

Based on:

- ML risk probability
- confidence thresholds
- quality metrics
- regression status
- test pass rate

---

### ✔ Real Playwright & Selenium Execution

Features:

- headless and headful browser automation
- demo bots for real websites
- failure bubbles into PTQA
- automatic execution timing
- JSON → bot parameter passing

Demo bots available:

- add/remove elements site
- dynamic loading site
- OrangeHRM login (Playwright)
- OrangeHRM login (Selenium)

---

### ✔ Video Recording Support

- Playwright screen recordings enabled
- `.webm` files stored for evidence
- path returned in PTQA test results

Output folder:

artifacts/videos/

---

### ✔ User Interfaces

| Feature | URL |
|--------|------|
| Interactive PTQA Console | /ui |
| PTQA Decisions Dashboard | /dashboard |
| Report Lookup | /ptqa/report/{healing_id} |
| API Documentation | /docs |

Dashboard displays:

- healing id
- risk level
- recommendation
- timestamp
- report link

---

## 4. Requirements Coverage Matrix

Requirement | Status
----------- | ------
ML Failure Prediction | ✔ Completed
Industrial Dataset | ✔ Completed
Regression Test Generation | ✔ Completed
Regression Execution | ✔ Completed
Quality Metrics Engine | ✔ Completed
Regression Detection | ✔ Completed
Execution Video Recording | ✔ Completed
Headful Browser Mode | ✔ Completed
API Endpoints | ✔ Completed
Interactive Manual UI | ✔ Completed
Historical Dashboard | ✔ Completed
CI/CD Quality Gate API | ✔ Completed
Database Storage | ✔ Completed

---

## 5. Folder Structure

ptqa_service/
  app/
    api/
    core/
    ml/
    db/
    utils/
  bots/
  artifacts/
  data/
  tests/

---

## 6. Running the System

Create virtual environment:

python -m venv venv
venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt
python -m playwright install

Train ML model:

python -m app.ml.train_pipeline

Run service:

uvicorn app.main:app --reload

Open:

http://127.0.0.1:8000/ui

---

## 7. User Manual

### Evaluate a healed script

Open:

http://127.0.0.1:8000/ui

Paste JSON  
Click Evaluate Healing

System:

- predicts failure probability
- runs real RPA script
- records result
- applies quality gate
- stores report

---

### Run headful browser for demo

Set:

"headless": false

---

### Retrieve PTQA report

/ptqa/report/H1001

---

### View dashboard

/dashboard

---

## 8. Example Output

"recommendation": "APPROVE_HEALING",
"risk_level": "LOW",
"will_work_probability": 0.72

---

## 9. Limitations & Future Enhancements

Completed previous limitations:

- Industrial dataset implemented
- Real RPA tool integration complete
- Video recording enabled
- Dashboard implemented

Future enhancements:

- Deep learning / LLM risk predictor
- Continual learning
- Cross-bot learning
- Self-explanation for ML decisions

---

## 10. Conclusion

PTQA delivers:

- ML-based risk scoring
- regression execution automation
- Playwright/Selenium integration
- performance regression detection
- CI/CD quality gate enforcement
- historical decision storage
- interactive user console

