import os
from flask import Blueprint, request, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import Complaint, Notification, User, Feedback
from ..utils import role_required, serialize_complaint, ALLOWED_CATEGORIES, ALLOWED_PRIORITIES, ai_analyze, similarity

complaints_bp = Blueprint('complaints', __name__)

@complaints_bp.get('')
@role_required('student', 'faculty', 'warden', 'staff', 'admin')
def get_complaints():
    user_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    user = User.query.get(user_id)
    query = Complaint.query

    if role == 'student' or request.args.get('mine') == 'true':
        query = query.filter_by(student_id=user_id)
    elif role == 'faculty':
        if user and user.hostel_block and user.floor:
            query = query.filter(Complaint.block == user.hostel_block, Complaint.floor == str(user.floor))
        else:
            query = query.filter(Complaint.faculty_id == user_id)
    elif role == 'warden':
        if user and user.hostel_block:
            query = query.filter(Complaint.block == user.hostel_block)
        else:
            query = query.filter(Complaint.warden_id == user_id)
    elif role == 'staff':
        query = query.filter_by(staff_id=user_id)

    items = query.order_by(Complaint.created_at.desc()).all()
    return {'complaints': [serialize_complaint(item) for item in items]}

@complaints_bp.get('/<int:complaint_id>')
@role_required('student', 'faculty', 'warden', 'staff', 'admin')
def get_complaint_by_id(complaint_id):
    item = Complaint.query.get_or_404(complaint_id)
    return {'complaint': serialize_complaint(item)}

@complaints_bp.post('')
@role_required('student')
def create_complaint():
    try:
        user_id = int(get_jwt_identity())
        student = User.query.get(user_id)
        data = request.form or request.get_json() or {}

        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()

        if not title or not description:
            return {'message': 'Title and description are required'}, 400

        block = (data.get('block') or data.get('hostelBlock') or student.hostel_block or '').strip()
        floor = str(data.get('floor') or student.floor or '').strip()
        room_no = (data.get('roomNo') or data.get('room_no') or student.room_no or '').strip()

        ai_category, ai_priority = ai_analyze(title, description)
        category = data.get('category') if data.get('category') in ALLOWED_CATEGORIES else ai_category
        priority = data.get('priority') if data.get('priority') in ALLOWED_PRIORITIES else ai_priority

        image = request.files.get('image')
        image_url = None
        if image and image.filename:
            if image.mimetype not in {'image/jpeg', 'image/png', 'image/webp'}:
                return {'message': 'Only JPG, PNG, and WEBP images are allowed'}, 400
            filename = secure_filename(f"req_{user_id}_{image.filename}")
            image.save(os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/uploads/{filename}'

        # Auto-assign Floor Coordinator (Faculty) & Warden for block/floor
        faculty = User.query.filter_by(role='faculty', hostel_block=block, floor=floor).first()
        warden = User.query.filter_by(role='warden', hostel_block=block).first()

        duplicate = next((existing for existing in Complaint.query.filter(Complaint.status.notin_(['Resolved', 'Closed', 'Rejected'])).all()
                          if similarity(f"{existing.title} {existing.description}", f"{title} {description}") >= 72), None)

        item = Complaint(
            title=title,
            description=description,
            category=category,
            priority=priority,
            status='Pending',
            block=block,
            floor=floor,
            room_no=room_no,
            image_url=image_url,
            ai_category=ai_category,
            ai_priority=ai_priority,
            duplicate_of_id=duplicate.id if duplicate else None,
            affected_students=(duplicate.affected_students + 1) if duplicate else 1,
            student_id=user_id,
            faculty_id=faculty.id if faculty else None,
            warden_id=warden.id if warden else None
        )

        if duplicate:
            duplicate.affected_students += 1

        db.session.add(item)
        db.session.flush()

        # Notify Floor Coordinator (Faculty)
        if faculty:
            db.session.add(Notification(
                message=f"New complaint #{item.id} raised in {block} Floor {floor} (Room {room_no}). Pending verification.",
                user_id=faculty.id
            ))

        # Notify Student
        db.session.add(Notification(
            message=f"Complaint #{item.id} submitted successfully. Assigned to Floor Coordinator for verification.",
            user_id=user_id
        ))

        db.session.commit()

        result = serialize_complaint(item)
        result['ai'] = {
            'category': ai_category,
            'priority': ai_priority,
            'duplicateFound': bool(duplicate),
            'duplicateOf': duplicate.id if duplicate else None
        }
        return {'complaint': result}, 201
    except Exception as e:
        current_app.logger.exception('Error creating complaint')
        return {'message': f'Server error while creating complaint: {str(e)}'}, 500

@complaints_bp.post('/<int:complaint_id>/feedback')
@role_required('student')
def add_feedback(complaint_id):
    user_id = int(get_jwt_identity())
    item = Complaint.query.filter_by(id=complaint_id, student_id=user_id).first_or_404()
    if item.status not in {'Resolved', 'Closed'}:
        return {'message': 'Feedback is available only after complaint resolution'}, 409

    data = request.get_json() or {}
    rating = int(data.get('rating', 0))
    if rating not in range(1, 6):
        return {'message': 'Rating must be between 1 and 5'}, 400

    feedback = item.feedback or Feedback(complaint_id=item.id, student_id=item.student_id, rating=rating)
    feedback.rating = rating
    feedback.comment = data.get('comment', '').strip()
    db.session.add(feedback)
    db.session.commit()
    return {'message': 'Feedback saved successfully', 'feedback': {'rating': feedback.rating, 'comment': feedback.comment}}

@complaints_bp.patch('/<int:complaint_id>')
@role_required('student')
def update_complaint(complaint_id):
    user_id = int(get_jwt_identity())
    item = Complaint.query.filter_by(id=complaint_id, student_id=user_id).first_or_404()
    if item.status != 'Pending':
        return {'message': 'Only pending complaints can be edited'}, 409

    data = request.get_json() or {}
    for field in ('title', 'description', 'category', 'priority', 'block', 'floor', 'room_no'):
        if field in data:
            setattr(item, field, data[field])

    db.session.commit()
    return {'complaint': serialize_complaint(item)}

@complaints_bp.delete('/<int:complaint_id>')
@role_required('student', 'admin')
def delete_complaint(complaint_id):
    item = Complaint.query.get_or_404(complaint_id)
    claims = get_jwt()
    if claims.get('role') == 'student' and item.student_id != int(get_jwt_identity()):
        return {'message': 'You can only delete your own complaints'}, 403
    if claims.get('role') == 'student' and item.status != 'Pending':
        return {'message': 'Only pending complaints can be deleted'}, 409

    db.session.delete(item)
    db.session.commit()
    return {'message': 'Complaint deleted successfully'}
