import sys
from pathlib import Path
import json


def test_end_to_end(tmp_path):
    # ensure src is importable
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    sys.path.insert(0, str(src_root))

    # import generator, converter and trainer
    from data.synthetic_logs import generate_synthetic_logs
    from data.convert_logs import convert
    from train.train_baseline import train

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    pw = str(logs_dir / "playwright_synth.jsonl")
    se = str(logs_dir / "selenium_synth.jsonl")

    # generate small deterministic logs
    generate_synthetic_logs(out_playwright=pw, out_selenium=se, n=20, fail_rate=0.3, seed=123)

    # convert
    out_train = str(tmp_path / "dataset" / "train.jsonl")
    out_val = str(tmp_path / "dataset" / "val.jsonl")
    convert([pw, se], out_train, out_val, val_frac=0.2)

    # train
    model_out = str(tmp_path / "models" / "baseline.joblib")
    preds_out = str(tmp_path / "output" / "predictions.jsonl")
    metrics_out = str(tmp_path / "output" / "metrics.json")
    train(out_train, out_val, model_out, preds_out, metrics_out)

    # assertions: outputs exist and metrics contain accuracy
    assert Path(model_out).exists()
    assert Path(preds_out).exists()
    assert Path(metrics_out).exists()
    metrics = json.loads(Path(metrics_out).read_text())
    assert "accuracy" in metrics
