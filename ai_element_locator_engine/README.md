# README.md — AI-Powered Element Locator Engine

## 1. Overview
This repository contains the implementation of the AI-Powered Element Locator Engine, which is the Member 2 Component of the AI-Enhanced Self-Healing RPA Framework. The locator engine is responsible for automatically recovering from UI locator failures by generating new element selectors when RPA bots fail due to UI changes. The component reduces “Element Not Found” exceptions and increases the robustness of automation workflows.

This engine operates as an independent microservice and communicates with:
- Distributed Self-Healing Orchestrator
- Code Generation & Healing Engine
- Predictive Testing & QA Engine

It exposes a REST API and an interactive web-based testing dashboard for demonstration, evaluation, and experimentation.

---

## 2. Main Functional Objectives
The objectives assigned to this component were:
- Detect web elements even after UI change
- Reduce RPA bot element-not-found failures
- Provide multi-strategy element locator generation
- Support machine-learning-based confidence scoring
- Integrate with other microservices through JSON APIs
- Provide structured reports to the orchestrator
- Support evaluation through datasets and dashboard

---

## 3. Features Implemented (Current Status)

### Core engine functionality (Completed)
| Feature                          | Status     |
|----------------------------------|-----------|
| DOM fetch and parsing            | Completed |
| Multi-strategy locator detection | Completed |
| Fallback hierarchical execution  | Completed |
| JSON API interface               | Completed |
| Locator report generation        | Completed |
| Swagger/OpenAPI UI               | Completed |

### Locator strategies implemented
| Strategy                | Status     | Description                                           |
|------------------------|-----------|-------------------------------------------------------|
| XPath strategy         | Completed | Structural matching based on XPath paths              |
| CSS selector strategy  | Completed | CSS rule generation and matching                      |
| Attribute similarity   | Completed | id, name, class, text overlap analysis                |
| Fuzzy DOM strategy     | Completed | Fuzzy match based on tree resemblance                 |
| Vision strategy        | Planned   | To be implemented using OpenCV in next phase          |

### Machine learning reliability scoring
| Component                    | Status     |
|-----------------------------|-----------|
| Feature builder             | Completed |
| Synthetic dataset generator | Completed |
| RandomForest training       | Completed |
| ROC-AUC and Accuracy eval   | Completed |
| Model persistence (.pkl)    | Completed |
| Runtime inference           | Completed |

Current model results:
- Accuracy: 84.88%
- ROC-AUC: 89.45%
- Training performed on synthetic dataset with label noise

### Testing Dashboard (React + Vite)
The dashboard allows users to:
- execute test locators
- visualize locator recovery
- show JSON output
- display ML evaluation metrics
- show pie chart of strategy usage
- display confidence score charts
- test predefined failure scenarios
- manually paste DOM snapshots

Intended uses:
- viva demonstration
- research evaluation
- visualization of outcomes
- strategy comparison

---

## 4. System Architecture Role
Processing pipeline:
Failure → Analyze → Propose new locator → Score → Return Report

Inputs
- failed action type
- old locator
- page HTML or URL
- execution metadata

Outputs
- recovered locator candidate
- ML confidence probability
- chosen strategy
- structured JSON report
- identified element snippet

---

## 5. Datasets Used

### 5.1 Synthetic Training Dataset (Completed)
- More than 5000 generated samples
- Consists of:
  - valid locator cases
  - broken locator variations
  - injected label noise
  - overlapping feature distributions
- Used to train the RandomForest reliability model

### 5.2 Real DOM Snapshot Dataset (In Progress)
Collected from:
- the-internet.herokuapp.com/login
- other demo web applications

Snapshots modified to simulate:
- ID change
- text change
- element relocation
- button to anchor migration

### 5.3 Runtime Evaluation Dataset (Planned / Partial)
Planned capture:
- chosen strategy
- confidence score
- success flag
- target page

---

## 6. API Description
Base service implemented using FastAPI.

Endpoints:
- GET /health — service health check
- POST /element-locator/report — generate locator recovery report

The element-locator report endpoint accepts orchestrator failure JSON and returns:
- recovered XPath
- recovered CSS selector
- confidence score
- strategy used
- HTML snippet

---

## 7. Technologies Used

Backend
- Python 3
- FastAPI
- Uvicorn
- Scikit-learn
- BeautifulSoup / lxml
- Requests
- Pydantic

Frontend
- React (Vite)
- Chart.js
- Axios
- Tailwind CSS

Machine Learning
- feature extraction
- supervised training
- dataset generation script
- RandomForest model
- serialized .pkl model

---

## 8. How to Run the Component
Backend steps:
1. Create virtual environment
2. Activate environment (Windows or Linux / macOS)
3. Install dependencies from requirements.txt
4. Run Uvicorn server entrypoint app.api:app with reload enabled
5. Open Swagger UI at 127.0.0.1:8000/docs

Frontend dashboard steps:
1. Navigate to locator-dashboard directory
2. Run npm install
3. Run npm run dev
4. Open browser at localhost:5173

All of the above remains within this single markdown section intentionally without additional code blocks, as requested.

---

## 9. User Guide (Dashboard Usage)
Steps:
1. Open dashboard in browser
2. Choose a predefined failure scenario or provide:
   - Page URL
   - Expected text
   - Old locator
   - Optional DOM snapshot
3. Click “Run Locator Engine”

Dashboard shows:
- selected strategy
- new XPath and CSS
- confidence score
- JSON response
- history of runs
- pie chart and bar charts
- matched element HTML preview

If DOM snapshot is provided, the engine will not fetch the URL.

---

## 10. Requirements Coverage Summary

Completed
- multi-strategy locator engine
- ML scoring model
- API contracts
- JSON reporting layer
- interactive dashboard
- synthetic dataset training
- real DOM snapshot support
- result visualization

Partially completed
| Requirement                     | Status                |
|---------------------------------|-----------------------|
| Real website automation         | partially simulated   |
| Runtime evaluation dataset      | in progress           |
| Computer vision locator         | designed, not built   |
| Full orchestrator integration   | stubbed               |

Remaining and future work
- computer-vision locator using OpenCV or YOLO
- orchestrator integration in Docker or Kubernetes
- automatic screenshot ingestion
- larger benchmark datasets
- online incremental ML learning
- database persistence layer

---

## 11. Conclusion
The component successfully demonstrates:
- autonomous locator healing
- multi-strategy detection
- ML-assisted confidence scoring
- dashboard-driven testing and evaluation

It forms a core pillar of the Self-Healing RPA framework and significantly reduces element-not-found errors, improving automation robustness. Future developments will extend into vision-based recognition, richer datasets, and CI/CD integration.

---

## 12. Mapping of Requirements to Implementation Files

DOM Fetching and Parsing  
Files:
- app/core/dom_fetcher.py
- app/core/dom_parser.py
- app/core/models/internal.py  
Description:
dom_fetcher.py retrieves HTML from orchestrator snapshots or HTTP GET, dom_parser.py parses and normalizes HTML, and internal.py defines DOM snapshot models.

Multi-Strategy Locator Engine  
Files:
- app/core/locator_engine.py
- app/core/strategies (folder)  
Description:
Coordinates execution order of strategies, manages fallbacks, and composes final report.

XPath Strategy  
File:
- app/core/strategies/xpath_strategy.py  
Description:
Repairs and regenerates XPath expressions based on structural similarity.

CSS Selector Strategy  
File:
- app/core/strategies/css_strategy.py  
Description:
Builds robust CSS selectors based on tag, class combinations, and hierarchy.

Attribute Similarity Strategy  
File:
- app/core/strategies/attribute_strategy.py  
Description:
Uses id, name, class, type, and text similarity to locate elements.

Fuzzy DOM Matching Strategy  
File:
- app/core/strategies/fuzzy_dom_strategy.py  
Description:
Performs approximate DOM tree matching for relocated elements or layout refactors.

Machine Learning Reliability Model  
Files:
- app/core/scoring/feature_builder.py
- app/core/scoring/reliability_model.py
- scripts/train_reliability.py
- data/models/reliability_model.pkl  
Description:
Implements feature extraction, model training, inference, and persisted RandomForest model.

API Service and JSON Contracts  
Files:
- app/api.py
- app/core/models/contracts.py  
Description:
Defines REST API and strict Pydantic data contracts.

Central Logging and Configuration  
Files:
- app/infra/logging_config.py
- app/infra/settings.py  
Description:
Implements centralized logging and environment configuration handling.

Frontend Testing Dashboard  
Folder:
- locator-dashboard  
Description:
Provides interactive UI for testing, charts, JSON view, scenario buttons, and visual analytics.

---