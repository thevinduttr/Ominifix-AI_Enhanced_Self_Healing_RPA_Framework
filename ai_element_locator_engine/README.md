# README.md — AI-Powered Element Locator Engine

## 1. Overview
This repository contains the implementation of the **AI-Powered Element Locator Engine**, which is the Member 2 (IT22352026) Component of the AI-Enhanced Self-Healing RPA Framework. 

The locator engine is responsible for automatically recovering from UI locator failures by generating new element selectors when RPA bots fail due to UI changes. The component reduces “Element Not Found” exceptions and increases the robustness of automation workflows.

It combines:

- Machine-learning confidence scoring  
- OpenCV-based visual template matching  
- Attribute changes (id, name, class)
- Structural modifications
- Text updates
- Tag migrations
- Element relocation
- Visual style changes

The engine integrates:

- Multi-strategy DOM analysis
- Real-time DOM retrieval from live URLs
- OpenCV-based visual template matching
- Machine-learning reliability scoring
- Confidence threshold gating
- Structured JSON API contracts
- Interactive dashboard-based evaluation


The system is implemented as a standalone **FastAPI microservice** and integrates with:

- Distributed Self-Healing Orchestrator  
- Code Generation & Healing Engine  
- Predictive Testing & QA Engine  

It also includes an interactive **React-based dashboard** for experimentation, evaluation, and viva demonstration.

---

## 2. Main Functional Objectives
The objectives assigned to this component were:
- Detect web elements even after UI structure or attribute changes
- Reduce RPA bot element-not-found failures
- Provide multi-strategy element locator generation
- Support machine-learning-based confidence scoring
- Support OpenCV vision-based locator recovery  
- Integrate with other microservices through JSON APIs
- Provide structured reports to the orchestrator
- Provide evaluation and visualization tools

---

## 3. Features Implemented (Current Status)

### Core engine functionality (Completed)
| Feature                                       | Status     |
|-----------------------------------------------|-----------|
| DOM fetch from snapshot or URL                | Completed |
| Graceful failure when DOM unavailable         | Completed |
| Multi-strategy execution pipeline             | Completed |
| Optional DOM execution model                  | Completed |
| ML reliability scoring                        | Completed |
| Confidence threshold gating                   | Completed |
| Structured JSON report generation             | Completed |
| Swagger/OpenAPI documentation                 | Completed |

### Locator strategies implemented
| Strategy                 | Status    | Description                                |
|--------------------------|-----------|--------------------------------------------|
| XPath Strategy           | Completed | Validates and reuses original XPath        |
| CSS Strategy             | Completed | Placeholder for CSS resolution integration |
| Attribute Similarity     | Completed | id, name, class, visible text matching     |
| Fuzzy DOM Structure      | Completed | Ancestor path and depth similarity         |
| Vision Template Matching | Completed | OpenCV edge-based template detection       |

The engine supports:

- DOM-only execution  
- Vision-only fallback  
- Hybrid DOM + Vision execution 

---

## 4. OpenCV Vision Component

The vision-based strategy is fully implemented using:

- Canny edge detection  
- OpenCV template matching (`TM_CCOEFF_NORMED`)  
- Per-template threshold tuning  
- Vision-only fallback when DOM is unavailable  
- Integration into ML scoring pipeline  

### Vision Capabilities

- Accepts `screenshot_path` and `template_path`
- Computes normalized match score in range `[0,1]`
- Applies configurable per-template thresholds
- Produces DOM-aligned candidates when DOM is available
- Produces fallback candidate when DOM is unavailable
- Injects vision features into reliability model

Vision signals are visible in the dashboard.

---

### 5. Machine learning reliability scoring
| Component                   | Status    |
|-----------------------------|-----------|
| Feature builder             | Completed |
| dataset generator           | Completed |
| RandomForest training       | Completed |
| ROC-AUC and Accuracy eval   | Completed |
| Model persistence (.pkl)    | Completed |
| Runtime inference           | Completed |
| Confidence threshold gating | Completed |

### Model Performance (Train Dataset)

- Accuracy: **84.88%**
- ROC-AUC: **89.45%**

If the model is unavailable, the system falls back to heuristic scoring.

Confidence thresholding prevents unreliable locator recovery.

---

## 6. System Architecture Role

### Processing Pipeline
Failure → DOM Retrieval → Multi-Strategy Execution → ML Scoring → Confidence Gate → Structured Report


### Inputs

- Page URL  
- Old locator and type  
- Expected text  
- Optional DOM snapshot  
- Optional screenshot and template  
- Execution metadata  

### Outputs

- Recovered XPath  
- Recovered CSS selector  
- Strategy used  
- Confidence score  
- HTML snippet  
- Structured JSON report  

---

## 7. Datasets

### 7.1 Training Dataset

- > 5000 samples  
- Valid and broken locator cases  
- Injected label noise  
- Overlapping feature distributions  

Used for training the RandomForest reliability model.

---

### 7.2 Real DOM Snapshot Dataset

Collected from demo applications.

Simulated modifications include:

- ID changes  
- Text changes  
- Element relocation  
- Tag migration  

Used for DOM-based strategy testing.

---

### 7.3 Vision Evaluation Dataset

Stored under:
  data/raw/screenshots/full
  data/raw/screenshots/templates


Includes:

- login_button  
- checkbox  
- dropdown_select  
- add_button  
- delete  

Thresholds tuned empirically.

---

## 8. API Description

Backend implemented using **FastAPI**.

### Endpoints

**GET /health**  
Service liveness check.

**POST /element-locator/report**  
Generates locator recovery report.

### Response Includes

- Recovered XPath  
- Recovered CSS  
- Final confidence score  
- Strategy used  
- HTML snippet  
- Metadata (report_id, run_id, timestamp)

Supports DOM-only, vision-only, and hybrid execution modes.

---

## 9. Technologies Used

### Backend

- Python 3  
- FastAPI  
- Uvicorn  
- Scikit-learn  
- OpenCV  
- BeautifulSoup  
- lxml  
- Requests  
- Pydantic  

### Frontend

- React (Vite)  
- Axios  
- Chart.js  
- Tailwind CSS  

### Machine Learning

- Feature engineering  
- RandomForest classifier  
- Model serialization  
- Runtime inference  

---

## 10. How to Run

### Backend

1. Create virtual environment  
2. Activate environment  
3. Install dependencies  
4. Run: uvicorn app.api:app --reload
5. Open: http://127.0.0.1:8000/doc

---

### Frontend Dashboard

1. Navigate to `locator-dashboard`  
2. Run:
      npm install
  # optional: if backend runs on a non-default port
  # set VITE_API_BASE_URL (default is http://127.0.0.1:8001)
      npm run dev
3. Open:http://localhost:5173

If your backend is started with `uvicorn app.api:app --reload` on port `8000`, run:

```
set VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev
```


---

## 11. Dashboard Usage

The dashboard allows:

- Testing DOM-based recovery  
- Testing vision-based recovery  
- Running hybrid scenarios  
- Viewing JSON reports  
- Viewing confidence scores  
- Viewing strategy usage  
- Inspecting matched HTML snippets  
- Reviewing run history  

If `page_html` is provided, the engine skips HTTP fetching.

If URL is unreachable, vision strategy can still execute.

---

## 10. Requirements Coverage Summary

### Fully Completed

- Multi-strategy locator engine  
- DOM-optional execution
- Real-time URL execution
- Snapshot-based replay capability  
- ML reliability scoring  
- OpenCV template matching  
- Confidence gating  
- JSON API contracts  
- Interactive dashboard  
- Dataset training  
- Hybrid execution model  

### Partially Completed

- Browser automation integration (Playwright/Selenium)
- Persistent database storage
- Containerized deployment

### Future Extensions

- YOLO-based visual detection  
- Large-scale benchmark dataset  
- Online incremental learning  
- Kubernetes deployment  
- CI/CD integration  

---

## 13. Conclusion

The AI-Powered Element Locator Engine demonstrates:

- Autonomous locator healing  
- Multi-strategy detection  
- Real-time DOM retrieval
- Hybrid DOM and vision fusion 
- Safe recovery through threshold gating 
- Structured microservice integration
- ML-assisted confidence scoring  
- Dashboard-driven evaluation  

The OpenCV component is fully implemented and integrated into the scoring pipeline.

This component significantly reduces element-not-found failures and strengthens RPA automation resilience.

---

## 14. Implementation File Mapping

### DOM Fetching and Parsing
- `app/core/dom_fetcher.py`
- `app/core/dom_parser.py`
- `app/core/models/internal.py`

### Strategy Architecture
- `app/core/locator_engine.py`
- `app/core/strategies/base.py`

### XPath Strategy
- `app/core/strategies/xpath_strategy.py`

### CSS Strategy
- `app/core/strategies/css_strategy.py`

### Attribute Strategy
- `app/core/strategies/attribute_strategy.py`

### Fuzzy DOM Strategy
- `app/core/strategies/fuzzy_dom_strategy.py`

### Vision Strategy (OpenCV)
- `app/core/strategies/vision_strategy.py`

### Reliability Model
- `app/core/scoring/feature_builder.py`
- `app/core/scoring/reliability_model.py`
- `scripts/train_reliability.py`
- `data/models/reliability_model.pkl`

### API and Contracts
- `app/api.py`
- `app/core/models/contracts.py`

### Logging and Configuration
- `app/infra/logging_config.py`
- `app/infra/settings.py`

### Frontend Dashboard
- `locator-dashboard/`

---


**Current State:**  
Fully functional hybrid DOM + Vision + ML locator recovery engine.