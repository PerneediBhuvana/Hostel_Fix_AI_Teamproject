"""Trained complaint classifier (scikit-learn).

* Category model : TF-IDF (word 1-2 grams + char 2-5 grams) -> Logistic Regression
* Priority model : same features -> Logistic Regression, with a safety rule layer
                   (fire / shock / flooding etc. are always escalated)
* Similar complaints: TF-IDF cosine similarity

Models train in well under a second at start-up from complaint_data.py, so there is no
pickle file to keep in sync. If the model is unsure (low confidence) the caller can fall
back to the old rule-based `ai_analyze`.
"""
import re
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline

from .complaint_data import build_category_dataset, build_priority_dataset, TEST_SET

CONFIDENCE_FLOOR = 0.30

URGENT_TERMS = ('fire', 'smoke', 'sparking', 'sparks', 'electric shock', 'shock from', 'gas leak', 'gas smell',
                'flooding', 'flooded', 'collapsing', 'collapsed', 'food poisoning', 'vomiting', 'injured',
                'emergency', 'live wire', 'trapped', 'stranger inside')
SCOPE_TERMS = ('everyone', 'all students', 'whole floor', 'entire floor', 'whole block', 'entire block',
               'all rooms', 'many students', 'every room', 'no one', 'nobody')
LOW_TERMS = ('minor', 'cosmetic', 'not urgent', 'no hurry', 'when time permits', 'suggestion', 'whenever possible')
PRIORITY_ORDER = ['Low', 'Medium', 'High', 'Urgent']

_lock = threading.Lock()
_state = {}


def _features():
    return FeatureUnion([
        ('word', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)),
        ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), sublinear_tf=True, lowercase=True)),
    ])


def _make_pipeline():
    return Pipeline([
        ('tfidf', _features()),
        ('clf', LogisticRegression(C=12, max_iter=2000, class_weight='balanced')),
    ])


def _ensure_trained():
    if _state:
        return
    with _lock:
        if _state:
            return
        cat_x, cat_y = build_category_dataset()
        pri_x, pri_y = build_priority_dataset()
        cat_model = _make_pipeline().fit(cat_x, cat_y)
        pri_model = _make_pipeline().fit(pri_x, pri_y)
        _state.update(cat=cat_model, pri=pri_model, cat_n=len(cat_x), pri_n=len(pri_x))


def _clean(text):
    return re.sub(r'\s+', ' ', (text or '')).strip()


def _apply_priority_rules(text, label, confidence):
    low = text.lower()
    reasons = []
    idx = PRIORITY_ORDER.index(label)
    if any(t in low for t in URGENT_TERMS):
        idx = PRIORITY_ORDER.index('Urgent')
        reasons.append('safety keyword detected')
    else:
        if any(t in low for t in SCOPE_TERMS):
            idx = max(idx, PRIORITY_ORDER.index('High'))
            reasons.append('affects many residents')
        if any(t in low for t in LOW_TERMS) and idx <= PRIORITY_ORDER.index('Medium'):
            idx = PRIORITY_ORDER.index('Low')
            reasons.append('marked minor / not urgent')
    return PRIORITY_ORDER[idx], reasons


def analyze(title, description=''):
    """Return a dict with category, priority, confidences and top-3 category alternatives."""
    _ensure_trained()
    text = _clean(f'{title}. {description}')
    if not text:
        return {'category': 'Others', 'priority': 'Medium', 'categoryConfidence': 0.0,
                'priorityConfidence': 0.0, 'alternatives': [], 'reasons': [], 'model': 'empty-input'}

    cat_model, pri_model = _state['cat'], _state['pri']
    probs = cat_model.predict_proba([text])[0]
    classes = list(cat_model.classes_)
    ranked = sorted(zip(classes, probs), key=lambda kv: kv[1], reverse=True)
    category, cat_conf = ranked[0]

    p_probs = pri_model.predict_proba([text])[0]
    p_ranked = sorted(zip(pri_model.classes_, p_probs), key=lambda kv: kv[1], reverse=True)
    model_priority, pri_conf = p_ranked[0]
    priority, reasons = _apply_priority_rules(text, model_priority, pri_conf)

    return {
        'category': category,
        'categoryConfidence': round(float(cat_conf), 3),
        'priority': priority,
        'priorityConfidence': round(float(pri_conf), 3),
        'alternatives': [{'category': c, 'confidence': round(float(p), 3)} for c, p in ranked[1:3]],
        'reasons': reasons,
        'lowConfidence': bool(cat_conf < CONFIDENCE_FLOOR),
        'model': 'tfidf+logreg',
    }


def find_similar(text, candidates, threshold=0.55, limit=3):
    """candidates: list of (id, text). Returns best matches by TF-IDF cosine similarity."""
    candidates = [(i, t) for i, t in candidates if t]
    if not candidates or not _clean(text):
        return []
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words='english')
    try:
        matrix = vec.fit_transform([t for _, t in candidates] + [text])
    except ValueError:
        return []
    sims = cosine_similarity(matrix[-1], matrix[:-1])[0]
    hits = [(candidates[i][0], float(s)) for i, s in enumerate(sims) if s >= threshold]
    hits.sort(key=lambda kv: kv[1], reverse=True)
    return [{'id': cid, 'similarity': round(s * 100)} for cid, s in hits[:limit]]


def evaluate():
    """Honest metrics: cross-validation on training data + accuracy on the held-out hand-written set."""
    _ensure_trained()
    cat_x, cat_y = build_category_dataset()
    pri_x, pri_y = build_priority_dataset()
    cv_cat = cross_val_score(_make_pipeline(), cat_x, cat_y, cv=5).mean()
    cv_pri = cross_val_score(_make_pipeline(), pri_x, pri_y, cv=4).mean()
    right, misses = 0, []
    for text, label in TEST_SET:
        got = analyze(text)['category']
        if got == label:
            right += 1
        else:
            misses.append((text, label, got))
    return {
        'trainingExamples': {'category': _state['cat_n'], 'priority': _state['pri_n']},
        'categoryCV': round(float(cv_cat), 3),
        'priorityCV': round(float(cv_pri), 3),
        'heldOutAccuracy': round(right / len(TEST_SET), 3),
        'heldOutSize': len(TEST_SET),
        'misses': misses,
    }


if __name__ == '__main__':
    import json
    print(json.dumps(evaluate(), indent=2))
