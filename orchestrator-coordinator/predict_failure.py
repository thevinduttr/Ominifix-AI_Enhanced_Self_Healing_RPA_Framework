import os
import requests
import joblib
import pandas as pd
from scipy.sparse import hstack
from typing import Optional

# Try to use remote model server if configured, otherwise fall back to local joblib files if present.
MODEL_URL = os.environ.get('MODEL_URL') or os.environ.get('MODEL_SERVER_URL')

# Local model paths (optional)
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
LOCAL_MODELS_DIR = os.environ.get('MODEL_DIR', os.path.join(REPO_ROOT, 'orchestrator-monitor', '..', 'models'))
LOCAL_MODEL_PATH = os.environ.get('LOCAL_MODEL_PATH', os.path.join(LOCAL_MODELS_DIR, 'ui_failure_model.pkl'))
LOCAL_TEXT_VECT = os.environ.get('LOCAL_TEXT_VECT', os.path.join(LOCAL_MODELS_DIR, 'text_vectorizer.pkl'))
LOCAL_CAT_ENCODER = os.environ.get('LOCAL_CAT_ENCODER', os.path.join(LOCAL_MODELS_DIR, 'cat_encoder.pkl'))

_local_clf = None
_local_text_vectorizer = None
_local_cat_encoder = None

def _load_local_model():
    global _local_clf, _local_text_vectorizer, _local_cat_encoder
    if _local_clf is not None:
        return True
    try:
        if os.path.exists(LOCAL_MODEL_PATH) and os.path.exists(LOCAL_TEXT_VECT) and os.path.exists(LOCAL_CAT_ENCODER):
            _local_clf = joblib.load(LOCAL_MODEL_PATH)
            _local_text_vectorizer = joblib.load(LOCAL_TEXT_VECT)
            _local_cat_encoder = joblib.load(LOCAL_CAT_ENCODER)
            return True
    except Exception:
        _local_clf = _local_text_vectorizer = _local_cat_encoder = None
    return False


def predict_failure(error: Optional[str], dom: Optional[str], last_action: Optional[str], bot: Optional[str], priority: Optional[str], strategy: Optional[str]=None) -> str:
    """Predict failure category using remote model server if configured, else local model if available.

    Returns predicted label string or 'unknown' on failure.
    """
    payload = {
        'botId': bot,
        'error': error,
        'dom': dom,
        'last_action': last_action,
        'strategy': strategy,
        'priority': priority
    }

    # Try remote model server first
    if MODEL_URL:
        try:
            resp = requests.post(MODEL_URL, json=payload, timeout=5)
            if resp.ok:
                j = resp.json()
                # accept category, label, or prediction
                cat = j.get('category') or j.get('label') or j.get('prediction')
                if cat:
                    return str(cat)
        except Exception:
            pass

    # Fallback to local model
    if _load_local_model():
        try:
            df = pd.DataFrame([{
                'error': error or '',
                'dom': dom or '',
                'last_action': last_action or '',
                'bot': bot or '',
                'strategy': strategy or '',
                'priority': priority or ''
            }])
            df['text'] = df['error'].astype(str) + ' ' + df['dom'].astype(str) + ' ' + df['last_action'].astype(str)
            text_vec = _local_text_vectorizer.transform(df['text'])
            cat_vec = _local_cat_encoder.transform(df[['bot','strategy','priority']])
            X = hstack([text_vec, cat_vec])
            pred = _local_clf.predict(X)
            return str(pred[0])
        except Exception:
            return 'unknown'

    return 'unknown'
