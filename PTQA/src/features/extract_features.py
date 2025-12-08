"""
Feature extraction module for RPA failure prediction.
Converts raw events into rich feature vectors suitable for ML training.
Features include: text embeddings, selector volatility, timing aggregations, error patterns.
"""
import json
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

import pandas as pd
from sentence_transformers import SentenceTransformer


class FeatureExtractor:
    """Extract features from RPA logs for ML."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with a pre-trained sentence embedding model.
        Args:
            model_name: HuggingFace model ID for embeddings (default: small, fast model)
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def extract_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features from a DataFrame of events.
        Adds columns: text_embedding, event_duration, selector_entropy, etc.
        Args:
            df: DataFrame with columns: timestamp, session, type, selector, message, status, ...
        Returns:
            DataFrame with added feature columns.
        """
        df = df.copy()
        # normalize session values so aggregation columns always exist
        if "session" not in df.columns:
            df["session"] = "default_session"
        df["session"] = df["session"].fillna("default_session")

        # 1. Text embeddings: embed the message field
        messages = df["message"].fillna("").values
        embeddings = self.model.encode(messages, show_progress_bar=False)
        emb_cols = [f"text_emb_{i}" for i in range(self.embedding_dim)]
        df = pd.concat([df, pd.DataFrame(embeddings, columns=emb_cols, index=df.index)], axis=1)

        # 2. Message length and word count
        df["msg_len"] = df["message"].fillna("").apply(len)
        df["msg_words"] = df["message"].fillna("").apply(lambda x: len(x.split()))

        # 3. Event type encoding (one-hot)
        event_types = pd.get_dummies(df["type"], prefix="evt_type")
        df = pd.concat([df, event_types], axis=1)

        # 4. Status encoding
        status_types = pd.get_dummies(df["status"], prefix="evt_status")
        df = pd.concat([df, status_types], axis=1)

        # 5. Selector features: presence, length, volatility
        df["has_selector"] = df["selector"].notna().astype(int)
        df["selector_len"] = df["selector"].fillna("").apply(len)

        # 6. Error indicators from message text
        df["has_error_keyword"] = df["message"].fillna("").apply(
            lambda x: int(bool(re.search(r"error|fail|timeout|exception|crash", x.lower())))
        )

        # 7. Aggregate features by session
        session_stats = self._compute_session_stats(df)
        df = df.merge(session_stats, on="session", how="left")

        return df

    def _compute_session_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-session aggregate statistics.
        Returns a DataFrame with one row per unique session.
        """
        session_stats: List[Dict[str, Any]] = []

        for session_id, group in df.groupby("session"):
            stats = {
                "session": session_id,
                "session_event_count": len(group),
                "session_error_count": (group["status"] == "error").sum(),
                "session_error_rate": (group["status"] == "error").sum() / len(group) if len(group) else 0.0,
                "session_avg_msg_len": group["msg_len"].mean(),
                "session_unique_selectors": group["selector"].nunique(),
                "session_avg_time_between_events": self._compute_time_gaps(group),
            }
            session_stats.append(stats)

        if not session_stats:
            return pd.DataFrame(
                columns=
                [
                    "session",
                    "session_event_count",
                    "session_error_count",
                    "session_error_rate",
                    "session_avg_msg_len",
                    "session_unique_selectors",
                    "session_avg_time_between_events",
                ]
            )

        return pd.DataFrame(session_stats)

    def _compute_time_gaps(self, group: pd.DataFrame) -> float:
        """Compute average time (in seconds) between events in a session."""
        if len(group) < 2:
            return 0.0
        try:
            times = pd.to_datetime(group["timestamp"], errors="coerce")
            if times.isna().all():
                return 0.0
            times = times.dropna().sort_values()
            gaps = times.diff().dt.total_seconds()
            return gaps[gaps > 0].mean() if len(gaps[gaps > 0]) > 0 else 0.0
        except Exception:
            return 0.0

    def extract_from_jsonl(self, jsonl_path: str) -> pd.DataFrame:
        """
        Load JSONL file and extract features.
        Args:
            jsonl_path: Path to JSONL file
        Returns:
            DataFrame with extracted features
        """
        events = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        df = pd.DataFrame(events)
        return self.extract_from_dataframe(df)


def create_feature_dataset(
    input_parquet: str,
    output_parquet: str,
    model_name: str = "all-MiniLM-L6-v2"
):
    """
    Load raw Parquet, extract features, save enhanced Parquet.
    Args:
        input_parquet: Path to raw events Parquet
        output_parquet: Path to save feature-enriched Parquet
        model_name: Sentence embedding model to use
    """
    print(f"Loading {input_parquet}...")
    df = pd.read_parquet(input_parquet)
    print(f"Loaded {len(df)} events. Extracting features...")

    extractor = FeatureExtractor(model_name=model_name)
    df_features = extractor.extract_from_dataframe(df)

    print(f"Extracted {df_features.shape[1]} features. Saving to {output_parquet}...")
    df_features.to_parquet(output_parquet, index=False)
    print(f"✓ Saved {len(df_features)} rows with {df_features.shape[1]} features")

    return df_features


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract features from RPA event logs")
    parser.add_argument("--input", type=str, required=True, help="Input Parquet file with raw events")
    parser.add_argument("--output", type=str, required=True, help="Output Parquet file with extracted features")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="Sentence embedding model")

    args = parser.parse_args()
    create_feature_dataset(args.input, args.output, args.model)
