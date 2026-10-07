import time
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, get_jwt
from ..models import Complaint, User
from ..utils import role_required
from ..ml import complaint_classifier as classifier
from ..ml.insights import build_insights, ResolutionTimeModel, format_eta

ai_bp = Blueprint('ai', __name__)

_cache = {'eta': (0, None), 'metrics': (0, None)}


def _load_items(block=None):
    query = Complaint.query
    if block:
        query = query.filter(Complaint.block == block)
    items = []
    for c in query.all():
        items.append({
            'category': c.category, 'block': c.block, 'priority': c.priority, 'status': c.status,
            'created_at': c.created_at,
            'resolved_at': c.updated_at if c.status in ('Resolved', 'Closed') else None,
            'rating': c.feedback.rating if c.feedback else None,
        })
    return items


def _eta_model():
    ts, model = _cache['eta']
    if model is None or time.time() - ts > 300:
        model = ResolutionTimeModel(_load_items())
        _cache['eta'] = (time.time(), model)
    return model


@ai_bp.post('/analyze')
@role_required('student', 'faculty', 'warden', 'staff', 'admin')
def analyze():
    """Live suggestion while the student types: category, priority, ETA, similar open complaints."""
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    if len(f'{title} {description}') < 6:
        return {'ready': False}

    result = classifier.analyze(title, description)
    hours = _eta_model().predict_hours(result['category'], result['priority'])
    result['estimatedHours'] = round(hours, 1) if hours else None
    result['estimatedResolution'] = format_eta(hours)

    open_items = Complaint.query.filter(Complaint.status.notin_(['Resolved', 'Closed', 'Rejected']))
    block = (data.get('block') or '').strip()
    if block:
        open_items = open_items.filter(Complaint.block == block)
    candidates = [(c.id, f'{c.title} {c.description}') for c in open_items.limit(300).all()]
    similar = classifier.find_similar(f'{title} {description}', candidates)
    lookup = {c.id: c for c in Complaint.query.filter(Complaint.id.in_([s['id'] for s in similar])).all()} if similar else {}
    result['similar'] = [{'id': s['id'], 'similarity': s['similarity'], 'title': lookup[s['id']].title,
                          'status': lookup[s['id']].status} for s in similar if s['id'] in lookup]
    result['ready'] = True
    return result


@ai_bp.get('/insights')
@role_required('warden', 'admin')
def insights():
    block = None
    if get_jwt().get('role') == 'warden':
        user = User.query.get(int(get_jwt_identity()))
        block = user.hostel_block if user else None
    data = build_insights(_load_items(block))
    data['scope'] = block or 'All blocks'
    return data


@ai_bp.get('/model-info')
@role_required('admin', 'warden')
def model_info():
    ts, cached = _cache['metrics']
    if cached is None or time.time() - ts > 3600:
        cached = classifier.evaluate()
        cached['misses'] = [{'text': t, 'expected': e, 'got': g} for t, e, g in cached['misses']]
        _cache['metrics'] = (time.time(), cached)
    return cached
