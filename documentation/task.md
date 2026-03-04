# OmniiFix — Research Completion Task Checklist

## Phase 1 — ML Pipeline (CRITICAL — Do First)
- [ ] Implement [train_strategy_model.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/train_strategy_model.py) — real reproducible training (TF-IDF + RandomForest + multi-class)
- [ ] Expand [SampleGenerator](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/sample_generator.py#6-146) to produce 5-class dataset: `LOCATOR_REGEN_LIBCST`, `FALLBACK_LOCATOR`, `FALLBACK_XPATH`, `CLICK_ONLY`, `NO_FIX`
- [ ] Fix [evaluate_strategy_model.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/evaluate_strategy_model.py) — column name bug (`new_element_html` → `element_html`), add baseline, save charts
- [ ] Add confidence-aware threshold gate in [heal.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/runner/heal.py) (conservative vs aggressive healing, `MIN_CONFIDENCE = 0.70`)
- [ ] Update [DatasetLogger](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/dataset_logger.py#6-77) to include `CLICK_ONLY` and `FALLBACK_XPATH` strategy labels

## Phase 2 — Failure Analysis & Integration (HIGH PRIORITY)
- [ ] Implement [failure_analyzer.py](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/analyzer/failure_analyzer.py) — parse raw Playwright error trace into structured `failure_context`
- [ ] Build `tools/failure_injector.py` — deliberately corrupt locators in the RPA script to trigger failures
- [ ] Build `tools/run_full_loop.py` — end-to-end: Bot runs → fails → healing triggers → healed script re-runs → result logged

## Phase 3 — Stress Testing & Validation (RESEARCH QUALITY)
- [ ] Expand [SampleGenerator](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/sample_generator.py#6-146) to generate 150+ diverse synthetic failure cases across all 5 strategy classes
- [ ] Build `tools/stress_test.py` — runs batch healing on all synthetic cases and generates a summary report
- [ ] Produce final evaluation metrics: success rate, incorrect patch rate, NO_FIX correctness, confidence distribution
- [ ] Save evaluation results as structured JSON + PNG charts to `data/results/`

## Phase 4 — Code Quality & Tests
- [ ] Add `pytest` test suite for [LocatorGenerator](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/locator_gen/locator_generator.py#4-91) (CSS/XPath all types)
- [ ] Add `pytest` test for [ScriptPatcher](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/patcher/libcst_patcher.py#142-317) (success / fallback / failure cases)
- [ ] Add `pytest` test for [HealingValidator](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/engine/healing_validator.py#4-25) (valid + SyntaxError cases)
- [ ] Add `pytest` test for [StrategyPredictor](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/src/ml/strategy_predictor.py#14-46) (smoke test: model loads + predicts)
- [ ] Replace all raw `print()` with `logging` module calls
- [ ] Add type hints to all public functions
- [ ] Write proper [README.md](file:///c:/Users/ThevinduRathnaweera/OneDrive%20-%20Algospring%20%28PVT%29%20LTD/Desktop/SLIIT_RESEARCH/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine/README.md) for `ai_rpa_healing_engine`

## Phase 5 — Documentation & Research Artifacts
- [ ] Produce final `data/results/experiment_results.json` with all metrics
- [ ] Produce final `data/results/confusion_matrix.png`
- [ ] Update `documentation/` with final architecture diagram
