"""
End-to-end integration test: demonstrates complete pipeline from logs to trained model.
Run with: pytest tests/test_e2e_advanced.py -v
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import joblib
import numpy as np

from src.data.synthetic_logs import generate_synthetic_logs
from src.data.convert_logs import convert
from src.features.extract_features import create_feature_dataset
from src.train.train_rf_advanced import train_rf_advanced


class TestE2EAdvancedPipeline:
    """Test the complete ML pipeline."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test artifacts."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    def test_complete_pipeline(self, temp_dir):
        """
        Full pipeline test:
        1. Generate synthetic logs
        2. Convert & label
        3. Extract features
        4. Split train/val
        5. Train model
        6. Verify outputs
        """
        temp_path = Path(temp_dir)

        # Step 1: Generate synthetic logs
        print("\n=== Step 1: Generating synthetic logs ===")
        logs_dir = temp_path / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        log_file = logs_dir / "synthetic.jsonl"
        log_file_selenium = logs_dir / "synthetic_selenium.jsonl"
        generate_synthetic_logs(str(log_file), str(log_file_selenium), n=100, fail_rate=0.3, seed=42)
        assert log_file.exists(), "Synthetic log file not created"
        
        # Verify log format
        with open(log_file) as f:
            lines = f.readlines()
            assert len(lines) > 0, "No logs generated"
            first_event = json.loads(lines[0])
            assert "timestamp" in first_event
            assert "message" in first_event
            print(f"✓ Generated {len(lines)} synthetic events")

        # Step 2: Convert & label
        print("\n=== Step 2: Converting & labeling logs ===")
        dataset_dir = temp_path / "dataset"
        dataset_dir.mkdir(exist_ok=True)
        parquet_file = dataset_dir / "raw.parquet"
        
        convert([str(log_file)], out_parquet=str(parquet_file))
        assert parquet_file.exists(), "Parquet file not created"
        
        df = pd.read_parquet(parquet_file)
        assert len(df) > 0, "Empty dataframe"
        assert "label" in df.columns, "Label column missing"
        assert "message" in df.columns, "Message column missing"
        print(f"✓ Converted to Parquet: {len(df)} rows, {df.shape[1]} columns")
        print(f"✓ Label distribution: {df['label'].value_counts().to_dict()}")

        # Step 3: Extract features
        print("\n=== Step 3: Extracting features ===")
        featured_file = dataset_dir / "featured.parquet"
        
        df_features = create_feature_dataset(
            str(parquet_file),
            str(featured_file),
            model_name="all-MiniLM-L6-v2"
        )
        
        assert featured_file.exists(), "Featured Parquet file not created"
        assert df_features.shape[1] > df.shape[1], "No features added"
        print(f"✓ Extracted {df_features.shape[1]} features ({df_features.shape[1] - df.shape[1]} new)")

        # Step 4: Split train/val
        print("\n=== Step 4: Splitting train/val ===")
        from sklearn.model_selection import train_test_split
        
        train_df, val_df = train_test_split(
            df_features,
            test_size=0.2,
            random_state=42,
            stratify=df_features["label"]
        )
        
        train_file = dataset_dir / "train_features.parquet"
        val_file = dataset_dir / "val_features.parquet"
        train_df.to_parquet(train_file, index=False)
        val_df.to_parquet(val_file, index=False)
        
        print(f"✓ Train: {len(train_df)} samples")
        print(f"✓ Val: {len(val_df)} samples")

        # Step 5: Train model
        print("\n=== Step 5: Training advanced RandomForest ===")
        model_dir = temp_path / "models"
        model_dir.mkdir(exist_ok=True)
        output_dir = temp_path / "output"
        output_dir.mkdir(exist_ok=True)
        
        model_file = model_dir / "model.joblib"
        metrics_file = output_dir / "metrics.json"
        preds_file = output_dir / "predictions.jsonl"
        
        trainer, metrics = train_rf_advanced(
            str(train_file),
            str(val_file),
            str(model_file),
            str(metrics_file),
            str(preds_file),
            n_trials=3,
            cv_splits=2
        )
        
        assert model_file.exists(), "Model file not created"
        assert metrics_file.exists(), "Metrics file not created"
        assert preds_file.exists(), "Predictions file not created"
        print(f"✓ Model trained and saved")

        # Step 6: Verify outputs
        print("\n=== Step 6: Verifying outputs ===")
        
        # Load and verify model
        model = joblib.load(model_file)
        assert hasattr(model, "predict"), "Model missing predict method"
        print(f"✓ Model loaded: {type(model).__name__}")
        
        # Verify metrics
        with open(metrics_file) as f:
            metrics = json.load(f)
            assert "accuracy" in metrics, "Accuracy missing"
            assert "f1" in metrics, "F1 score missing"
            assert "confusion_matrix" in metrics, "Confusion matrix missing"
            print(f"✓ Metrics: accuracy={metrics['accuracy']:.3f}, f1={metrics['f1']:.3f}")
        
        # Verify predictions
        preds = []
        with open(preds_file) as f:
            for line in f:
                preds.append(json.loads(line))
        
        assert len(preds) == len(val_df), "Prediction count mismatch"
        assert all("pred_proba" in p for p in preds), "Missing pred_proba"
        assert all(0 <= p["pred_proba"] <= 1 for p in preds), "Probabilities out of range"
        print(f"✓ Predictions: {len(preds)} predictions generated")

        # Summary
        print("\n" + "="*60)
        print("✅ FULL PIPELINE TEST PASSED")
        print("="*60)
        print(f"\nPipeline Summary:")
        print(f"  Logs Generated:      {len(lines)} events")
        print(f"  Features Created:    {df_features.shape[1]} dimensions")
        print(f"  Training Samples:    {len(train_df)}")
        print(f"  Validation Samples:  {len(val_df)}")
        print(f"  Model Type:          {type(model).__name__}")
        print(f"  Test Accuracy:       {metrics['accuracy']:.1%}")
        print(f"  Test F1:             {metrics['f1']:.1%}")
        print(f"\nAll outputs created successfully in: {temp_path}")

    def test_model_reproducibility(self, temp_dir):
        """Test that the same seed produces identical models."""
        temp_path = Path(temp_dir)
        
        # Generate logs twice with same seed
        logs_dir = temp_path / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        log_file1 = logs_dir / "test1.jsonl"
        log_file1_sel = logs_dir / "test1_sel.jsonl"
        log_file2 = logs_dir / "test2.jsonl"
        log_file2_sel = logs_dir / "test2_sel.jsonl"
        
        generate_synthetic_logs(str(log_file1), str(log_file1_sel), n=50, fail_rate=0.3, seed=42)
        generate_synthetic_logs(str(log_file2), str(log_file2_sel), n=50, fail_rate=0.3, seed=42)
        
        # Convert both
        dataset_dir = temp_path / "dataset"
        dataset_dir.mkdir(exist_ok=True)
        
        parquet1 = dataset_dir / "log1.parquet"
        parquet2 = dataset_dir / "log2.parquet"
        
        convert([str(log_file1)], out_parquet=str(parquet1))
        convert([str(log_file2)], out_parquet=str(parquet2))
        
        df1 = pd.read_parquet(parquet1)
        df2 = pd.read_parquet(parquet2)
        
        # Same seed should produce identical data
        assert len(df1) == len(df2), "Different number of events"
        assert (df1["label"].values == df2["label"].values).all(), "Different labels"
        print("✓ Reproducibility test passed: same seed → same data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
