# OmniiFix — Code Healing Engine: API & System Documentation

> **Component:** Code Healing Engine REST API  
> **API Version:** 1.0.0  
> **Base URL:** `http://localhost:8000`  
> **Date:** March 2026  
> **Author:** Thevindu Rathnaweera  
> **Framework:** OmniiFix — AI-Enhanced Self-Healing RPA Framework

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Prerequisites & Installation](#2-prerequisites--installation)
3. [Starting the API Server](#3-starting-the-api-server)
4. [API Endpoints Overview](#4-api-endpoints-overview)
5. [Endpoint: Health Check](#5-endpoint-health-check)
6. [Endpoint: Heal Single Input](#6-endpoint-heal-single-input)
7. [Endpoint: Heal Batch](#7-endpoint-heal-batch)
8. [Input Schema Reference](#8-input-schema-reference)
9. [Output Schema Reference](#9-output-schema-reference)
10. [Status Codes & Error Handling](#10-status-codes--error-handling)
11. [Supported Error Types & Actions](#11-supported-error-types--actions)
12. [Confidence Thresholds & Healing Modes](#12-confidence-thresholds--healing-modes)
13. [Postman Testing Guide](#13-postman-testing-guide)
14. [Integration Code Samples](#14-integration-code-samples)
15. [Interactive API Docs (Swagger)](#15-interactive-api-docs-swagger)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. System Overview

The **Code Healing Engine** is the self-healing component of the OmniiFix framework. When an RPA bot fails due to a broken element locator (e.g., a CSS selector or XPath changed on a website), this engine:

1. **Receives** an ELR (Element Locator Report) JSON — via REST API or CLI
2. **Predicts** the best healing strategy using an ML classifier (TF-IDF + Random Forest)
3. **Generates** new locator candidates from the updated DOM HTML
4. **Merges** upstream `element_candidate` hints if provided (optional)
5. **Applies** confidence-aware healing gates (aggressive / conservative / no-fix)
6. **Patches** the broken RPA script with the correct new locator (using LibCST)
7. **Validates** the healed script (Python syntax check)
8. **Returns** a complete healing output JSON as the API response

```
┌─────────────────────┐         POST /api/v1/heal         ┌──────────────────────┐
│  Element Locator    │  ────── ELR JSON (request) ──────▶ │  Code Healing        │
│  Engine / RPA Bot   │                                    │  Engine API          │
│                     │  ◀──── Healing Output (response) ─ │  (FastAPI)           │
└─────────────────────┘                                    └──────────────────────┘
                                                                     │
                                                                     ▼
                                                           ┌──────────────────────┐
                                                           │  Predictive Testing  │
                                                           │  Engine (downstream) │
                                                           └──────────────────────┘
```

---

## 2. Prerequisites & Installation

### 2.1 System Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| OS | Windows / Linux / macOS |
| RAM | 2 GB minimum |
| Disk | 500 MB for models + dependencies |

### 2.2 Installation Steps

```bash
# 1. Clone or navigate to the project
cd Ominifix-AI_Enhanced_Self_Healing_RPA_Framework/ai_rpa_healing_engine

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 4. Install all dependencies
pip install -r requirements.txt
```

### 2.3 Required Dependencies

```
# Core
beautifulsoup4, lxml, libcst, python-dateutil

# Machine Learning
scikit-learn, joblib, numpy, pandas

# REST API
fastapi, uvicorn[standard], httpx

# Utilities
tqdm, streamlit, playwright
```

### 2.4 Verify Installation

```bash
# Check ML model exists
ls models/strategy_selector_v1.pkl

# Run test suite (97 tests should pass)
python -m pytest tests/ -v
```

### 2.5 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `RPA_ROOT` | No | Parent of `ai_rpa_healing_engine/` | Root path to RPA bot scripts. Set this if bot scripts are outside the engine directory. |

---

## 3. Starting the API Server

### 3.1 Standard Start

```bash
cd ai_rpa_healing_engine
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

### 3.2 Development Mode (auto-reload)

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3.3 Direct Python Run

```bash
python -m src.api.app
```

### 3.4 Verify Server is Running

```bash
curl http://localhost:8000/api/v1/health
```

**Expected:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "component": "code_healing_engine"
}
```

### 3.5 Server Configuration

| Setting | Default | Notes |
|---|---|---|
| Host | `0.0.0.0` | Accepts connections from any IP |
| Port | `8000` | Change with `--port <number>` |
| CORS | All origins allowed | Restrict in production |
| Swagger UI | `http://localhost:8000/docs` | Interactive API testing |
| ReDoc | `http://localhost:8000/redoc` | Alternative API docs |

---

## 4. API Endpoints Overview

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/health` | Health check & version info | None |
| `POST` | `/api/v1/heal` | Heal a single ELR input | None |
| `POST` | `/api/v1/heal/batch` | Heal multiple ELR inputs | None |

**Base URL:** `http://localhost:8000`  
**Content-Type:** `application/json` (for POST requests)

---

## 5. Endpoint: Health Check

### `GET /api/v1/health`

Returns the current status and version of the API.

**Request:**
```
GET http://localhost:8000/api/v1/health
```

No headers or body required.

**Response — 200 OK:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "component": "code_healing_engine"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | Always `"ok"` when running |
| `version` | string | API version number |
| `component` | string | Component identifier |

---

## 6. Endpoint: Heal Single Input

### `POST /api/v1/heal`

Accepts a single ELR (Element Locator Report) JSON input, processes it through the healing engine, and returns the full healing output.

**Headers:**
```
Content-Type: application/json
```

### 6.1 Minimum Required Input

The bare minimum fields needed:

```json
{
  "metadata": {
    "bot_id": "BOT-MY-SYSTEM-01"
  },
  "failure_context": {
    "script_path": "path/to/broken_script.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-btn-old",
    "error_type": "ELEMENT_NOT_FOUND"
  },
  "dom_context": {
    "new_element_html": "<button id=\"submit-btn\" class=\"btn\">Submit</button>"
  }
}
```

### 6.2 Full Input (All Fields)

```json
{
  "metadata": {
    "schema_version": "1.0",
    "report_id": "ELR-001",
    "run_id": "run-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T14:00:00Z",
    "source_component": "element_locator_engine",
    "target_component": "code_healing_engine",
    "environment": "production"
  },
  "failure_context": {
    "script_path": "bots/checkout_flow.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "dom_context": {
    "new_element_html": "<button id=\"submit-order\" class=\"btn primary\" data-testid=\"checkout-submit\">Place Order</button>",
    "page_url": "https://example.com/checkout",
    "page_name": "Checkout Page"
  },
  "element_expectation": {
    "expected_role": "button",
    "expected_text": "Place Order"
  },
  "element_candidate": {
    "css": "#submit-order",
    "xpath": "//button[@id='submit-order']",
    "full_xpath": "/html/body/div[2]/form/button[1]",
    "score": 85,
    "strategy": "attribute_match"
  }
}
```

### 6.3 Success Response — 200 OK

```json
{
  "metadata": {
    "healing_id": "HEAL-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "report_id": "ELR-001",
    "run_id": "run-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T14:00:05.123456",
    "source_component": "code_healing_engine",
    "target_component": "predictive_testing_engine"
  },
  "failure_context": {
    "script_path": "bots/checkout_flow.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "dom_context": {
    "page_url": "https://example.com/checkout",
    "page_name": "Checkout Page",
    "new_element_html": "<button id=\"submit-order\" class=\"btn primary\" data-testid=\"checkout-submit\">Place Order</button>"
  },
  "element_expectation": {
    "expected_role": "button",
    "expected_text": "Place Order"
  },
  "element_candidate": {
    "css": "#submit-order",
    "xpath": "//button[@id='submit-order']",
    "full_xpath": "/html/body/div[2]/form/button[1]",
    "score": 85,
    "strategy": "attribute_match"
  },
  "healing_summary": {
    "status": "SUCCESS",
    "strategy_used": "LOCATOR_REGEN_LIBCST",
    "action": "click",
    "old_locator": "#submit-order-old",
    "new_locator": "#submit-order",
    "confidence": 0.85,
    "patcher": "LibCST",
    "validation": {
      "valid": true,
      "reason": "OK"
    }
  },
  "script_output": {
    "original_script_path": "/full/path/to/bots/checkout_flow.py",
    "healed_script_path": "data/outbox/healed_scripts/BOT-ECOMMERCE-01/2026-03-05/healed_script--20260305--140005.py"
  },
  "model_info": {
    "model": "strategy_selector_v1",
    "confidence": 0.88,
    "healing_mode": "aggressive",
    "ml_confidence": 0.88
  }
}
```

### 6.4 NO_FIX Response — 200 OK

When the engine cannot heal (still returns 200, check `healing_summary.status`):

```json
{
  "healing_summary": {
    "status": "NO_FIX",
    "strategy_used": "NO_FIX",
    "old_locator": "#submit-order-old",
    "new_locator": "",
    "confidence": 0.42,
    "patcher": "N/A",
    "validation": {
      "valid": true,
      "reason": "ML confidence 0.4200 < 0.50. Threshold too low for safe healing."
    }
  }
}
```

---

## 7. Endpoint: Heal Batch

### `POST /api/v1/heal/batch`

Heals multiple ELR inputs in a single API call. Each input is processed sequentially and individual results are returned.

**Headers:**
```
Content-Type: application/json
```

### 7.1 Request

```json
{
  "inputs": [
    {
      "metadata": { "bot_id": "BOT-SEARCH-01", "run_id": "batch-001" },
      "failure_context": {
        "script_path": "data/scripts/broken/search_flow.py",
        "failing_line": 13,
        "action": "fill",
        "old_locator": "textarea[name='qqq']",
        "error_type": "ELEMENT_NOT_FOUND"
      },
      "dom_context": {
        "new_element_html": "<textarea class=\"gLFyf\" name=\"q\" aria-label=\"Search\"></textarea>"
      }
    },
    {
      "metadata": { "bot_id": "BOT-LOGIN-01", "run_id": "batch-002" },
      "failure_context": {
        "script_path": "bots/login_flow.py",
        "failing_line": 8,
        "action": "click",
        "old_locator": "#login-old",
        "error_type": "ELEMENT_NOT_FOUND"
      },
      "dom_context": {
        "new_element_html": ""
      }
    }
  ]
}
```

### 7.2 Response — 200 OK

```json
{
  "total": 2,
  "success": 1,
  "no_fix": 1,
  "failed": 0,
  "results": [
    {
      "metadata": { "healing_id": "HEAL-...", "bot_id": "BOT-SEARCH-01", "..." : "..." },
      "healing_summary": {
        "status": "SUCCESS",
        "new_locator": "textarea[name=\"q\"]",
        "confidence": 0.8
      },
      "...": "..."
    },
    {
      "metadata": { "healing_id": "HEAL-...", "bot_id": "BOT-LOGIN-01", "..." : "..." },
      "healing_summary": {
        "status": "NO_FIX",
        "validation": {
          "reason": "Missing dom_context.new_element_html; cannot regenerate locator."
        }
      },
      "...": "..."
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `total` | int | Total number of inputs processed |
| `success` | int | Count of inputs healed successfully |
| `no_fix` | int | Count of inputs where no fix was possible |
| `failed` | int | Count of inputs that caused errors |
| `results` | array | Full healing output for each input |

---

## 8. Input Schema Reference

### 8.1 Top-Level Structure

| Field | Type | Required | Description |
|---|---|---|---|
| `metadata` | object | **Yes** | Bot and run identifiers |
| `failure_context` | object | **Yes** | Details about the failure |
| `dom_context` | object | **Yes** | Current DOM state |
| `element_expectation` | object | No | Expected element properties |
| `element_candidate` | object | No | Upstream locator hints (from Element Locator Engine) |

### 8.2 `metadata` Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `bot_id` | string | **Yes** | Unique bot identifier (e.g., `"BOT-ECOMMERCE-01"`) |
| `run_id` | string | No | Run/session identifier |
| `report_id` | string | No | ELR report ID |
| `schema_version` | string | No | Input schema version (default: `"1.0"`) |
| `timestamp` | string | No | ISO 8601 timestamp of the failure |
| `source_component` | string | No | Who sent this (default: `"element_locator_engine"`) |
| `target_component` | string | No | Where to send (default: `"code_healing_engine"`) |
| `environment` | string | No | `"production"`, `"qa"`, `"dev"`, etc. |

### 8.3 `failure_context` Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `script_path` | string | **Yes** | Path to the broken RPA Python script |
| `failing_line` | integer | **Yes** | Line number that failed (1-indexed) |
| `action` | string | **Yes** | Playwright action: `click`, `fill`, `wait_for_selector`, `query_selector_all`, `locator` |
| `old_locator` | string | **Yes** | The broken CSS selector or XPath |
| `error_type` | string | **Yes** | Error classification (see Section 11) |
| `error_message` | string | No | Full error text from Playwright |

### 8.4 `dom_context` Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `new_element_html` | string | **Yes** | Current HTML snippet of the target element from the live page |
| `page_url` | string | No | URL where the failure occurred |
| `page_name` | string | No | Friendly page label |

### 8.5 `element_expectation` Fields (Optional)

| Field | Type | Required | Description |
|---|---|---|---|
| `expected_role` | string | No | Semantic role: `button`, `link`, `input`, etc. |
| `expected_text` | string | No | Visible text of the element |

### 8.6 `element_candidate` Fields (Optional)

Upstream locator hints from the Element Locator Engine. If provided, these are merged into the locator candidates. Handled gracefully if `null` or partially filled.

| Field | Type | Required | Description |
|---|---|---|---|
| `css` | string | No | CSS selector hint |
| `xpath` | string | No | XPath hint |
| `full_xpath` | string | No | Absolute XPath hint |
| `score` | float | No | Upstream confidence score (0–100) |
| `strategy` | string | No | How the upstream found this candidate |

**Merge behavior:** External candidates are capped at score 90 so local ID-based locators (score=100) always win. If the external value matches an existing candidate, the score is boosted instead of adding a duplicate.

---

## 9. Output Schema Reference

### 9.1 Top-Level Structure

| Field | Type | Always Present | Description |
|---|---|---|---|
| `metadata` | object | Yes | Healing run identifiers |
| `failure_context` | object | Yes | Echoed from input |
| `dom_context` | object | Yes | Echoed from input |
| `element_expectation` | object | Yes | Echoed from input |
| `element_candidate` | object/null | Yes | Echoed from input (null if not provided) |
| `healing_summary` | object | Yes | **Main result — check this** |
| `script_output` | object | Yes | Paths to original and healed scripts |
| `model_info` | object | Yes | ML model details |

### 9.2 `metadata` Output Fields

| Field | Type | Description |
|---|---|---|
| `healing_id` | string | Unique UUID for this healing run (e.g., `"HEAL-a1b2c3d4-..."`) |
| `report_id` | string | Echoed from input |
| `run_id` | string | Echoed from input |
| `bot_id` | string | Echoed from input |
| `timestamp` | string | ISO 8601 timestamp when healing was performed |
| `source_component` | string | Always `"code_healing_engine"` |
| `target_component` | string | Downstream consumer (default: `"predictive_testing_engine"`) |

### 9.3 `healing_summary` Output Fields ★

**This is the most important section in the response.**

| Field | Type | Description |
|---|---|---|
| `status` | string | **`"SUCCESS"`** / **`"NO_FIX"`** / **`"FAILED"`** |
| `strategy_used` | string | `"LOCATOR_REGEN_LIBCST"`, `"LOCATOR_REGEN_BASIC"`, `"FALLBACK_LOCATOR"`, `"NO_FIX"` |
| `action` | string | Playwright action (echoed, lowercase) |
| `old_locator` | string | The broken selector (echoed) |
| `new_locator` | string | **The healed selector** (empty if NO_FIX) |
| `confidence` | float | Healing confidence score (0.0 – 1.0) |
| `patcher` | string | `"LibCST"`, `"basic"`, or `"N/A"` |
| `validation` | object | `{"valid": true/false, "reason": "..."}` |

### 9.4 `script_output` Output Fields

| Field | Type | Description |
|---|---|---|
| `original_script_path` | string | Full path to the original broken script |
| `healed_script_path` | string | Path to the generated healed script (empty if NO_FIX) |

### 9.5 `model_info` Output Fields

| Field | Type | Description |
|---|---|---|
| `model` | string | ML model name: `"strategy_selector_v1"` |
| `confidence` | float | ML prediction confidence (0.0 – 1.0) |
| `healing_mode` | string | `"aggressive"` or `"conservative"` (only on SUCCESS) |
| `ml_confidence` | float | Same as confidence (explicit label, only on SUCCESS) |

### 9.6 Status Values

| Status | Meaning | What Happened |
|---|---|---|
| `SUCCESS` | Healed | New locator found, script patched, syntax valid |
| `NO_FIX` | Cannot heal | Confidence too low, missing DOM, unsupported error, etc. |
| `FAILED` | Error | Unexpected error during patching or validation |

---

## 10. Status Codes & Error Handling

### 10.1 HTTP Status Codes

| Code | When | Description |
|---|---|---|
| **200** | Healing completed | Even for NO_FIX — always check `healing_summary.status` |
| **405** | Wrong HTTP method | You used GET instead of POST (or vice versa) |
| **422** | Validation error | Missing required fields in the request body |
| **500** | Engine error | Unexpected internal error |

### 10.2 Validation Error Response (422)

When required fields are missing:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "failure_context"],
      "msg": "Field required",
      "input": { "metadata": { "bot_id": "BOT-TEST" } }
    },
    {
      "type": "missing",
      "loc": ["body", "dom_context"],
      "msg": "Field required",
      "input": { "metadata": { "bot_id": "BOT-TEST" } }
    }
  ]
}
```

### 10.3 Internal Error Response (500)

```json
{
  "detail": {
    "error": "HEALING_ENGINE_ERROR",
    "message": "Description of what went wrong"
  }
}
```

### 10.4 Method Not Allowed (405)

```json
{
  "detail": "Method Not Allowed"
}
```

**Cause:** You sent a GET request to a POST endpoint, or a POST to a GET endpoint.  
**Fix:** Use the correct HTTP method (see Section 4).

---

## 11. Supported Error Types & Actions

### 11.1 Supported Error Types

These are the error types the engine can heal:

| Error Type | Description |
|---|---|
| `ELEMENT_NOT_FOUND` | Element selector no longer matches any DOM element |
| `TIMEOUT_WAITING_FOR_SELECTOR` | Playwright timed out waiting for selector |
| `STRICT_MODE_VIOLATION` | Selector matched multiple elements |
| `DETACHED_FROM_DOM` | Element was removed from DOM during interaction |
| `NOT_VISIBLE` | Element exists but is not visible |
| `NOT_ENABLED` | Element exists but is disabled |

### 11.2 Supported Actions

| Action | Description |
|---|---|
| `click` | Click on an element |
| `fill` | Type text into an input/textarea |
| `wait_for_selector` | Wait for element to appear |
| `query_selector_all` | Query multiple elements |
| `locator` | Playwright locator chain |

**Unsupported actions** will return `NO_FIX` with a reason message.

---

## 12. Confidence Thresholds & Healing Modes

| ML Confidence | Mode | Behavior |
|---|---|---|
| **≥ 0.70** | Aggressive | Uses best candidate (any type) |
| **≥ 0.50, < 0.70** | Conservative | Only uses ID-based selectors (e.g., `#submit-btn`) |
| **< 0.50** | No Fix | Returns `NO_FIX` — confidence too low for safe healing |

**Why?** The conservative gate prevents incorrect healing when the ML model is uncertain. ID-based selectors are the safest because they're unique.

---

## 13. Postman Testing Guide

### 13.1 Setup

1. **Start the server:**
   ```bash
   cd ai_rpa_healing_engine
   uvicorn src.api.app:app --port 8000
   ```
2. Open Postman
3. Create a new **Collection** called "Code Healing Engine"

### 13.2 Test 1 — Health Check ✅

| Setting | Value |
|---|---|
| Method | **GET** |
| URL | `http://localhost:8000/api/v1/health` |

**Expected (200):**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "component": "code_healing_engine"
}
```

### 13.3 Test 2 — Heal Single (SUCCESS) ✅

| Setting | Value |
|---|---|
| Method | **POST** |
| URL | `http://localhost:8000/api/v1/heal` |
| Body | raw → JSON |

**Body:**
```json
{
  "metadata": {
    "bot_id": "BOT-SEARCH-01",
    "run_id": "postman-test-001",
    "report_id": "ELR-POSTMAN-001"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/search_flow.py",
    "failing_line": 13,
    "action": "fill",
    "old_locator": "textarea[name='qqq']",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30s exceeded while waiting for selector textarea[name='qqq']"
  },
  "dom_context": {
    "new_element_html": "<textarea class=\"gLFyf\" name=\"q\" aria-label=\"Search\" rows=\"1\"></textarea>",
    "page_url": "https://www.google.com",
    "page_name": "search"
  },
  "element_expectation": {
    "expected_role": "search_box",
    "expected_text": "Search"
  }
}
```

**Expected — Check these fields:**
```
healing_summary.status       → "SUCCESS"
healing_summary.new_locator  → "textarea[name=\"q\"]"
healing_summary.confidence   → 0.8
healing_summary.patcher      → "LibCST"
model_info.healing_mode      → "aggressive"
```

### 13.4 Test 3 — Heal with element_candidate ✅

| Setting | Value |
|---|---|
| Method | **POST** |
| URL | `http://localhost:8000/api/v1/heal` |
| Body | raw → JSON |

**Body:**
```json
{
  "metadata": {
    "bot_id": "BOT-SEARCH-01",
    "run_id": "postman-test-002"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/search_flow.py",
    "failing_line": 13,
    "action": "fill",
    "old_locator": "textarea[name='qqq']",
    "error_type": "ELEMENT_NOT_FOUND"
  },
  "dom_context": {
    "new_element_html": "<textarea class=\"gLFyf\" name=\"q\" aria-label=\"Search\" rows=\"1\"></textarea>",
    "page_url": "https://www.google.com"
  },
  "element_candidate": {
    "css": "textarea.gLFyf",
    "xpath": "//textarea[@name='q']",
    "full_xpath": "/html/body/div/form/textarea",
    "score": 85,
    "strategy": "attribute_match"
  }
}
```

**Expected:**
```
healing_summary.status       → "SUCCESS"
element_candidate            → echoed back in response
```

### 13.5 Test 4 — NO_FIX (empty DOM) ⚠️

| Setting | Value |
|---|---|
| Method | **POST** |
| URL | `http://localhost:8000/api/v1/heal` |
| Body | raw → JSON |

**Body:**
```json
{
  "metadata": {
    "bot_id": "BOT-NOFIX-TEST"
  },
  "failure_context": {
    "script_path": "bots/some_script.py",
    "failing_line": 10,
    "action": "click",
    "old_locator": "#old-button",
    "error_type": "ELEMENT_NOT_FOUND"
  },
  "dom_context": {
    "new_element_html": ""
  }
}
```

**Expected:**
```
healing_summary.status   → "NO_FIX"
healing_summary.validation.reason → "Missing dom_context.new_element_html; cannot regenerate locator."
```

### 13.6 Test 5 — Validation Error (missing fields) ❌

| Setting | Value |
|---|---|
| Method | **POST** |
| URL | `http://localhost:8000/api/v1/heal` |
| Body | raw → JSON |

**Body:**
```json
{
  "metadata": {
    "bot_id": "BOT-TEST"
  }
}
```

**Expected (422):**
```json
{
  "detail": [
    { "loc": ["body", "failure_context"], "msg": "Field required" },
    { "loc": ["body", "dom_context"], "msg": "Field required" }
  ]
}
```

### 13.7 Test 6 — Batch Heal 📦

| Setting | Value |
|---|---|
| Method | **POST** |
| URL | `http://localhost:8000/api/v1/heal/batch` |
| Body | raw → JSON |

**Body:**
```json
{
  "inputs": [
    {
      "metadata": { "bot_id": "BOT-SEARCH-01", "run_id": "batch-001" },
      "failure_context": {
        "script_path": "data/scripts/broken/search_flow.py",
        "failing_line": 13,
        "action": "fill",
        "old_locator": "textarea[name='qqq']",
        "error_type": "ELEMENT_NOT_FOUND"
      },
      "dom_context": {
        "new_element_html": "<textarea class=\"gLFyf\" name=\"q\" aria-label=\"Search\"></textarea>"
      }
    },
    {
      "metadata": { "bot_id": "BOT-NOFIX-01", "run_id": "batch-002" },
      "failure_context": {
        "script_path": "bots/some_script.py",
        "failing_line": 10,
        "action": "click",
        "old_locator": "#missing",
        "error_type": "ELEMENT_NOT_FOUND"
      },
      "dom_context": {
        "new_element_html": ""
      }
    }
  ]
}
```

**Expected:**
```
total   → 2
success → 1
no_fix  → 1
failed  → 0
```

### 13.8 Common Postman Mistakes

| Problem | Cause | Fix |
|---|---|---|
| `405 Method Not Allowed` | Wrong HTTP method (GET instead of POST) | Change method dropdown to **POST** |
| `422 Unprocessable Entity` | Missing required fields | Add `metadata`, `failure_context`, `dom_context` |
| `Connection refused` | Server not running | Start with `uvicorn src.api.app:app --port 8000` |
| Empty response | Body not set to raw JSON | Select Body → raw → JSON |
| No Content-Type | Header missing | Postman adds it automatically when you select JSON body |

---

## 14. Integration Code Samples

### 14.1 Python (requests)

```python
import requests

API_URL = "http://localhost:8000/api/v1/heal"

elr_input = {
    "metadata": {"bot_id": "BOT-HR-01", "run_id": "run-001"},
    "failure_context": {
        "script_path": "bots/hr_portal.py",
        "failing_line": 22,
        "action": "click",
        "old_locator": "#login-btn-old",
        "error_type": "ELEMENT_NOT_FOUND",
    },
    "dom_context": {
        "new_element_html": '<button id="login-btn" class="btn">Login</button>',
    },
}

response = requests.post(API_URL, json=elr_input)
result = response.json()

if result["healing_summary"]["status"] == "SUCCESS":
    print(f"✅ Healed! New locator: {result['healing_summary']['new_locator']}")
    print(f"   Healed script: {result['script_output']['healed_script_path']}")
    print(f"   Confidence: {result['healing_summary']['confidence']}")
elif result["healing_summary"]["status"] == "NO_FIX":
    print(f"⚠️ No fix: {result['healing_summary']['validation']['reason']}")
else:
    print(f"❌ Failed: {result['healing_summary']['validation']['reason']}")
```

### 14.2 Python (httpx — async)

```python
import httpx
import asyncio

async def heal_locator(elr_input: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/heal",
            json=elr_input,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

# Usage
result = asyncio.run(heal_locator(elr_input))
```

### 14.3 JavaScript / Node.js (fetch)

```javascript
const API_URL = 'http://localhost:8000/api/v1/heal';

const elrInput = {
  metadata: { bot_id: 'BOT-WEB-01', run_id: 'run-001' },
  failure_context: {
    script_path: 'bots/web_flow.py',
    failing_line: 15,
    action: 'click',
    old_locator: '#old-btn',
    error_type: 'ELEMENT_NOT_FOUND',
  },
  dom_context: {
    new_element_html: '<button id="new-btn" class="btn">Click</button>',
  },
};

const response = await fetch(API_URL, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(elrInput),
});

const result = await response.json();
console.log(result.healing_summary.status);      // "SUCCESS" | "NO_FIX" | "FAILED"
console.log(result.healing_summary.new_locator); // "#new-btn"
```

### 14.4 cURL

```bash
curl -X POST http://localhost:8000/api/v1/heal \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {"bot_id": "BOT-CURL-TEST"},
    "failure_context": {
      "script_path": "data/scripts/broken/search_flow.py",
      "failing_line": 13,
      "action": "fill",
      "old_locator": "textarea[name=qqq]",
      "error_type": "ELEMENT_NOT_FOUND"
    },
    "dom_context": {
      "new_element_html": "<textarea name=\"q\" class=\"gLFyf\"></textarea>"
    }
  }'
```

### 14.5 PowerShell

```powershell
$body = @{
    metadata = @{ bot_id = "BOT-PS-TEST" }
    failure_context = @{
        script_path = "data/scripts/broken/search_flow.py"
        failing_line = 13
        action = "fill"
        old_locator = "textarea[name='qqq']"
        error_type = "ELEMENT_NOT_FOUND"
    }
    dom_context = @{
        new_element_html = '<textarea name="q" class="gLFyf"></textarea>'
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/heal" -Method POST -Body $body -ContentType "application/json"
```

---

## 15. Interactive API Docs (Swagger)

Once the server is running, open these URLs in your browser:

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | **Swagger UI** — interactive API testing (try it directly in browser) |
| `http://localhost:8000/redoc` | **ReDoc** — cleaner read-only API documentation |
| `http://localhost:8000/openapi.json` | **OpenAPI schema** — raw JSON spec for code generators |

**Swagger UI** lets you:
- See all endpoints with their request/response schemas
- Click "Try it out" to test endpoints directly in the browser
- View validation rules and field descriptions

---

## 16. Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `405 Method Not Allowed` | Wrong HTTP method | Use **POST** for `/heal` and `/heal/batch`, **GET** for `/health` |
| `422 Unprocessable Entity` | Missing required fields | Ensure `metadata.bot_id`, all `failure_context` fields, and `dom_context.new_element_html` are present |
| `500 Internal Server Error` | Engine crash | Check terminal logs; ensure `models/strategy_selector_v1.pkl` exists |
| `Connection refused` | Server not running | Start with `uvicorn src.api.app:app --port 8000` |
| `NO_FIX: "Original script not found"` | Bad `script_path` | Set `RPA_ROOT` env var or use a path relative to `ai_rpa_healing_engine/` |
| `NO_FIX: "Missing new_element_html"` | Empty DOM snippet | Provide the current HTML of the target element |
| `NO_FIX: "Error type not healable"` | Unsupported error | Use one from Section 11 |
| `NO_FIX: "Action not supported"` | Unsupported action | Use: `click`, `fill`, `wait_for_selector`, `query_selector_all`, `locator` |
| `NO_FIX: "ML confidence below threshold"` | Low confidence | Provide better `new_element_html` with `id` attributes for higher accuracy |
| Port already in use | Another process on 8000 | Use `--port 8001` or kill the existing process |
| Module not found | Dependencies not installed | Run `pip install -r requirements.txt` |

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────────────────────┐
│                 Code Healing Engine API v1.0.0                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  START:   uvicorn src.api.app:app --port 8000                   │
│  DOCS:    http://localhost:8000/docs                             │
│                                                                  │
│  GET  /api/v1/health       → Health check                       │
│  POST /api/v1/heal         → Heal single input                  │
│  POST /api/v1/heal/batch   → Heal multiple inputs               │
│                                                                  │
│  REQUIRED INPUT FIELDS:                                         │
│    metadata.bot_id                                               │
│    failure_context.script_path                                   │
│    failure_context.failing_line                                  │
│    failure_context.action                                        │
│    failure_context.old_locator                                   │
│    failure_context.error_type                                    │
│    dom_context.new_element_html                                  │
│                                                                  │
│  CHECK RESPONSE:                                                │
│    healing_summary.status  →  "SUCCESS" | "NO_FIX" | "FAILED"  │
│    healing_summary.new_locator  →  the healed selector          │
│                                                                  │
│  CONFIDENCE:                                                    │
│    >= 0.70  →  Aggressive (any candidate)                       │
│    >= 0.50  →  Conservative (ID-only)                           │
│    <  0.50  →  NO_FIX                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

*Document generated for OmniiFix Research Project — SLIIT 2026*
