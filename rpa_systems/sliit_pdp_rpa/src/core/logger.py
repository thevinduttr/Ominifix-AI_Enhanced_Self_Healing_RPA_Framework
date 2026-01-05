import logging
from pathlib import Path
from datetime import datetime

def build_logger() -> logging.Logger:
    Path("logs").mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path("logs") / f"run_{ts}.log"

    logger = logging.getLogger("sliit_pdp_rpa")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    logger.info(f"Logger initialized: {log_path}")
    return logger
