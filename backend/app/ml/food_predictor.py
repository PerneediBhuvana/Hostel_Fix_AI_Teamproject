"""
Food Waste Predictor
---------------------
Predicts how many meals will actually be eaten (consumed_count) for a
future date/meal_type, using historical MealRecord data.

Features used (matches the factors a canteen manager would naturally reason about):
  - day of week
  - weather condition
  - whether it's a holiday
  - whether there's a special event
  - recent average attendance (last up to 3 records of the same meal type)
  - recent average consumption (last up to 3 records of the same meal type)

Model: scikit-learn LinearRegression trained fresh on every request from
whatever history exists in the DB (the dataset is small — a few hundred
rows at most — so retraining on demand is cheap and always uses the latest
data).

Fallback: if there isn't enough history yet (< MIN_TRAINING_ROWS complete
records), we fall back to a simple weighted-average heuristic so the
feature still works on a brand-new install before enough real data has
been logged.
"""
from datetime import date, timedelta
from statistics import mean

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
WEATHER_OPTIONS = ['Normal', 'Sunny', 'Rainy', 'Cloudy', 'Hot', 'Cold']
MIN_TRAINING_ROWS = 10

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:  # sklearn not installed yet — heuristic fallback still works
    SKLEARN_AVAILABLE = False


def _recent_averages(history, before_date, meal_type, window=3):
    """Average attendance/consumption from the most recent up-to-`window`
    records of this meal_type strictly before `before_date`."""
    prior = sorted(
        [r for r in history if r.meal_type == meal_type and r.record_date < before_date and r.consumed_count is not None],
        key=lambda r: r.record_date,
        reverse=True
    )[:window]
    if not prior:
        return None, None
    attendance_vals = [r.attendance_count for r in prior if r.attendance_count is not None]
    consumed_vals = [r.consumed_count for r in prior if r.consumed_count is not None]
    avg_attendance = mean(attendance_vals) if attendance_vals else None
    avg_consumed = mean(consumed_vals) if consumed_vals else None
    return avg_attendance, avg_consumed


def _encode_features(day_of_week, weather, is_holiday, is_special_event, avg_attendance, avg_consumed, fallback_avg_consumed):
    day_vec = [1.0 if day_of_week == d else 0.0 for d in DAYS]
    weather_vec = [1.0 if weather == w else 0.0 for w in WEATHER_OPTIONS]
    holiday = 1.0 if is_holiday else 0.0
    event = 1.0 if is_special_event else 0.0
    att = avg_attendance if avg_attendance is not None else (fallback_avg_consumed or 0)
    cons = avg_consumed if avg_consumed is not None else (fallback_avg_consumed or 0)
    return day_vec + weather_vec + [holiday, event, att, cons]


def _build_training_set(history, meal_type):
    rows = sorted(
        [r for r in history if r.meal_type == meal_type and r.consumed_count is not None],
        key=lambda r: r.record_date
    )
    fallback_avg = mean([r.consumed_count for r in rows]) if rows else None
    X, y = [], []
    for r in rows:
        avg_attendance, avg_consumed = _recent_averages(history, r.record_date, meal_type)
        if avg_attendance is None and avg_consumed is None:
            continue  # skip the very first record(s) with no prior history to learn from
        X.append(_encode_features(r.day_of_week, r.weather, r.is_holiday, r.is_special_event, avg_attendance, avg_consumed, fallback_avg))
        y.append(r.consumed_count)
    return X, y, fallback_avg


def _heuristic_predict(history, meal_type, target_date, weather, is_holiday, is_special_event):
    """Weighted-average fallback used when there isn't enough data to train a model yet."""
    same_meal = [r for r in history if r.meal_type == meal_type and r.consumed_count is not None]
    if not same_meal:
        return 200, 'low'  # sensible generic starting default for a hostel mess

    target_day = DAYS[target_date.weekday()]
    same_weekday = [r.consumed_count for r in same_meal if r.day_of_week == target_day]
    base = mean(same_weekday) if same_weekday else mean([r.consumed_count for r in same_meal])

    recent = sorted(same_meal, key=lambda r: r.record_date, reverse=True)[:5]
    recent_avg = mean([r.consumed_count for r in recent])

    predicted = 0.6 * base + 0.4 * recent_avg

    if is_holiday:
        predicted *= 0.55
    if is_special_event:
        predicted *= 1.25
    if weather in ('Rainy', 'Cold'):
        predicted *= 0.95

    confidence = 'medium' if len(same_meal) >= 5 else 'low'
    return round(predicted), confidence


def predict_demand(history, meal_type, target_date, weather='Normal', is_holiday=False, is_special_event=False):
    """
    Returns dict: {
        predictedCount, confidence, method, factors: {...}
    }
    `history` is a list of MealRecord objects (already fetched from DB).
    """
    target_day = DAYS[target_date.weekday()]
    avg_attendance, avg_consumed = _recent_averages(history, target_date, meal_type)

    X, y, fallback_avg = _build_training_set(history, meal_type)

    method = 'linear_regression'
    if SKLEARN_AVAILABLE and len(X) >= MIN_TRAINING_ROWS:
        model = LinearRegression()
        model.fit(X, y)
        features = _encode_features(target_day, weather, is_holiday, is_special_event, avg_attendance, avg_consumed, fallback_avg)
        predicted_count = max(0, round(model.predict([features])[0]))
        confidence = 'high' if len(X) >= 25 else 'medium'
    else:
        predicted_count, confidence = _heuristic_predict(history, meal_type, target_date, weather, is_holiday, is_special_event)
        method = 'weighted_average'

    return {
        'predictedCount': int(predicted_count),
        'confidence': confidence,
        'method': method,
        'trainingSamples': len(X),
        'factors': {
            'dayOfWeek': target_day,
            'weather': weather,
            'isHoliday': is_holiday,
            'isSpecialEvent': is_special_event,
            'recentAvgAttendance': round(avg_attendance) if avg_attendance is not None else None,
            'recentAvgConsumed': round(avg_consumed) if avg_consumed is not None else None,
        }
    }
