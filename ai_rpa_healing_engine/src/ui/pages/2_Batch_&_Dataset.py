import sys
from pathlib import Path

# --- Fix import path for Streamlit ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

DATASET_PATH = Path("data/ml/healing_dataset.csv")


def load_dataset() -> pd.DataFrame | None:
    if not DATASET_PATH.exists():
        return None
    try:
        return pd.read_csv(DATASET_PATH)
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        return None


def main():
    st.set_page_config(page_title="Batch & Dataset", page_icon="📊", layout="wide")

    st.title("📊 Batch Execution & Dataset Overview")
    st.caption(
        "This page shows batch-generated healing data used for ML training "
        "(standalone, no integration required for PP1)."
    )

    df = load_dataset()
    if df is None or df.empty:
        st.warning("Dataset not found or empty. Run batch healing first.")
        return

    # ---------- TOP METRICS ----------
    total_rows = len(df)
    success_rows = len(df[df["outcome"] == "SUCCESS"])
    failed_rows = len(df[df["outcome"] != "SUCCESS"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Records", total_rows)
    c2.metric("Successful Heals", success_rows)
    c3.metric("Other Outcomes", failed_rows)

    st.divider()

    # ---------- STRATEGY DISTRIBUTION ----------
    st.subheader("Strategy Distribution (SUCCESS only)")

    success_df = df[df["outcome"] == "SUCCESS"]
    strategy_counts = success_df["strategy"].value_counts().reset_index()
    strategy_counts.columns = ["strategy", "count"]

    st.bar_chart(
        strategy_counts.set_index("strategy"),
        use_container_width=True
    )

    st.caption(
        "Each record represents one autonomous healing decision logged "
        "during batch execution."
    )

    st.divider()

    # ---------- DATASET PREVIEW ----------
    st.subheader("Latest Dataset Entries")

    show_n = st.slider("Rows to display", min_value=5, max_value=50, value=10, step=5)

    preview_cols = [
        "timestamp",
        "bot_id",
        "error_type",
        "strategy",
        "confidence",
        "outcome",
    ]

    available_cols = [c for c in preview_cols if c in df.columns]

    st.dataframe(
        df.tail(show_n)[available_cols],
        use_container_width=True
    )

    st.divider()

    # ---------- OPTIONAL BATCH INFO ----------
    with st.expander("ℹ️ About Batch Execution"):
        st.markdown(
            """
            - Batch execution is used to **generate training data** for the ML model.
            - Each batch run simulates multiple failure scenarios.
            - The healing engine runs fully **standalone**, without UI or integration.
            - Logged data is later uploaded to Kaggle for model training.
            
            **For PP1:**  
            This page demonstrates dataset availability and readiness for ML.
            """
        )

    # ---------- DOWNLOAD DATASET ----------
    st.subheader("Download Dataset")

    st.download_button(
        label="⬇️ Download healing_dataset.csv",
        data=DATASET_PATH.read_bytes(),
        file_name="healing_dataset.csv",
        mime="text/csv",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
