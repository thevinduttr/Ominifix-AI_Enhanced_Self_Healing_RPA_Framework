from pathlib import Path
from datetime import datetime


class PathManager:
    def __init__(self, bot_id: str):
        self.bot_id = bot_id
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.ts = datetime.now().strftime("%Y%m%d--%H%M%S")

    # ---------- INPUT ----------
    @staticmethod
    def inbox_root():
        return Path("data/inbox/elr_inputs")

    # ---------- OUTPUT ----------
    def healed_script_path(self) -> Path:
        p = Path("data/outbox/healed_scripts") / self.bot_id / self.date
        p.mkdir(parents=True, exist_ok=True)
        return p / f"healed_script--{self.ts}.py"

    def healing_output_path(self) -> Path:
        p = Path("data/outbox/healing_outputs") / self.bot_id / self.date
        p.mkdir(parents=True, exist_ok=True)
        return p / f"healing_output--{self.ts}.json"

    @staticmethod
    def run_report_path() -> Path:
        date = datetime.now().strftime("%Y-%m-%d")
        ts = datetime.now().strftime("%Y%m%d--%H%M%S")
        p = Path("data/outbox/run_reports") / date
        p.mkdir(parents=True, exist_ok=True)
        return p / f"run_report--{ts}.json"
