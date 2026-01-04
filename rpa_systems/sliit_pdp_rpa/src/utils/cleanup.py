import shutil
from pathlib import Path

def clear_demo_outputs(logger):
    folders = [
        Path("outputs"),
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        for item in folder.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
                logger.info(f"Removed: {item}")
            except Exception as e:
                logger.warning(f"Failed to remove {item}: {e}")
