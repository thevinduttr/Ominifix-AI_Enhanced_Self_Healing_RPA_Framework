# OmniFix - AI-Enhanced Self-Healing RPA Framework

> Healing Engine Module  
> SLIIT Research Project | Algospring (PVT) LTD

OmniFix automatically detects broken Playwright locators, predicts the best healing strategy using ML, generates replacement selectors from DOM context, and patches scripts while preserving formatting.

---

## System Architecture

```
                          +---------------------+
                          |   ELR Input (JSON)   |
                          |  error_trace + DOM   |
                          +----------+----------+
                                     |
                          +----------v----------+
                          |  Failure Analyzer    |
                          |  (traceback parser)  |
                          +----------+----------+
                                     |
                          +----------v----------+
                          |  Strategy Predictor  |
                          |  (TF-IDF + RF model) |
                          +----------+----------+
                                     |
                    +----------------+----------------+
                    |                |                |
           +-------v------+ +------v-------+ +------v-------+
           | LOCATOR_REGEN| | CLICK_ONLY   | | FALLBACK_LOC |
           |   (LibCST)   | |              | |              |
           +--------------+ +--------------+ +--------------+
                    |                |                |
                    +----------------+----------------+
                                     |
                          +----------v----------+
                          |  Locator Generator   |
                          |  (BS4 DOM parsing)   |
                          +----------+----------+
                                     |
                          +----------v----------+
                          |  Script Patcher      |
                          |  (LibCST + fallback) |
                          +----------+----------+
                                     |
                          +----------v----------+
                          |  Healing Validator   |
                          |  (syntax check)      |
                          +----------+----------+
                                     |
                          +----------v----------+
                          |  Healed Script (.py) |
                          +---------------------+
```

---

## Project Structure

```
ai_rpa_healing_engine/
  src/
    analyzer/
      failure_analyzer.py     # Playwright traceback parser
    ast_engine/
      ast_parser.py           # AST utilities
    engine/
      healing_engine.py       # Core orchestrator
      healing_router.py       # Strategy routing & gates
      healing_validator.py    # Syntax validation
    locator_gen/
      locator_generator.py    # DOM -> selector candidates
    ml/
      strategy_predictor.py   # ML model inference
      train_strategy_model.py # TF-IDF + RandomForest training
      sample_generator.py     # Synthetic training data generator
      dataset_logger.py       # Healing outcomes -> CSV logger
    patcher/
      libcst_patcher.py       # Format-preserving code patching
      script_patcher.py       # Legacy patcher
    runner/
      heal.py                 # CLI single-case healer
      run_batch_healing.py    # Batch healing on all inputs
      run_engine.py           # Engine entry point
    templates/
      template_manager.py     # Script template management
    ui/
      app.py                  # Streamlit dashboard
  tests/
    test_failure_analyzer.py  # 16 tests - traceback parsing
    test_locator_generator.py # 17 tests - selector generation
    test_script_patcher.py    # 8 tests  - LibCST patching
    test_healing_validator.py # 7 tests  - syntax validation
    test_strategy_predictor.py# 11 tests - ML predictions
  tools/
    stress_test.py            # Batch validation (150 cases)
    run_full_loop.py          # End-to-end loop demo
    failure_injector.py       # Inject failures for testing
  models/
    strategy_selector_v1.pkl  # Trained ML model
  data/
    synthetic_inputs/batch/   # 150 generated ELR inputs
    synthetic_outputs/        # Healing results
    results/                  # Stress test & evaluation outputs
    scripts/
      broken/                 # Broken RPA scripts
      healed/                 # Healed output scripts
      original/               # Reference scripts
```

---

## Setup

### Prerequisites

- Python 3.12+
- pip

### Installation

```powershell
# Clone and navigate to the healing engine
cd ai_rpa_healing_engine

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
pip install pytest  # for testing
```

---

## Usage

### 1. Train the ML Model

Generate synthetic training data, run batch healing to build the dataset, then train:

```powershell
# Generate 150 synthetic ELR inputs
python -m src.ml.sample_generator

# Run batch healing to produce dataset CSV
python -m src.runner.run_batch_healing

# Train the strategy selector model
python -m src.ml.train_strategy_model

# Evaluate model accuracy (optional)
python evaluate_strategy_model.py
```

**Expected Output:** Model saved to `models/strategy_selector_v1.pkl`, accuracy >= 80%.

### 2. Heal a Single Failure

```powershell
python -m src.runner.heal --input data/synthetic_inputs/batch/elr_input_001.json
```

### 3. Run End-to-End Loop

Injects a failure into a script, then heals it automatically:

```powershell
python -m tools.run_full_loop --input data/inbox/elr_inputs/BOT-SLIIT-PDP-01/2026-01-04/elr_input--20260104--090001.json
```

### 4. Launch the Dashboard

```powershell
streamlit run src/ui/app.py
```

---

## Testing

### Run All Tests

```powershell
python -m pytest tests/ -v
```

**59 tests** across 5 modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_failure_analyzer.py` | 16 | Traceback parsing, error classification, locator extraction |
| `test_locator_generator.py` | 17 | ID/attribute/XPath candidates, scoring, pick_best |
| `test_script_patcher.py` | 8 | LibCST patching, fallback, failure handling |
| `test_healing_validator.py` | 7 | Syntax validation, edge cases |
| `test_strategy_predictor.py` | 11 | Model loading, predictions, confidence ranges |

### Run Stress Test

Validates the full pipeline on all 150 synthetic cases:

```powershell
python -m tools.stress_test --verbose
```

**Expected Output:**

```
Total Cases:            150
SUCCESS:                132 (88.0%)
NO_FIX:                 18 (12.0%)
FAILED:                 0 (0.0%)
Incorrect Patch Rate:   0 (0.0%)
NO_FIX Correctness:     18/18 (100.0%)
```

Results saved to `data/results/stress_test_results.json`.

---

## ML Pipeline

| Component | Details |
|-----------|---------|
| **Features** | TF-IDF vectorization of `"{error_type} {old_locator} {element_html}"` |
| **Model** | RandomForestClassifier (scikit-learn) |
| **Labels** | `LOCATOR_REGEN_LIBCST`, `FALLBACK_LOCATOR`, `CLICK_ONLY` |
| **Training Data** | 476+ synthetic samples via `sample_generator.py` |
| **Accuracy** | 100% on test split |
| **Confidence Thresholds** | Aggressive >= 0.70, Conservative >= 0.50 |

---

## Healing Strategies

| Strategy | When Used | What It Does |
|----------|-----------|--------------|
| `LOCATOR_REGEN_LIBCST` | Element has ID, unique attributes | Regenerates selector from DOM, patches via LibCST |
| `FALLBACK_LOCATOR` | No ID, uses name/aria-label/placeholder | Generates fallback selectors, applies line-level patch |
| `CLICK_ONLY` | Click actions on buttons/links | Generates click-specific selectors |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Healing Success Rate | 88.0% |
| NO_FIX Correctness | 100.0% |
| Incorrect Patch Rate | 0.0% |
| Avg Time-to-Heal | 73ms |
| Test Suite | 59/59 passing |

---

## License

SLIIT Research Project - All rights reserved.
