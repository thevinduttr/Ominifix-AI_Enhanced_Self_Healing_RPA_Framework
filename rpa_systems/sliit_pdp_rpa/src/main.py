import yaml
from datetime import datetime
from pathlib import Path

from src.core.logger import build_logger
from src.core.browser import launch_browser
from src.extract.pdp_scraper import goto_professional_programmes, extract_all_tabs
from src.export.excel_writer import write_excel
from src.utils.cleanup import clear_demo_outputs


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_run_output_path(settings: dict) -> str:
    """
    outputs/YYYY-MM-DD/sliit_professional_programmes-extraction--HHMMSS--.xlsx
    """
    now = datetime.now()
    date_part = now.strftime("%Y-%m-%d")
    time_part = now.strftime("%H%M%S")

    out_dir = Path(settings.get("output_dir", "outputs")) / date_part
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = settings.get("output_prefix", "sliit_professional_programmes-extraction")
    filename = f"{prefix}--{time_part}--.xlsx"

    return str(out_dir / filename)


def main():
    logger = build_logger()
    settings = load_yaml("config/settings.yml")

    # Optional: clean outputs before run (useful for video demos)
    clear_demo_outputs(logger)

    output_excel = build_run_output_path(settings)
    logger.info(f"Run output Excel will be saved to: {output_excel}")

    pw, browser, context, page = launch_browser(
        headless=settings.get("headless", False),
        slow_mo_ms=settings.get("slow_mo_ms", 0),
    )

    try:
        goto_professional_programmes(
            page=page,
            base_url=settings["base_url"],
            target_url=settings["target_url"],
            logger=logger,
            timeout_ms=settings.get("timeout_ms", 30000),
        )

        data = extract_all_tabs(page, logger, settings.get("timeout_ms", 30000))

        # Keep only required columns
        data_clean = {}
        for sheet, rows in data.items():
            data_clean[sheet] = [
                {"Program Name": r.get("Program Name", ""), "Starting Date": r.get("Starting Date", "N/A")}
                for r in rows
            ]

        write_excel(output_excel, data_clean, logger)
        logger.info("DONE ✅ Extraction completed successfully.")

    finally:
        context.close()
        browser.close()
        pw.stop()


if __name__ == "__main__":
    main()
