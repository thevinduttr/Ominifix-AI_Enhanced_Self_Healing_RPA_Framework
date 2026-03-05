import logging

from engine.healing_engine import HealingEngine

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    engine = HealingEngine()
    logger.info("Engine runner placeholder")
