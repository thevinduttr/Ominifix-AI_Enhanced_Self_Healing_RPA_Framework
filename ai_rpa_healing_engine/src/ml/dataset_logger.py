import csv
from pathlib import Path
from datetime import datetime


class DatasetLogger:
    """
    Logs healing decisions into a CSV dataset for ML training.
    """

    HEADER = [
        "timestamp",
        "bot_id",
        "error_type",
        "old_locator",
        "new_locator",
        "strategy",
        "confidence",
        "outcome",
        "element_html"
    ]

    def __init__(self, dataset_path: str = "data/ml/healing_dataset.csv"):
        self.dataset_path = Path(dataset_path)
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

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
        row = [
            datetime.utcnow().isoformat(),
            bot_id,
            error_type,
            old_locator,
            new_locator,
            strategy,
            round(confidence, 4),
            outcome,
            element_html.replace("\n", " ").strip(),
        ]

        with open(self.dataset_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
