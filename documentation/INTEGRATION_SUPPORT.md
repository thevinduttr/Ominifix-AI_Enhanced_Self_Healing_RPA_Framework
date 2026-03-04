# OmniiFix — Code Healing Engine: Integration Support Document

> **Component:** Code Healing Engine (Element Locator Repair)  
> **Version:** 1.0  
> **Date:** March 2026  
> **Author:** Thevindu Rathnaweera  
> **Framework:** OmniiFix — AI-Enhanced Self-Healing RPA Framework

---

## Table of Contents

1. [Component Overview](#1-component-overview)
2. [Architecture & Data Flow](#2-architecture--data-flow)
3. [Directory Structure](#3-directory-structure)
4. [Input Specification (ELR JSON)](#4-input-specification-elr-json)
5. [Output Specification](#5-output-specification)
6. [How to Run](#6-how-to-run)
7. [Environment Setup](#7-environment-setup)
8. [Integration Points](#8-integration-points)
9. [Multi-Bot Routing](#9-multi-bot-routing)
10. [Supported Error Types & Actions](#10-supported-error-types--actions)
11. [Confidence Thresholds](#11-confidence-thresholds)
12. [Complete Input/Output Samples](#12-complete-inputoutput-samples)
13. [Integration Checklist](#13-integration-checklist)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Component Overview

The **Code Healing Engine** is the self-healing component of the OmniiFix framework. When an RPA bot fails due to a broken element locator (e.g., a button ID changed on a website), this component:

1. **Receives** an ELR (Element Locator Report) JSON file describing the failure
2. **Analyzes** the error type and broken locator using an ML classifier
3. **Generates** a new locator from the updated DOM HTML
4. **Patches** the broken RPA script with the correct new locator (using LibCST)
5. **Validates** the healed script (syntax check)
6. **Outputs** a healing report JSON + the healed `.py` script file

**Key capability:** Handles multiple bots simultaneously — each bot's failures are processed and output to bot-specific directories with zero cross-contamination.

---

## 2. Architecture & Data Flow

```
┌────────────────────────┐
│  RPA Bot Fails         │  Bot detects element locator failure
│  (Any Bot System)      │  and generates an ELR input JSON
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────────┐
│  INPUT: data/inbox/elr_inputs/<BOT_ID>/<DATE>/elr_input.json  │
│  (or pass directly via --input CLI flag)                      │
└──────────┬─────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────────┐
│                   CODE HEALING ENGINE                          │
│                                                                │
│  ┌─────────────────┐   ┌──────────────────┐                   │
│  │ Healing Router   │──▶│ ML Strategy      │                   │
│  │ (error+action    │   │ Predictor        │                   │
│  │  validation)     │   │ (TF-IDF+RF)      │                   │
│  └─────────────────┘   └──────┬───────────┘                   │
│                               │                                │
│  ┌─────────────────┐   ┌─────▼────────────┐                   │
│  │ Confidence Gate  │◀──│ Locator Generator│                   │
│  │ (aggressive/     │   │ (CSS/XPath from  │                   │
│  │  conservative)   │   │  DOM HTML)       │                   │
│  └────────┬────────┘   └──────────────────┘                   │
│           │                                                    │
│  ┌────────▼────────┐   ┌──────────────────┐                   │
│  │ Script Patcher   │──▶│ Healing Validator│                   │
│  │ (LibCST AST)     │   │ (syntax check)   │                   │
│  └─────────────────┘   └──────────────────┘                   │
└──────────┬─────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────────┐
│  OUTPUT:                                                       │
│  data/outbox/healing_outputs/<BOT_ID>/<DATE>/healing_output.json│
│  data/outbox/healed_scripts/<BOT_ID>/<DATE>/healed_script.py   │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
ai_rpa_healing_engine/
│
├── data/
│   ├── inbox/                          ← PUT INPUT FILES HERE
│   │   └── elr_inputs/
│   │       └── <BOT_ID>/
│   │           └── <YYYY-MM-DD>/
│   │               └── elr_input--<YYYYMMDD>--<HHMMSS>.json
│   │
│   └── outbox/                         ← READ OUTPUT FILES HERE
│       ├── healing_outputs/
│       │   └── <BOT_ID>/
│       │       └── <YYYY-MM-DD>/
│       │           └── healing_output--<YYYYMMDD>--<HHMMSS>.json
│       ├── healed_scripts/
│       │   └── <BOT_ID>/
│       │       └── <YYYY-MM-DD>/
│       │           └── healed_script--<YYYYMMDD>--<HHMMSS>.py
│       └── run_reports/
│           └── <YYYY-MM-DD>/
│               └── run_report--<YYYYMMDD>--<HHMMSS>.json
│
├── models/
│   └── strategy_selector_v1.pkl        ← Pre-trained ML model
│
└── src/
    └── runner/
        └── heal.py                     ← MAIN ENTRY POINT
```

### Path Patterns

| Item | Path Pattern |
|---|---|
| **Input (single)** | `data/inbox/elr_inputs/<BOT_ID>/<DATE>/elr_input--<TS>.json` |
| **Input (batch)** | `data/inbox/elr_inputs/` (entire folder, recursive) |
| **Healing Output JSON** | `data/outbox/healing_outputs/<BOT_ID>/<DATE>/healing_output--<TS>.json` |
| **Healed Script** | `data/outbox/healed_scripts/<BOT_ID>/<DATE>/healed_script--<TS>.py` |
| **Batch Run Report** | `data/outbox/run_reports/<DATE>/run_report--<TS>.json` |

---

## 4. Input Specification (ELR JSON)

The input is an **ELR (Element Locator Report) JSON** file. This is the contract between any RPA bot/component and the healing engine.

### 4.1 Minimum Required Input

The bare minimum fields needed for healing to work:

```json
{
  "metadata": {
    "bot_id": "BOT-MY-SYSTEM-01",
    "run_id": "run-20260305-001"
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

### 4.2 Full Input (All Fields)

```json
{
  "metadata": {
    "schema_version": "1.0",
    "report_id": "ELR-E2E-001",
    "run_id": "e2e-test-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T14:00:01Z",
    "source_component": "element_locator_engine",
    "target_component": "code_healing_engine",
    "environment": "production"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "dom_context": {
    "page_url": "https://shop.example.com/cart",
    "page_name": "checkout",
    "new_element_html": "<button id=\"submit-order\" class=\"btn-checkout btn-primary\" type=\"submit\">Place Order</button>"
  },
  "element_expectation": {
    "expected_role": "submit_button",
    "expected_text": "Place Order"
  }
}
```

### 4.3 Field Reference

| Field | Required | Type | Description |
|---|---|---|---|
| `metadata.bot_id` | **YES** | `string` | Unique bot identifier. Used for output routing (e.g., `BOT-HR-PORTAL-01`) |
| `metadata.run_id` | **YES** | `string` | Unique run ID for traceability |
| `metadata.schema_version` | No | `string` | Schema version (currently `1.0`) |
| `metadata.report_id` | No | `string` | Report identifier from source component |
| `metadata.timestamp` | No | `string` | ISO 8601 timestamp of when the failure occurred |
| `metadata.source_component` | No | `string` | Name of the component that generated this ELR |
| `metadata.target_component` | No | `string` | Target component (always `code_healing_engine`) |
| `metadata.environment` | No | `string` | Environment: `production`, `staging`, `development` |
| `failure_context.script_path` | **YES** | `string` | Relative path to the broken RPA `.py` script |
| `failure_context.failing_line` | **YES** | `int` | Line number where the broken `page.locator()` call is |
| `failure_context.action` | **YES** | `string` | Playwright action: `click`, `fill`, `wait_for_selector`, `query_selector_all`, `locator` |
| `failure_context.old_locator` | **YES** | `string` | The broken CSS selector or XPath string |
| `failure_context.error_type` | **YES** | `string` | Error classification (see Section 10) |
| `failure_context.error_message` | No | `string` | Full error message text from Playwright |
| `dom_context.new_element_html` | **YES** | `string` | The **updated** HTML of the target element from the live page |
| `dom_context.page_url` | No | `string` | URL where the failure occurred |
| `dom_context.page_name` | No | `string` | Human-readable page name |
| `element_expectation.expected_role` | No | `string` | Semantic role (for logging only) |
| `element_expectation.expected_text` | No | `string` | Expected visible text (for logging only) |

### 4.4 How to Get `new_element_html`

This is the most critical field. The integrating component must provide the **current HTML** of the target element from the live webpage. Methods to obtain it:

```python
# Method 1: Playwright — if you know a parent container
element = page.query_selector("body")  # or a closer parent
html = element.inner_html()
# Then extract the specific element's HTML

# Method 2: Playwright — using evaluate
html = page.evaluate("""
    () => {
        const el = document.querySelector('#submit-order');
        return el ? el.outerHTML : '';
    }
""")

# Method 3: From your Element Locator Engine's DOM diff output
# The EL engine already tracks DOM changes — use its output
```

---

## 5. Output Specification

### 5.1 Healing Output JSON

Written to: `data/outbox/healing_outputs/<BOT_ID>/<DATE>/healing_output--<TS>.json`

```json
{
  "metadata": {
    "healing_id": "HEAL-4004ab74-a368-4628-bcff-c0c2094cd160",
    "report_id": "ELR-E2E-001",
    "run_id": "e2e-test-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T17:57:52.502935",
    "source_component": "code_healing_engine",
    "target_component": "code_healing_engine"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "dom_context": {
    "page_url": "https://shop.example.com/cart",
    "page_name": "checkout",
    "new_element_html": "<button id=\"submit-order\" class=\"btn-checkout btn-primary\" type=\"submit\">Place Order</button>"
  },
  "element_expectation": {
    "expected_role": "submit_button",
    "expected_text": "Place Order"
  },
  "healing_summary": {
    "status": "SUCCESS",
    "strategy_used": "CLICK_ONLY",
    "action": "click",
    "old_locator": "#submit-order-old",
    "new_locator": "#submit-order",
    "confidence": 1.0,
    "patcher": "LibCST",
    "validation": {
      "valid": true,
      "reason": "OK"
    }
  },
  "script_output": {
    "original_script_path": "C:\\...\\data\\scripts\\broken\\e2e\\bot1_ecommerce_checkout.py",
    "healed_script_path": "data\\outbox\\healed_scripts\\BOT-ECOMMERCE-01\\2026-03-05\\healed_script--20260305--175752.py"
  },
  "model_info": {
    "model": "strategy_selector_v1",
    "confidence": 0.8398,
    "healing_mode": "aggressive",
    "ml_confidence": 0.8398
  }
}
```

### 5.2 Key Output Fields for Integration

| Field | Type | Description |
|---|---|---|
| `healing_summary.status` | `string` | **`SUCCESS`** / **`NO_FIX`** / **`FAILED`** |
| `healing_summary.new_locator` | `string` | The generated replacement locator (CSS/XPath) |
| `healing_summary.old_locator` | `string` | The original broken locator (echoed back) |
| `healing_summary.strategy_used` | `string` | ML strategy used: `LOCATOR_REGEN_LIBCST`, `CLICK_ONLY`, `FALLBACK_LOCATOR`, `NO_FIX` |
| `healing_summary.confidence` | `float` | Locator generation confidence (0.0–1.0) |
| `healing_summary.validation.valid` | `bool` | Whether the healed script passes syntax check |
| `script_output.healed_script_path` | `string` | Path to the healed `.py` file (empty if NO_FIX) |
| `model_info.ml_confidence` | `float` | ML classifier confidence score |
| `model_info.healing_mode` | `string` | `aggressive` (≥0.70) or `conservative` (≥0.50) |

### 5.3 Status Values

| Status | Meaning | What to Do |
|---|---|---|
| **`SUCCESS`** | Script healed and validated | Deploy the healed script from `script_output.healed_script_path` |
| **`NO_FIX`** | Cannot heal (unsupported error, low confidence, missing data) | Flag for manual review |
| **`FAILED`** | Attempted healing but patching/validation failed | Flag for manual review |

### 5.4 Batch Run Report

When running in batch mode (`--inbox`), a summary report is generated at:
`data/outbox/run_reports/<DATE>/run_report--<TS>.json`

```json
{
  "processed": 5,
  "results": {
    "SUCCESS": 4,
    "FAILED": 0,
    "NO_FIX": 1
  }
}
```

---

## 6. How to Run

### 6.1 Single File Mode

Process one ELR input file:

```bash
cd ai_rpa_healing_engine
python -m src.runner.heal --input "data/inbox/elr_inputs/BOT-HR-PORTAL-01/2026-03-05/elr_input--20260305--140001.json"
```

**Output:** Prints `SUCCESS`, `NO_FIX`, or `FAILED` to stdout.  
**Files:** Writes healing output JSON + healed script to `data/outbox/`.

### 6.2 Batch Inbox Mode

Process ALL ELR files in the inbox folder recursively:

```bash
cd ai_rpa_healing_engine
python -m src.runner.heal --inbox "data/inbox/elr_inputs"
```

**Output:** Prints `DONE` when complete.  
**Files:** Writes individual output per bot + a batch run report to `data/outbox/run_reports/`.

### 6.3 Programmatic (Python Import)

```python
from pathlib import Path
from src.runner.heal import heal_one

# Heal a single ELR input
input_path = Path("data/inbox/elr_inputs/BOT-HR-PORTAL-01/2026-03-05/elr_input.json")
status = heal_one(input_path)  # Returns "SUCCESS" | "NO_FIX" | "FAILED"

# Find the output
from src.utils.path_manager import PathManager
pm = PathManager("BOT-HR-PORTAL-01")
output_json = pm.healing_output_path()   # data/outbox/healing_outputs/BOT-HR-PORTAL-01/...
healed_py   = pm.healed_script_path()    # data/outbox/healed_scripts/BOT-HR-PORTAL-01/...
```

### 6.4 Full Loop Mode (with Failure Analyzer)

The full loop runner includes failure context enrichment from raw Playwright error traces:

```bash
cd ai_rpa_healing_engine
python -m tools.run_full_loop --input "path/to/elr_input.json" --verbose
```

### 6.5 E2E System Test (Multi-Bot)

Run the complete system test across multiple bots:

```bash
cd ai_rpa_healing_engine
python -m tools.e2e_system_test --verbose
```

---

## 7. Environment Setup

### 7.1 Prerequisites

- Python 3.10+
- Virtual environment with required packages

### 7.2 Install Dependencies

```bash
cd ai_rpa_healing_engine
pip install -r requirements.txt
```

### 7.3 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `RPA_ROOT` | No | (cwd) | Root directory of RPA bot scripts. Used to resolve `failure_context.script_path` |
| `PYTHONIOENCODING` | No | `utf-8` | Set to `utf-8` on Windows if you see Unicode errors |

### 7.4 Script Path Resolution

The engine resolves `failure_context.script_path` in this order:

1. **Absolute path** — if the path is absolute and the file exists, use it directly
2. **Relative to CWD** — if `script_path` resolves relative to the current working directory
3. **Relative to `RPA_ROOT`** — if `script_path` resolves relative to the `RPA_ROOT` env var

**Recommendation:** Set `RPA_ROOT` to the root of the workspace/repository:

```bash
# Windows PowerShell
$env:RPA_ROOT = "C:\path\to\Ominifix-AI_Enhanced_Self_Healing_RPA_Framework"

# Linux/Mac
export RPA_ROOT="/path/to/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework"
```

### 7.5 ML Model

The pre-trained model must exist at: `models/strategy_selector_v1.pkl`

To retrain if needed:
```bash
python -m src.ml.train_strategy_model
```

---

## 8. Integration Points

### 8.1 How Other Components Send Input

**Step 1:** Generate an ELR JSON file when your bot detects a locator failure.

**Step 2:** Place it in the inbox directory:

```
data/inbox/elr_inputs/<YOUR_BOT_ID>/<YYYY-MM-DD>/elr_input--<YYYYMMDD>--<HHMMSS>.json
```

**Step 3:** Trigger healing by calling:
```bash
python -m src.runner.heal --input "data/inbox/elr_inputs/<YOUR_BOT_ID>/<DATE>/<filename>.json"
```

Or for batch mode (all pending inputs):
```bash
python -m src.runner.heal --inbox "data/inbox/elr_inputs"
```

**Step 4:** Read the output from:
```
data/outbox/healing_outputs/<YOUR_BOT_ID>/<DATE>/healing_output--<TS>.json
```

### 8.2 Upstream Integration (Element Locator Engine → Code Healing Engine)

The Element Locator Engine detects DOM changes and generates the ELR input. It must provide:

```
EL Engine Output  →  ELR JSON  →  Code Healing Engine Input
─────────────────────────────────────────────────────────────
error_type        →  failure_context.error_type
broken_selector   →  failure_context.old_locator
failing_line      →  failure_context.failing_line
playwright_action →  failure_context.action
script_file       →  failure_context.script_path
new_element_html  →  dom_context.new_element_html
bot_identifier    →  metadata.bot_id
```

### 8.3 Downstream Integration (Code Healing Engine → Predictive Testing Engine)

After healing, the output JSON contains everything the testing engine needs:

```
Code Healing Engine Output  →  Testing Engine Input
────────────────────────────────────────────────────
healing_summary.status      →  was healing successful?
healing_summary.new_locator →  what selector was applied?
script_output.healed_script_path → where is the healed .py?
model_info.ml_confidence    →  how confident was the fix?
healing_summary.validation  →  did it pass syntax check?
```

### 8.4 Integration Flow Diagram

```
┌────────────────────┐     ELR JSON      ┌──────────────────────┐    Healing Output    ┌──────────────────────┐
│  Element Locator   │ ───────────────▶  │  Code Healing        │ ─────────────────▶  │  Predictive Testing  │
│  Engine            │                    │  Engine              │                      │  Engine              │
│                    │                    │                      │                      │                      │
│  - Detect DOM diff │                    │  - ML prediction     │                      │  - Verify healed     │
│  - Identify broken │                    │  - Generate locator  │                      │    script works      │
│    selectors       │                    │  - Patch script      │                      │  - Report results    │
│  - Capture new HTML│                    │  - Validate syntax   │                      │                      │
└────────────────────┘                    └──────────────────────┘                      └──────────────────────┘
```

---

## 9. Multi-Bot Routing

The system handles multiple bots simultaneously. Every input/output is routed by `bot_id`:

```
Bot A fails  →  ELR with bot_id="BOT-A"  →  output: data/outbox/.../BOT-A/...
Bot B fails  →  ELR with bot_id="BOT-B"  →  output: data/outbox/.../BOT-B/...
Bot C fails  →  ELR with bot_id="BOT-C"  →  output: data/outbox/.../BOT-C/...
```

### How it works:

1. `metadata.bot_id` in the ELR input determines the output directory
2. `PathManager(bot_id)` creates bot-specific output paths
3. Each bot gets its own subdirectory — **zero cross-contamination**
4. In batch mode (`--inbox`), the engine processes ALL JSON files and routes each by its `bot_id`

### Verified with E2E test (5 bots):

| Bot ID | Input | Output Location |
|---|---|---|
| `BOT-ECOMMERCE-01` | `data/e2e_test/inputs/BOT-ECOMMERCE-01/...` | `data/outbox/.../BOT-ECOMMERCE-01/...` |
| `BOT-HR-PORTAL-01` | `data/e2e_test/inputs/BOT-HR-PORTAL-01/...` | `data/outbox/.../BOT-HR-PORTAL-01/...` |
| `BOT-SLIIT-PDP-01` | `data/e2e_test/inputs/BOT-SLIIT-PDP-01/...` | `data/outbox/.../BOT-SLIIT-PDP-01/...` |
| `BOT-INVENTORY-01` | `data/e2e_test/inputs/BOT-INVENTORY-01/...` | `data/outbox/.../BOT-INVENTORY-01/...` |
| `BOT-REPORT-01` | `data/e2e_test/inputs/BOT-REPORT-01/...` | `data/outbox/.../BOT-REPORT-01/...` |

---

## 10. Supported Error Types & Actions

### Supported Error Types (healable)

| Error Type | Description |
|---|---|
| `ELEMENT_NOT_FOUND` | Selector does not match any DOM element |
| `TIMEOUT_WAITING_FOR_SELECTOR` | Selector timed out before element appeared |
| `STRICT_MODE_VIOLATION` | Selector matched multiple elements |
| `DETACHED_FROM_DOM` | Element was found but later detached |
| `NOT_VISIBLE` | Element exists in DOM but not visible |
| `NOT_ENABLED` | Element exists but is disabled |

### Supported Playwright Actions

| Action | Description |
|---|---|
| `click` | `page.click(selector)` |
| `fill` | `page.fill(selector, value)` |
| `wait_for_selector` | `page.wait_for_selector(selector)` |
| `query_selector_all` | `page.query_selector_all(selector)` |
| `locator` | `page.locator(selector)` |

### What Happens with Unsupported Errors/Actions

If the error type is not in the supported list, or the action is not supported, the engine returns `NO_FIX` with a clear reason:

```json
{
  "healing_summary": {
    "status": "NO_FIX",
    "validation": {
      "valid": true,
      "reason": "Error type 'NETWORK_ERROR' not healable by locator patching."
    }
  }
}
```

---

## 11. Confidence Thresholds

The ML classifier produces a confidence score that determines healing behavior:

| Confidence | Mode | Behavior |
|---|---|---|
| **≥ 0.70** | `aggressive` | Uses the best locator candidate (any type) |
| **≥ 0.50** | `conservative` | Only uses ID-based locators (`#element-id`) for safety |
| **< 0.50** | `no_fix` | Rejects healing — confidence too low |

This is reflected in `model_info.healing_mode` in the output.

---

## 12. Complete Input/Output Samples

### 12.1 Sample Scenario: Button ID Changed on Website

**The RPA bot had:** `page.click("#submit-order-old")`  
**Website changed the button to:** `<button id="submit-order" class="btn-primary">Place Order</button>`

#### INPUT (ELR JSON)

```json
{
  "metadata": {
    "schema_version": "1.0",
    "report_id": "ELR-E2E-001",
    "run_id": "e2e-test-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T14:00:01Z",
    "source_component": "element_locator_engine",
    "target_component": "code_healing_engine",
    "environment": "production"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "dom_context": {
    "page_url": "https://shop.example.com/cart",
    "page_name": "checkout",
    "new_element_html": "<button id=\"submit-order\" class=\"btn-checkout btn-primary\" type=\"submit\">Place Order</button>"
  },
  "element_expectation": {
    "expected_role": "submit_button",
    "expected_text": "Place Order"
  }
}
```

#### OUTPUT (Healing Report JSON)

```json
{
  "metadata": {
    "healing_id": "HEAL-4004ab74-a368-4628-bcff-c0c2094cd160",
    "report_id": "ELR-E2E-001",
    "run_id": "e2e-test-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T17:57:52.502935",
    "source_component": "code_healing_engine",
    "target_component": "code_healing_engine"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "dom_context": {
    "page_url": "https://shop.example.com/cart",
    "page_name": "checkout",
    "new_element_html": "<button id=\"submit-order\" class=\"btn-checkout btn-primary\" type=\"submit\">Place Order</button>"
  },
  "element_expectation": {
    "expected_role": "submit_button",
    "expected_text": "Place Order"
  },
  "healing_summary": {
    "status": "SUCCESS",
    "strategy_used": "CLICK_ONLY",
    "action": "click",
    "old_locator": "#submit-order-old",
    "new_locator": "#submit-order",
    "confidence": 1.0,
    "patcher": "LibCST",
    "validation": {
      "valid": true,
      "reason": "OK"
    }
  },
  "script_output": {
    "original_script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "healed_script_path": "data/outbox/healed_scripts/BOT-ECOMMERCE-01/2026-03-05/healed_script--20260305--175752.py"
  },
  "model_info": {
    "model": "strategy_selector_v1",
    "confidence": 0.8398,
    "healing_mode": "aggressive",
    "ml_confidence": 0.8398
  }
}
```

#### Script Diff (Broken → Healed)

```diff
--- broken/bot1_ecommerce_checkout.py
+++ healed/healed_script--20260305--175752.py
@@ -12,7 +12,7 @@
         page.fill("#address-line1", "123 Main St")

         # BROKEN: submit button ID changed on the website
-        page.click("#submit-order-old")
+        page.click("#submit-order")

         page.wait_for_timeout(3000)
         browser.close()
```

### 12.2 Sample Scenario: NO_FIX (Missing DOM Context)

When the system cannot heal, it returns a clear reason:

#### INPUT

```json
{
  "metadata": {
    "bot_id": "BOT-BROKEN-01",
    "run_id": "run-fail-001"
  },
  "failure_context": {
    "script_path": "some/script.py",
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

#### OUTPUT

```json
{
  "healing_summary": {
    "status": "NO_FIX",
    "strategy_used": "NO_FIX",
    "validation": {
      "valid": true,
      "reason": "Missing dom_context.new_element_html; cannot regenerate locator."
    }
  }
}
```

---

## 13. Integration Checklist

Use this checklist when integrating your component with the Code Healing Engine:

### For the **upstream component** (sending inputs):

- [ ] Generate valid ELR JSON with all **required** fields (see Section 4.3)
- [ ] Use a unique `bot_id` for your bot (e.g., `BOT-MYAPP-01`)
- [ ] Provide the correct `script_path` (relative to workspace or `RPA_ROOT`)
- [ ] Provide the correct `failing_line` number (1-indexed)
- [ ] Provide the correct `action` (`click`, `fill`, etc.)
- [ ] Provide the exact `old_locator` string from the broken script
- [ ] Provide the `new_element_html` from the live page's current DOM
- [ ] Use a supported `error_type` (see Section 10)
- [ ] Place the file in the inbox or pass via `--input` CLI

### For the **downstream component** (reading outputs):

- [ ] Read healing output JSON from `data/outbox/healing_outputs/<BOT_ID>/<DATE>/`
- [ ] Check `healing_summary.status` — only `SUCCESS` means the script was patched
- [ ] If `SUCCESS`, find the healed script at `script_output.healed_script_path`
- [ ] Check `healing_summary.validation.valid` to confirm syntax correctness
- [ ] Use `healing_summary.new_locator` to know what selector replaced the old one
- [ ] Handle `NO_FIX` and `FAILED` gracefully (flag for manual intervention)

### General setup:

- [ ] Python 3.10+ with virtual environment
- [ ] `pip install -r requirements.txt` in `ai_rpa_healing_engine/`
- [ ] ML model exists at `models/strategy_selector_v1.pkl`
- [ ] Set `RPA_ROOT` env var if scripts are outside the `ai_rpa_healing_engine/` directory
- [ ] Working directory must be `ai_rpa_healing_engine/` when running

---

## 14. Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `NO_FIX`: "Original script not found" | `script_path` doesn't resolve | Set `RPA_ROOT` env var to workspace root |
| `NO_FIX`: "Missing dom_context.new_element_html" | Empty `new_element_html` | Provide the current DOM HTML of the element |
| `NO_FIX`: "Error type not healable" | Unsupported `error_type` | Use a supported type from Section 10 |
| `NO_FIX`: "Action not supported" | Unsupported `action` | Use: `click`, `fill`, `wait_for_selector`, `query_selector_all`, `locator` |
| `NO_FIX`: "ML confidence below threshold" | Low confidence score | Provide better `new_element_html` with ID attributes |
| `FAILED`: "Patcher failed" | Locator not found at `failing_line` | Verify `failing_line` and `old_locator` exactly match the script |
| Unicode errors on Windows | Console encoding | Set `$env:PYTHONIOENCODING = "utf-8"` |
| Model not found | Missing `.pkl` file | Run `python -m src.ml.train_strategy_model` |
| Output in wrong bot folder | Wrong `bot_id` | Each ELR must have the correct `metadata.bot_id` |

---

## Quick Start Example

```bash
# 1. Navigate to the engine
cd ai_rpa_healing_engine

# 2. Activate virtual environment
C:\v\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Set RPA_ROOT (if scripts are outside this folder)
$env:RPA_ROOT = "C:\path\to\Ominifix-AI_Enhanced_Self_Healing_RPA_Framework"

# 4. Run healing on a single input
python -m src.runner.heal --input "data/e2e_test/inputs/BOT-ECOMMERCE-01/elr_input_checkout_fail.json"

# 5. Check output
cat data/outbox/healing_outputs/BOT-ECOMMERCE-01/2026-03-05/*.json

# 6. Or run batch mode for all pending inputs
python -m src.runner.heal --inbox "data/inbox/elr_inputs"
```

---

*This document is part of the OmniiFix AI-Enhanced Self-Healing RPA Framework — SLIIT Research Project 2026.*
