from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models import MealRecord
from ..utils import role_required
from ..ml.food_predictor import predict_demand, DAYS, WEATHER_OPTIONS

food_bp = Blueprint('food', __name__)

MEAL_TYPES = {'Breakfast', 'Lunch', 'Dinner'}


def serialize_meal_record(r):
    if not r:
        return None
    waste = None
    if r.prepared_count is not None and r.consumed_count is not None:
        waste = max(0, r.prepared_count - r.consumed_count)
    accuracy = None
    if r.predicted_count is not None and r.consumed_count is not None and r.consumed_count > 0:
        accuracy = round(100 - (abs(r.predicted_count - r.consumed_count) / r.consumed_count * 100))
    return {
        'id': r.id,
        'date': r.record_date.isoformat(),
        'mealType': r.meal_type,
        'dayOfWeek': r.day_of_week,
        'weather': r.weather,
        'isHoliday': r.is_holiday,
        'isSpecialEvent': r.is_special_event,
        'attendanceCount': r.attendance_count,
        'predictedCount': r.predicted_count,
        'preparedCount': r.prepared_count,
        'consumedCount': r.consumed_count,
        'wasteCount': waste,
        'accuracyPct': accuracy,
        'loggedBy': r.logged_by.name if r.logged_by else None,
    }


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return default


@food_bp.get('/meta')
@role_required('warden', 'admin', 'staff', 'faculty')
def meta():
    return jsonify({'mealTypes': sorted(MEAL_TYPES), 'weatherOptions': WEATHER_OPTIONS})


@food_bp.post('/predict')
@role_required('warden', 'admin', 'staff')
def predict():
    data = request.get_json(silent=True) or {}
    meal_type = data.get('mealType', 'Lunch')
    if meal_type not in MEAL_TYPES:
        return jsonify({'message': 'Invalid meal type'}), 400

    target_date = _parse_date(data.get('date'), date.today() + timedelta(days=1))
    weather = data.get('weather', 'Normal')
    if weather not in WEATHER_OPTIONS:
        weather = 'Normal'
    is_holiday = bool(data.get('isHoliday', False))
    is_special_event = bool(data.get('isSpecialEvent', False))

    history = MealRecord.query.filter(MealRecord.meal_type == meal_type).all()
    result = predict_demand(history, meal_type, target_date, weather, is_holiday, is_special_event)

    # Upsert a MealRecord row for this date/meal so the prediction is tracked
    # and can later be compared against the real prepared/consumed counts.
    record = MealRecord.query.filter_by(record_date=target_date, meal_type=meal_type).first()
    if not record:
        record = MealRecord(
            record_date=target_date,
            meal_type=meal_type,
            day_of_week=DAYS[target_date.weekday()],
        )
        db.session.add(record)

    record.weather = weather
    record.is_holiday = is_holiday
    record.is_special_event = is_special_event
    record.predicted_count = result['predictedCount']
    if record.attendance_count is None and result['factors']['recentAvgAttendance']:
        record.attendance_count = result['factors']['recentAvgAttendance']
    user_id = get_jwt_identity()
    record.logged_by_id = int(user_id) if user_id else record.logged_by_id
    db.session.commit()

    return jsonify({
        'prediction': result,
        'record': serialize_meal_record(record)
    })


@food_bp.patch('/records/<int:record_id>')
@role_required('warden', 'admin', 'staff')
def update_record(record_id):
    record = MealRecord.query.get_or_404(record_id)
    data = request.get_json(silent=True) or {}

    for field, attr in (('attendanceCount', 'attendance_count'), ('preparedCount', 'prepared_count'), ('consumedCount', 'consumed_count')):
        if field in data and data[field] is not None:
            try:
                setattr(record, attr, max(0, int(data[field])))
            except (TypeError, ValueError):
                return jsonify({'message': f'{field} must be a number'}), 400

    user_id = get_jwt_identity()
    record.logged_by_id = int(user_id) if user_id else record.logged_by_id
    db.session.commit()
    return jsonify(serialize_meal_record(record))


@food_bp.post('/records')
@role_required('warden', 'admin', 'staff')
def create_record():
    data = request.get_json(silent=True) or {}
    meal_type = data.get('mealType', 'Lunch')
    if meal_type not in MEAL_TYPES:
        return jsonify({'message': 'Invalid meal type'}), 400
    record_date = _parse_date(data.get('date'), date.today())

    record = MealRecord.query.filter_by(record_date=record_date, meal_type=meal_type).first()
    if not record:
        record = MealRecord(record_date=record_date, meal_type=meal_type, day_of_week=DAYS[record_date.weekday()])
        db.session.add(record)

    record.weather = data.get('weather', record.weather or 'Normal')
    record.is_holiday = bool(data.get('isHoliday', record.is_holiday))
    record.is_special_event = bool(data.get('isSpecialEvent', record.is_special_event))
    for field, attr in (('attendanceCount', 'attendance_count'), ('preparedCount', 'prepared_count'), ('consumedCount', 'consumed_count')):
        if data.get(field) is not None:
            record.__setattr__(attr, max(0, int(data[field])))

    user_id = get_jwt_identity()
    record.logged_by_id = int(user_id) if user_id else record.logged_by_id
    db.session.commit()
    return jsonify(serialize_meal_record(record)), 201


@food_bp.get('/records')
@role_required('warden', 'admin', 'staff', 'faculty')
def list_records():
    meal_type = request.args.get('mealType', 'Lunch')
    limit = min(int(request.args.get('limit', 14)), 90)
    records = (MealRecord.query
               .filter(MealRecord.meal_type == meal_type)
               .order_by(MealRecord.record_date.desc())
               .limit(limit)
               .all())
    return jsonify([serialize_meal_record(r) for r in reversed(records)])


@food_bp.get('/summary')
@role_required('warden', 'admin', 'staff', 'faculty')
def summary():
    meal_type = request.args.get('mealType', 'Lunch')
    since = date.today() - timedelta(days=30)
    records = (MealRecord.query
               .filter(MealRecord.meal_type == meal_type, MealRecord.record_date >= since)
               .order_by(MealRecord.record_date.asc())
               .all())

    total_waste = sum(max(0, (r.prepared_count or 0) - (r.consumed_count or 0)) for r in records if r.prepared_count is not None and r.consumed_count is not None)
    total_prepared = sum(r.prepared_count or 0 for r in records if r.prepared_count is not None)
    logged_days = len([r for r in records if r.consumed_count is not None])

    accuracies = [
        round(100 - (abs(r.predicted_count - r.consumed_count) / r.consumed_count * 100))
        for r in records if r.predicted_count is not None and r.consumed_count is not None and r.consumed_count > 0
    ]
    avg_accuracy = round(sum(accuracies) / len(accuracies)) if accuracies else None

    return jsonify({
        'mealType': meal_type,
        'windowDays': 30,
        'loggedDays': logged_days,
        'totalWasteMeals': total_waste,
        'totalPreparedMeals': total_prepared,
        'wastePct': round((total_waste / total_prepared) * 100, 1) if total_prepared else None,
        'avgPredictionAccuracyPct': avg_accuracy,
    })
