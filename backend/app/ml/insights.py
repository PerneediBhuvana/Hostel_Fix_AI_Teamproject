"""AI Insights: hotspot detection, complaint-volume forecast, resolution-time estimates.

All functions take plain dicts so they can be unit-tested without a database:
    {'category','block','priority','status','created_at': datetime, 'resolved_at': datetime|None, 'rating': int|None}
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge

PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
RESOLVED = {'Resolved', 'Closed'}


# ---------------------------------------------------------------- hotspots
def detect_hotspots(items, now=None, window_days=14, min_recent=4, ratio=1.8):
    """Flag (block, category) pairs whose last-`window_days` count jumped versus the window before."""
    now = now or datetime.utcnow()
    recent_start = now - timedelta(days=window_days)
    prev_start = now - timedelta(days=window_days * 2)
    recent, prev = Counter(), Counter()
    for c in items:
        key = (c.get('block') or 'Unknown', c.get('category') or 'Others')
        if c['created_at'] >= recent_start:
            recent[key] += 1
        elif c['created_at'] >= prev_start:
            prev[key] += 1
    out = []
    for key, n in recent.items():
        before = prev.get(key, 0)
        if n >= min_recent and n >= ratio * max(before, 1):
            out.append({
                'block': key[0], 'category': key[1], 'recent': n, 'previous': before,
                'changePct': None if before == 0 else round((n - before) / before * 100),
                'severity': 'critical' if n >= 2 * min_recent and before <= 1 else 'warning',
                'message': f'{key[1]} complaints in {key[0]} rose to {n} in the last {window_days} days (previously {before}).',
            })
    out.sort(key=lambda h: (h['severity'] != 'critical', -h['recent']))
    return out


# ---------------------------------------------------------------- forecast
def _week_start(d):
    d = d.replace(hour=0, minute=0, second=0, microsecond=0)
    return d - timedelta(days=d.weekday())


def forecast_volume(items, now=None, weeks_back=10, weeks_ahead=2):
    """Linear-regression forecast of weekly complaint counts (current partial week excluded)."""
    now = now or datetime.utcnow()
    this_week = _week_start(now)
    starts = [this_week - timedelta(weeks=i) for i in range(weeks_back, 0, -1)]
    counts = {s: 0 for s in starts}
    for c in items:
        ws = _week_start(c['created_at'])
        if ws in counts:
            counts[ws] += 1
    y = np.array([counts[s] for s in starts], dtype=float)
    result = {'history': [{'weekStart': s.date().isoformat(), 'count': int(counts[s])} for s in starts],
              'forecast': [], 'trend': 'not enough data', 'slopePerWeek': 0.0, 'r2': None}
    if y.sum() < 6 or np.count_nonzero(y) < 4:
        return result
    X = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(X, y)
    slope = float(model.coef_[0])
    result['slopePerWeek'] = round(slope, 2)
    result['r2'] = round(float(model.score(X, y)), 3)
    result['trend'] = 'rising' if slope > 0.4 else 'falling' if slope < -0.4 else 'stable'
    for k in range(1, weeks_ahead + 1):
        pred = float(model.predict([[len(y) - 1 + k]])[0])
        result['forecast'].append({'weekStart': (this_week + timedelta(weeks=k - 1)).date().isoformat(),
                                   'count': max(0, round(pred))})
    return result


def category_trends(items, now=None, window_days=30):
    now = now or datetime.utcnow()
    cur_start, prev_start = now - timedelta(days=window_days), now - timedelta(days=2 * window_days)
    cur, prev = Counter(), Counter()
    for c in items:
        if c['created_at'] >= cur_start:
            cur[c['category']] += 1
        elif c['created_at'] >= prev_start:
            prev[c['category']] += 1
    rows = []
    for cat in set(cur) | set(prev):
        rows.append({'category': cat, 'last30': cur[cat], 'previous30': prev[cat], 'delta': cur[cat] - prev[cat]})
    rows.sort(key=lambda r: r['last30'], reverse=True)
    return rows


# ---------------------------------------------------------------- resolution time
class ResolutionTimeModel:
    """Ridge regression on log(hours) with one-hot category + priority.

    Falls back to a global median if there are fewer than `min_samples` resolved complaints.
    """

    def __init__(self, items, min_samples=15):
        self.rows = []
        for c in items:
            if c.get('status') in RESOLVED and c.get('resolved_at'):
                hours = (c['resolved_at'] - c['created_at']).total_seconds() / 3600
                if hours > 0:
                    self.rows.append((c['category'], c['priority'], hours))
        self.cats = sorted({r[0] for r in self.rows})
        self.n = len(self.rows)
        self.model = None
        self.global_median = float(np.median([r[2] for r in self.rows])) if self.rows else None
        if self.n >= min_samples:
            X = np.array([self._vec(r[0], r[1]) for r in self.rows])
            y = np.log([r[2] for r in self.rows])
            self.model = Ridge(alpha=1.0).fit(X, y)

    def _vec(self, category, priority):
        v = [1.0 if category == c else 0.0 for c in self.cats]
        v += [1.0 if priority == p else 0.0 for p in PRIORITIES]
        return v

    def predict_hours(self, category, priority):
        if self.model is not None and category in self.cats:
            return float(np.exp(self.model.predict([self._vec(category, priority)])[0]))
        return self.global_median

    def summary(self):
        by_cat = defaultdict(list)
        for cat, _, h in self.rows:
            by_cat[cat].append(h)
        return sorted(({'category': k, 'avgHours': round(float(np.mean(v)), 1), 'resolved': len(v)} for k, v in by_cat.items()),
                      key=lambda r: r['avgHours'], reverse=True)


def format_eta(hours):
    if hours is None:
        return None
    if hours < 1:
        return 'under an hour'
    if hours < 48:
        return f'about {round(hours)} hours'
    return f'about {round(hours / 24, 1)} days'


# ---------------------------------------------------------------- satisfaction
def rating_by_category(items):
    by_cat = defaultdict(list)
    for c in items:
        if c.get('rating'):
            by_cat[c['category']].append(c['rating'])
    return sorted(({'category': k, 'avgRating': round(float(np.mean(v)), 2), 'count': len(v)} for k, v in by_cat.items()),
                  key=lambda r: r['avgRating'])


def build_insights(items, now=None):
    now = now or datetime.utcnow()
    rt = ResolutionTimeModel(items)
    recs = []
    hotspots = detect_hotspots(items, now)
    for h in hotspots[:3]:
        recs.append(f"Look into {h['category'].lower()} issues in {h['block']}: complaints jumped from {h['previous']} to {h['recent']} in two weeks.")
    slow = [r for r in rt.summary() if r['resolved'] >= 3][:1]
    if slow:
        recs.append(f"{slow[0]['category']} complaints take the longest to resolve (avg {format_eta(slow[0]['avgHours'])}); consider keeping spare parts or a dedicated technician.")
    low_rated = [r for r in rating_by_category(items) if r['count'] >= 3 and r['avgRating'] < 3.2][:1]
    if low_rated:
        recs.append(f"Residents rate {low_rated[0]['category']} fixes lowest ({low_rated[0]['avgRating']}/5); review the quality of these repairs.")
    return {
        'generatedAt': now.isoformat(),
        'totalAnalysed': len(items),
        'hotspots': hotspots,
        'forecast': forecast_volume(items, now),
        'categoryTrends': category_trends(items, now),
        'resolutionTime': {'samples': rt.n, 'byCategory': rt.summary(), 'method': 'ridge-regression' if rt.model else 'median-fallback'},
        'satisfaction': rating_by_category(items),
        'recommendations': recs,
    }
