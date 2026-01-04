import os
import joblib
import pandas as pd
from scipy.sparse import hstack
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Failure Classifier")


class ClassifyRequest(BaseModel):
    botId: Optional[str] = None
    error: Optional[str] = None
    dom: Optional[str] = None
    last_action: Optional[str] = None
    failure_type: Optional[str] = None
    strategy: Optional[str] = None
    priority: Optional[str] = None


# Config: paths can be overridden with env vars
MODEL_DIR = os.environ.get('MODEL_DIR', os.path.join(os.path.dirname(__file__), '..', 'models'))
MODEL_PATH = os.environ.get('MODEL_PATH', os.path.join(MODEL_DIR, 'ui_failure_model.pkl'))
TEXT_VECT_PATH = os.environ.get('TEXT_VECT_PATH', os.path.join(MODEL_DIR, 'text_vectorizer.pkl'))
CAT_ENCODER_PATH = os.environ.get('CAT_ENCODER_PATH', os.path.join(MODEL_DIR, 'cat_encoder.pkl'))


def _load_model():
    try:
        clf = joblib.load(MODEL_PATH)
    except Exception as e:
        raise RuntimeError(f"Failed to load classifier from {MODEL_PATH}: {e}")
    try:
        text_vectorizer = joblib.load(TEXT_VECT_PATH)
    except Exception as e:
        raise RuntimeError(f"Failed to load text vectorizer from {TEXT_VECT_PATH}: {e}")
    try:
        cat_encoder = joblib.load(CAT_ENCODER_PATH)
    except Exception as e:
        raise RuntimeError(f"Failed to load categorical encoder from {CAT_ENCODER_PATH}: {e}")
    return clf, text_vectorizer, cat_encoder


try:
    clf, text_vectorizer, cat_encoder = _load_model()
except Exception as e:
    clf = text_vectorizer = cat_encoder = None
    _load_error = str(e)
else:
    _load_error = None


@app.get("/health")
async def health():
    return {"ready": _load_error is None, "error": _load_error}


@app.post('/classify')
async def classify(req: ClassifyRequest):
    if _load_error:
        raise HTTPException(status_code=500, detail=f"Model load error: {_load_error}")

    # Build DataFrame like training script
    df = pd.DataFrame([{
        "error": req.error or '',
        "dom": req.dom or '',
        "last_action": req.last_action or '',
        "bot": req.botId or '',
        "strategy": req.strategy or '',
        "priority": req.priority or ''
    }])
    df['text'] = df['error'].astype(str) + ' ' + df['dom'].astype(str) + ' ' + df['last_action'].astype(str)

    try:
        text_vec = text_vectorizer.transform(df['text'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text vectorizer error: {e}")

    try:
        # cat_encoder expected to transform a 2D frame/array of categorical columns
        cat_vec = cat_encoder.transform(df[['bot', 'strategy', 'priority']])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorical encoder error: {e}")

    try:
        X = hstack([text_vec, cat_vec])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature stack error: {e}")

    try:
        pred = clf.predict(X)
        label = pred[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model prediction error: {e}")

    confidence = None
    try:
        if hasattr(clf, 'predict_proba'):
            probs = clf.predict_proba(X)
            # take max prob for first row
            confidence = float(probs[0].max())
    except Exception:
        confidence = None

    return {"category": str(label), "confidence": confidence}
