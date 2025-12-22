from pathlib import Path


class HealingValidator:
    """
    Validates healed script before sending to Predictive Testing.
    Prevents cascading failures.
    """

    @staticmethod
    def validate_script(path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {"valid": False, "reason": "Healed script not found"}

        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            return {
                "valid": False,
                "reason": f"SyntaxError: {e.msg} at line {e.lineno}"
            }

        return {"valid": True, "reason": "OK"}
