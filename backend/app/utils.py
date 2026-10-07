import os
import bcrypt
from functools import wraps
import re
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request

ALLOWED_CATEGORIES = {'Water', 'Electricity', 'WiFi', 'Internet', 'Food', 'Cleaning', 'Plumbing', 'Furniture', 'Security', 'Others'}
ALLOWED_PRIORITIES = {'Low', 'Medium', 'High', 'Urgent'}
ALLOWED_STATUSES = {'Pending', 'Approved', 'Rejected', 'Assigned', 'In Progress', 'Resolved', 'Closed'}

AI_CATEGORY_RULES = {
    'Electricity': ('fan', 'light', 'switch', 'power', 'electric', 'voltage', 'socket'),
    'Plumbing': ('water', 'leak', 'tap', 'pipe', 'toilet', 'drain', 'flush'),
    'Furniture': ('chair', 'table', 'bed', 'desk', 'cupboard', 'furniture'),
    'Cleaning': ('clean', 'garbage', 'dust', 'dirty', 'washroom', 'pest'),
    'Internet': ('wifi', 'internet', 'network', 'router', 'connection'),
    'Security': ('security', 'lock', 'guard', 'theft', 'unsafe'),
    'Food': ('food', 'mess', 'meal', 'canteen', 'menu', 'breakfast', 'lunch', 'dinner', 'stale', 'undercooked', 'hygiene', 'tasteless'),
}

def rule_based_analyze(title, description):
    text = f'{title} {description}'.lower()
    scores = {category: sum(1 for word in words if re.search(rf'\b{re.escape(word)}\b', text)) for category, words in AI_CATEGORY_RULES.items()}
    category = max(scores, key=scores.get) if max(scores.values()) and scores[max(scores, key=scores.get)] > 0 else 'Others'
    priority = 'High' if any(word in text for word in ('urgent', 'danger', 'flood', 'fire', 'sparking', 'everywhere', 'not working')) else 'Low' if any(word in text for word in ('minor', 'small', 'broken chair', 'cosmetic')) else 'Medium'
    return category, priority

def ai_analyze(title, description):
    """Trained TF-IDF + Logistic Regression classifier; falls back to keyword rules if unsure or unavailable."""
    try:
        from .ml.complaint_classifier import analyze
        result = analyze(title, description)
        if not result.get('lowConfidence') and result['category'] in ALLOWED_CATEGORIES:
            return result['category'], result['priority']
        return rule_based_analyze(title, description)[0], result['priority']
    except Exception:
        return rule_based_analyze(title, description)

def similarity(left, right):
    first = set(re.findall(r'\w+', left.lower()))
    second = set(re.findall(r'\w+', right.lower()))
    return round((len(first & second) / max(len(first | second), 1)) * 100)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Skip authentication for preflight requests
            from flask import request
            if request.method == 'OPTIONS':
                return fn(*args, **kwargs)
            
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') not in roles:
                return jsonify({'message': 'Insufficient permissions for this operation'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def serialize_user(user):
    if not user:
        return None
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'hostelBlock': user.hostel_block,
        'floor': user.floor,
        'roomNo': user.room_no,
        'department': user.department,
        'phone': user.phone,
        'isActive': user.is_active
    }

def serialize_complaint(item):
    if not item:
        return None
    return {
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'category': item.category,
        'priority': item.priority,
        'aiCategory': item.ai_category,
        'aiPriority': item.ai_priority,
        'status': item.status,
        'block': item.block,
        'floor': item.floor,
        'roomNo': item.room_no,
        'imageUrl': item.image_url,
        'completionImageUrl': item.completion_image_url,
        'facultyRemarks': item.faculty_remarks,
        'wardenRemarks': item.warden_remarks,
        'staffRemarks': item.staff_remarks,
        'studentId': item.student_id,
        'studentName': item.student.name if item.student else None,
        'facultyId': item.faculty_id,
        'facultyName': item.faculty.name if item.faculty else None,
        'wardenId': item.warden_id,
        'wardenName': item.warden.name if item.warden else None,
        'staffId': item.staff_id,
        'staffName': item.staff.name if item.staff else None,
        'affectedStudents': item.affected_students,
        'duplicateOfId': item.duplicate_of_id,
        'feedback': {'rating': item.feedback.rating, 'comment': item.feedback.comment} if item.feedback else None,
        'createdAt': item.created_at.isoformat() if item.created_at else None,
        'updatedAt': item.updated_at.isoformat() if item.updated_at else None
    }

