import os
from pathlib import Path
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from scipy.sparse import csr_matrix, hstack


def main():
    repo_root = Path(__file__).resolve().parent
    models_dir = (repo_root / '..' / 'models').resolve()
    models_dir.mkdir(parents=True, exist_ok=True)

    # Small synthetic dataset for demo purposes
    data = [
        {
            'error': 'APIFailure: 500 on /v1/data element username',
            'dom': "<div id='username'><input/></div>",
            'last_action': 'type(username)',
            'bot': 'ui-bot-77-23',
            'strategy': 'RunSelectorLocator',
            'priority': 'High',
            'label': 'RunSelectorLocator'
        },
        {
            'error': 'ElementNotFound: Could not find submit button',
            'dom': "<button id='submit'>Submit</button>",
            'last_action': 'click(submit)',
            'bot': 'ui-bot-3-1',
            'strategy': 'ElementNotFound',
            'priority': 'Medium',
            'label': 'ElementNotFound'
        },
        {
            'error': 'TimeoutError: waiting for element',
            'dom': "<div class='loader'></div>",
            'last_action': 'wait_for(element)',
            'bot': 'ui-bot-12-9',
            'strategy': 'Timeout',
            'priority': 'Low',
            'label': 'Timeout'
        },
        {
            'error': 'APIFailure: 502 Bad Gateway while fetching profile',
            'dom': "<div id='profile'></div>",
            'last_action': 'open(profile)',
            'bot': 'ui-bot-77-23',
            'strategy': 'APIFailure',
            'priority': 'High',
            'label': 'APIFailure'
        },
        {
            'error': 'ElementNotFound: username field not present',
            'dom': "<div class='login'></div>",
            'last_action': 'type(username)',
            'bot': 'ui-bot-3-1',
            'strategy': 'ElementNotFound',
            'priority': 'High',
            'label': 'ElementNotFound'
        },
        {
            'error': 'APIFailure: 500',
            'dom': "<div id='data'></div>",
            'last_action': 'fetch(data)',
            'bot': 'ui-bot-77-23',
            'strategy': 'APIFailure',
            'priority': 'Medium',
            'label': 'APIFailure'
        }
    ]

    df = pd.DataFrame(data)
    df['text'] = df['error'].astype(str) + ' ' + df['dom'].astype(str) + ' ' + df['last_action'].astype(str)

    # Text vectorizer
    text_vectorizer = TfidfVectorizer(max_features=500)
    X_text = text_vectorizer.fit_transform(df['text'])

    # Categorical encoder for ['bot','strategy','priority']
    cat_cols = ['bot', 'strategy', 'priority']
    # Create OneHotEncoder with compatibility for different sklearn versions
    try:
        # sklearn >=1.2 uses sparse_output
        cat_encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    except TypeError:
        try:
            cat_encoder = OneHotEncoder(handle_unknown='ignore', sparse=False)
        except TypeError:
            # last resort: use default and handle sparse outputs
            cat_encoder = OneHotEncoder(handle_unknown='ignore')

    cat_encoder.fit(df[cat_cols])
    X_cat_transformed = cat_encoder.transform(df[cat_cols])
    # transform result may be dense ndarray or sparse matrix depending on sklearn
    if hasattr(X_cat_transformed, 'toarray'):
        X_cat = csr_matrix(X_cat_transformed.toarray())
    else:
        # likely already sparse
        X_cat = csr_matrix(X_cat_transformed)

    X = hstack([X_text, X_cat])

    y = df['label']

    clf = LogisticRegression(max_iter=200, solver='liblinear')
    clf.fit(X, y)

    # Write files
    model_path = models_dir / 'ui_failure_model.pkl'
    text_vect_path = models_dir / 'text_vectorizer.pkl'
    cat_enc_path = models_dir / 'cat_encoder.pkl'

    joblib.dump(clf, model_path)
    joblib.dump(text_vectorizer, text_vect_path)
    joblib.dump(cat_encoder, cat_enc_path)

    print('Demo model files written to:', models_dir)
    print('Files:')
    print('-', model_path)
    print('-', text_vect_path)
    print('-', cat_enc_path)


if __name__ == '__main__':
    main()
