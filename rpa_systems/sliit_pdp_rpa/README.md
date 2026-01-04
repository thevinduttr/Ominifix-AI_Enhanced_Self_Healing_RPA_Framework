# SLIIT Professional Programmes – RPA Extractor (Playwright → Excel)

This project is a **professional RPA extractor** that navigates the SLIIT website, opens **Professional Programmes**, iterates through the tabs (Online / Regular / Workshops & Trainings / Upcoming), extracts **Program Name** + **Starting Date**, and exports results into **one Excel file** with **one sheet per tab**.

---

## ✅ What it does (Process)

1. Navigate to: `https://www.sliit.lk/`
2. Open: **Professional Programmes** (direct URL navigation for stability)
3. Click each tab:
   - Online Programs
   - Regular Programs
   - Workshops & Trainings
   - Upcoming Programs
4. Extract from each tab section:
   - **Program Name**
   - **Starting Date** (normalized e.g., `December 2025`, `January 2026`, `Closed`, `N/A`)
5. Export to Excel (per run):
   - `outputs/YYYY-MM-DD/sliit_professional_programmes-extraction--HHMMSS--.xlsx`

---

## 📁 Project Structure

sliit_pdp_rpa/
  config/
    settings.yml
    locators.yml
  src/
    main.py
    core/
      browser.py
      logger.py
      waits.py
    extract/
      pdp_scraper.py
      parser.py
    export/
      excel_writer.py
    utils/
      cleanup.py
  outputs/
    sliit_professional_programmes.xlsx
  logs/
    run_YYYYMMDD_HHMMSS.log
  requirements.txt


---

## 🧰 Requirements

- **Python 3.10+** recommended
- Windows / macOS / Linux supported
- Internet connection required

---

## ⚙️ Setup Guide (Step-by-step)

### 1) Clone / Copy the project
Place the folder anywhere on your machine.

### 2) Create and activate a virtual environment

**Windows (PowerShell / CMD)**
```bash
python -m venv venv
venv\Scripts\activate

## macOS / Linux

python -m venv venv
source venv/bin/activate

3) Install dependencies
pip install -r requirements.txt

4) Install Playwright browsers (required)
python -m playwright install

▶️ How to Run

Run from the project root (folder that contains src/).

Recommended (professional way)
python -m src.main

📄 Output

Each execution creates a new Excel file:

outputs/
  2026-01-04/
    sliit_professional_programmes-extraction--071233--.xlsx