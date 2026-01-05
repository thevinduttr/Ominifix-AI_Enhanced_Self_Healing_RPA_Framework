import csv
from pathlib import Path
from datetime import datetime


class DatasetLogger:
    """
    Logs healing decisions into a CSV dataset for ML training.
    Includes strict label integrity checks to keep the dataset clean.
    """

    ALLOWED_STRATEGIES = {
        "LOCATOR_REGEN_LIBCST",
        "WAIT_RETRY",
        "FALLBACK_LOCATOR",
        "TEMPLATE_REPAIR",
        "NO_FIX",
    }

    HEADER = [
        "timestamp",
        "bot_id",
        "error_type",
        "old_locator",
        "new_locator",
        "strategy",
        "confidence",
        "outcome",
        "element_html",
    ]

    def __init__(self, dataset_path: str = "data/ml/healing_dataset.csv"):
        self.dataset_path = Path(dataset_path)
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file with header if it doesn't exist
        if not self.dataset_path.exists():
            with open(self.dataset_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADER)

    def log(
        self,
        bot_id: str,
        error_type: str,
        old_locator: str,
        new_locator: str,
        strategy: str,
        confidence: float,
        outcome: str,
        element_html: str,
    ):
        # ✅ Label integrity check
        if strategy not in self.ALLOWED_STRATEGIES:
            raise ValueError(
                f"Invalid strategy label: {strategy}. Allowed: {sorted(self.ALLOWED_STRATEGIES)}"
            )

        # Normalize and protect dataset integrity
        element_html_clean = (element_html or "").replace("\n", " ").strip()

        row = [
            datetime.utcnow().isoformat(),
            bot_id,
            error_type,
            old_locator,
            new_locator,
            strategy,
            round(float(confidence), 4),
            outcome,
            element_html_clean,
        ]

        with open(self.dataset_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
