# OmniiFix — Research Component Completion Plan

Complete the AI-Enhanced Self-Healing RPA Framework from its current PP1 state into a **professional, submission-ready research component** that can be independently validated. The work is split into 5 phases that directly map to the research contributions in the thesis.

> [!IMPORTANT]
> The user's [my_plan.md](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/documentation/my_plan.md) suggestions are **all incorporated** here. `CLICK_ONLY`, `FALLBACK_XPATH`, confidence-aware healing, stress testing at 150+ cases, and the plug-in JSON integration model are all part of this plan.

---

## Proposed Changes

### Phase 1 — ML Pipeline Completion

---

#### [MODIFY] [train_strategy_model.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/train_strategy_model.py)

Currently a 3-line placeholder. Replace with a full, reproducible training script:
- Load `data/ml/healing_dataset.csv`
- Feature: concatenate `error_type + old_locator + element_html`
- Train: `Pipeline(TfidfVectorizer(ngram_range=(1,2)) + RandomForestClassifier(n_estimators=100, class_weight='balanced'))`
- Validate on 80/20 stratified split
- Save model to `models/strategy_selector_v1.pkl`
- Save evaluation metrics to `data/results/train_results.json`
- Save confusion matrix PNG to `data/results/confusion_matrix.png`

---

#### [MODIFY] [sample_generator.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/sample_generator.py)

Expand from 3-class to **5-class** dataset to match the full strategy taxonomy from [my_plan.md](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/documentation/my_plan.md):
- `LOCATOR_REGEN_LIBCST` — element has id, heal with `#id` selector
- `FALLBACK_LOCATOR` — no id, has `aria-label` / `placeholder` / [name](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/patcher/libcst_patcher.py#31-35)
- `FALLBACK_XPATH` — no CSS-friendly attributes, must use XPath
- `CLICK_ONLY` — button/link elements where action is `click` (new class)
- `NO_FIX` — empty/whitespace DOM, unfixable failures

Expand total sample count to **150** for statistically meaningful evaluation.

---

#### [MODIFY] [dataset_logger.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/dataset_logger.py)

Add `CLICK_ONLY` and `FALLBACK_XPATH` to `ALLOWED_STRATEGIES` set.

---

#### [MODIFY] [evaluate_strategy_model.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/evaluate_strategy_model.py)

Fix critical bugs + enhance:
- Fix column name: `new_element_html` → `element_html`  
- Fix feature column list to match [dataset_logger.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/dataset_logger.py) header  
- Add **ZeroR baseline** (majority class) for comparison  
- Save confusion matrix PNG to `data/results/`  
- Save classification report as JSON to `data/results/`  
- Print per-class precision/recall/F1

---

#### [MODIFY] [heal.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/runner/heal.py)

Add **confidence-aware healing gate** (from [my_plan.md](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/documentation/my_plan.md) Step 3.2):
```python
MIN_CONFIDENCE = 0.70
CONSERVATIVE_THRESHOLD = 0.50

if pred.confidence >= MIN_CONFIDENCE:
    # Aggressive healing — proceed with best locator candidate
elif pred.confidence >= CONSERVATIVE_THRESHOLD:
    # Conservative healing — only use id-based locators (#id)
else:
    # No fix — confidence too low, log reason
```

---

### Phase 2 — Failure Analysis & Integration

---

#### [MODIFY] [failure_analyzer.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/analyzer/failure_analyzer.py)

Implement (currently a stub). The `FailureAnalyzer` class will:
- Accept a raw Playwright traceback string
- Parse it using regex to extract: action, failing line number, error type, old locator, error message
- Return a structured `failure_context` dict compatible with the ELR JSON schema
- Support error types: `ELEMENT_NOT_FOUND`, `TIMEOUT_WAITING_FOR_SELECTOR`, `STRICT_MODE_VIOLATION`, `DETACHED_FROM_DOM`, `NOT_VISIBLE`, `NOT_ENABLED`

---

#### [NEW] [tools/failure_injector.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tools/failure_injector.py)

Controlled failure injection for research validation:
- Takes an RPA script path + target line number + old locator
- Corrupts the locator (appends `_BROKEN_` suffix) to deliberately trigger failure
- Creates a broken copy of the script for testing
- Generates a corresponding ELR input JSON

---

#### [NEW] [tools/run_full_loop.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tools/run_full_loop.py)

The **flagship integration tool** demonstrating end-to-end self-healing. Plug-in style, JSON-based, minimal coupling (as per [my_plan.md](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/documentation/my_plan.md) Step 4.2):
1. Accept an ELR input JSON  
2. Run the failing RPA script → capture the error  
3. Route through healing engine  
4. Re-run healed script → capture outcome  
5. Log: `original_status`, `healing_status`, `post_healing_status`, `time_to_heal_ms`

---

### Phase 3 — Stress Testing & Validation

---

#### [NEW] [tools/stress_test.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tools/stress_test.py)

Runs healing on all 150 synthetic cases. Reports:
- Overall healing success rate (%)
- Per-strategy success rate
- Incorrect patch rate (healed but wrong locator)
- NO_FIX correctness rate
- Confidence distribution per strategy
- Average time-to-heal (ms)

Saves full structured output to `data/results/stress_test_results.json` and summary charts.

---

### Phase 4 — Test Suite

---

#### [NEW] [tests/test_locator_generator.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tests/test_locator_generator.py)
- Test id-based candidate (#id) returned with score 100
- Test aria-label fallback when no id
- Test XPath fallback for bare elements
- Test empty HTML returns []
- Test [pick_best](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/locator_gen/locator_generator.py#78-82) returns highest-scored candidate

#### [NEW] [tests/test_script_patcher.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tests/test_script_patcher.py)
- Test successful LibCST patch on a known script
- Test fallback line-patch when LibCST fails
- Test failure returns [PatchResult(status="FAILED")](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/patcher/libcst_patcher.py#13-20)

#### [NEW] [tests/test_healing_validator.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tests/test_healing_validator.py)
- Test valid Python file → `valid: True`
- Test file with SyntaxError → `valid: False`

#### [NEW] [tests/test_strategy_predictor.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tests/test_strategy_predictor.py)
- Smoke test: model loads without error
- Test prediction returns a [StrategyPrediction](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/strategy_predictor.py#8-12) with valid label and 0.0–1.0 confidence

#### [NEW] [tests/test_failure_analyzer.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/tests/test_failure_analyzer.py)
- Test parsing of a known Playwright `TimeoutError` traceback
- Test parsing of `strict mode violation` error
- Test unknown error type returns safe defaults

---

### Phase 5 — README & Documentation

#### [MODIFY] [README.md](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/README.md)

Currently empty. Write a professional README covering:
- System architecture diagram (ASCII)
- Setup instructions
- How to run the training pipeline
- How to run the healing engine
- How to run stress tests
- How to run pytest

---

## Verification Plan

### Automated Tests

Run after Phase 4 is complete:

```powershell
# From: ai_rpa_healing_engine/
cd "c:\Users\ThevinduRathnaweera\OneDrive - Algospring (PVT) LTD\Desktop\SLIIT_RESEARCH\Ominifix-AI_Enhanced_Self_Healing_RPA_Framework\ai_rpa_healing_engine"
python -m pytest tests/ -v
```

Expected: All tests pass (green).

### Training Pipeline Verification

```powershell
cd ai_rpa_healing_engine
python -m src.runner.run_batch_healing   # generates dataset CSV
python -m src.ml.train_strategy_model    # trains + saves .pkl
python evaluate_strategy_model.py        # prints accuracy + saves charts
```

Expected: Model accuracy ≥ 80% on test split, confusion matrix PNG saved to `data/results/`.

### Stress Test Verification

```powershell
python tools/stress_test.py
```

Expected: Output shows healing success rate ≥ 70%, `data/results/stress_test_results.json` created.

### End-to-End Loop Verification

```powershell
python tools/run_full_loop.py --input data/inbox/elr_inputs/<sample>.json
```

Expected: Prints `original_status=FAILED`, `healing_status=SUCCESS`, healed script path displayed.

### Manual Verification (for Thesis/Demo)
1. Open `data/results/confusion_matrix.png` → verify matrix looks correct (diagonal dominant)
2. Open `data/results/stress_test_results.json` → verify success rate and per-strategy breakdown
3. Open a healed script in `data/scripts/healed/` → visually confirm locator was replaced correctly
