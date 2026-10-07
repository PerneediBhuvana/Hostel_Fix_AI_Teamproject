from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models import Complaint, Notification, User
from ..utils import role_required, serialize_complaint, ALLOWED_PRIORITIES

warden_bp = Blueprint('warden', __name__)

@warden_bp.get('/complaints')
@role_required('warden', 'admin')
def block_complaints():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    query = Complaint.query
    if user and user.hostel_block:
        query = query.filter(Complaint.block == user.hostel_block)
    else:
        query = query.filter_by(warden_id=user_id)

    items = query.order_by(Complaint.created_at.desc()).all()
    return {'complaints': [serialize_complaint(item) for item in items]}

@warden_bp.post('/complaints/<int:complaint_id>/assign')
@role_required('warden', 'admin')
def assign_staff(complaint_id):
    user_id = int(get_jwt_identity())
    item = Complaint.query.get_or_404(complaint_id)
    data = request.get_json() or {}

    staff_id = data.get('staffId')
    if not staff_id:
        return {'message': 'Staff ID is required for assignment'}, 400

    staff = User.query.filter_by(id=int(staff_id), role='staff').first()
    if not staff:
        return {'message': 'Selected staff member not found'}, 404

    item.staff_id = staff.id
    item.warden_id = user_id
    item.status = 'Assigned'
    if data.get('priority') in ALLOWED_PRIORITIES:
        item.priority = data['priority']
    if data.get('remarks'):
        item.warden_remarks = data['remarks'].strip()

    # Notify staff
    db.session.add(Notification(
        message=f"You have been assigned complaint #{item.id} ({item.title}) in {item.block} Room {item.room_no}.",
        user_id=staff.id
    ))

    # Notify student
    db.session.add(Notification(
        message=f"Complaint #{item.id} has been assigned to Maintenance Staff ({staff.name}).",
        user_id=item.student_id
    ))

    db.session.commit()
    return {'message': 'Staff assigned successfully', 'complaint': serialize_complaint(item)}

@warden_bp.patch('/complaints/<int:complaint_id>/close')
@role_required('warden', 'admin')
def close_complaint(complaint_id):
    user_id = int(get_jwt_identity())
    item = Complaint.query.get_or_404(complaint_id)
    data = request.get_json() or {}

    item.status = 'Closed'
    item.warden_id = user_id
    if data.get('remarks'):
        item.warden_remarks = data['remarks'].strip()

    # Notify student
    db.session.add(Notification(
        message=f"Complaint #{item.id} has been verified and closed by Warden.",
        user_id=item.student_id
    ))

    db.session.commit()
    return {'message': 'Complaint closed', 'complaint': serialize_complaint(item)}
