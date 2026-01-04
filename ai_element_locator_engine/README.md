# AI-Powered Element Locator Engine (Member 2)

This repository contains the implementation of **Member 2 – AI-Powered Element Locator Engine**, a core microservice of the **AI-Enhanced Self-Healing RPA Framework: A Distributed Microservices Architecture for Autonomous Bot Recovery and Intelligent Code Generation**.

The Element Locator Engine is responsible for intelligently recovering broken UI element references when RPA bots fail due to dynamic user interface (UI) changes. It operates as an autonomous service that analyses failure metadata and the current DOM state, executes multiple locator strategies, and returns a ranked, reliability-scored candidate element to downstream components.

---

## 1. Role in the Overall Framework

In the full self-healing RPA framework, this component is invoked whenever a bot raises an **element-related failure** (e.g., ELEMENT_NOT_FOUND, Timeout waiting for selector).

High-level flow:

1. The Distributed Self-Healing Orchestrator detects a bot failure and sends a structured failure event to this service.
2. The Element Locator Engine:
   - retrieves or receives the current DOM of the target page,
   - analyses the failure context (old locator, expected role/text),
   - generates candidate elements using multiple strategies (DOM-based and AI-assisted),
   - ranks candidates using a reliability scoring mechanism (heuristics + ML),
   - returns the best locator with an attached confidence score.
3. The resulting Locator Engine Report is consumed by:
   - Code Generation & Healing Engine (Member 1)
   - Predictive Testing & Quality Framework (Member 3)

---

## 2. Objectives of the Element Locator Engine

1. Multi-strategy element detection
2. Robustness to UI changes
3. Machine-learning-based reliability scoring
4. Clear machine-readable I/O contracts
5. Clean microservice architecture and modular design

---

## 3. High-Level Architecture

The project is structured as a standalone Python microservice.

Directory structure:

ai_element_locator_engine/
  app/
    api.py              – FastAPI service
    config.py
    core/
      locator_engine.py – orchestrates strategies and scoring
      dom_fetcher.py    – obtains HTML/DOM
      dom_parser.py     – parsing utilities
      models/
        contracts.py    – Pydantic I/O contracts
        internal.py     – internal domain models
      strategies/       – locator strategies
      scoring/          – ML reliability model
    infra/
      logging_config.py
      settings.py
    tests/
  data/
    raw/
    processed/
    models/
  scripts/
  logs/
  README.md
  requirements.txt

### 3.1 Core Modules Summary

app/api.py – REST API  
locator_engine.py – core orchestrator  
dom_fetcher/ parser – DOM processing utilities  
strategies/ – pluggable strategies  
scoring/ – feature builder + ML model wrapper  

---

## 4. IO Contracts (Public Data Models)

The API uses Pydantic contracts.

### 4.1 Input: FailureFromOrchestrator (JSON)

Includes:
- page URL
- failure type
- old locator
- expected role/text
- DOM snapshot or live fetch signal
- failure metadata

### 4.2 Output: LocatorEngineReport (JSON)

Includes:
- metadata
- failure context
- DOM context
- element expectations
- best candidate locator
- confidence/reliability score

---

## 5. Locator Strategies

Implemented / planned strategies:

1. XPath Strategy  
2. Attribute & Text Similarity Strategy  
3. Planned Fuzzy DOM Strategy  
4. Planned Vision Strategy  

Each strategy proposes candidates independently.

---

## 6. Machine Learning Reliability Model

Features include:

- heuristic similarity score
- text similarity
- id/name similarity
- strategy identifiers
- future structural/visual metrics

Initial model:

- RandomForestClassifier (tree-based)

Fallback mode:

- if model missing, heuristics still operate safely

---

## 7. Non-Functional Goals

- accuracy
- low latency
- scalability
- extensibility
- observability and logging

---

## 8. Running the Service Locally

Prerequisites:

- Python 3.10+

Installation:

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

Start API:

uvicorn app.api:app --reload

Service URLs:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- GET /health

---

## 9. Future Work

- full fuzzy DOM matching
- full CV-based locator detection
- larger dataset ML training
- full integration with orchestration layer

---

## 10. Academic and Industrial Relevance

This component addresses UI locator brittleness in RPA systems by combining:

- multi-strategy element discovery
- ML-based reliability scoring
- microservices architecture

It is designed as both a practical system component and a research contribution.

