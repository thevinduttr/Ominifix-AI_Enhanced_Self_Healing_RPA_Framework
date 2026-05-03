from pathlib import Path

from src.utils.script_path_resolver import resolve_script_path


def test_resolves_dummy_bot_container_app_path(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("RPA_ROOT", str(repo_root))

    resolved = resolve_script_path("/app/main.py")

    assert resolved == (repo_root / "distributed_self_healing_orchestrator" / "dummy_bot" / "main.py").resolve()


def test_resolves_dummy_bot_nested_container_app_path(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("RPA_ROOT", str(repo_root))

    resolved = resolve_script_path("/app/rpa/form_filler_bot.py")

    assert resolved == (
        repo_root
        / "distributed_self_healing_orchestrator"
        / "dummy_bot"
        / "rpa"
        / "form_filler_bot.py"
    ).resolve()
