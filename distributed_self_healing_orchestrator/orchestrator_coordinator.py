"""
Compatibility shim to import `predict_failure` from the `orchestrator-coordinator` folder
which contains a hyphen and can't be imported as a normal Python package.

Usage:
    python -c "from orchestrator_coordinator import predict_failure; print(predict_failure(...))"

This file dynamically loads the module at runtime so you can import it like a normal module.
"""
from importlib import util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
TARGET = (ROOT / 'orchestrator-coordinator' / 'predict_failure.py')

if not TARGET.exists():
    raise ImportError(f"predict_failure.py not found at expected locations: {TARGET}")

spec = util.spec_from_file_location('orchestrator_coordinator.predict_failure', str(TARGET))
mod = util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

# re-export the helper
predict_failure = getattr(mod, 'predict_failure')
