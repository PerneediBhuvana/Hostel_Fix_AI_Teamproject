from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, get_jwt
from ..extensions import db
from ..models import Complaint, Notification, User
from ..utils import role_required, serialize_complaint

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.get('/complaints')
@role_required('faculty', 'admin')
def floor_complaints():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    query = Complaint.query
    if user and user.hostel_block and user.floor:
        query = query.filter(Complaint.block == user.hostel_block, Complaint.floor == str(user.floor))
    else:
        query = query.filter_by(faculty_id=user_id)

    items = query.order_by(Complaint.created_at.desc()).all()
    return {'complaints': [serialize_complaint(item) for item in items]}

@faculty_bp.patch('/complaints/<int:complaint_id>/review')
@role_required('faculty', 'admin')
def review_complaint(complaint_id):
    user_id = int(get_jwt_identity())
    item = Complaint.query.get_or_404(complaint_id)
    data = request.get_json() or {}

    action = data.get('action', '').lower().strip() # 'approve' or 'reject'
    remarks = data.get('remarks', '').strip()

    if action not in {'approve', 'reject'}:
        return {'message': 'Action must be either "approve" or "reject"'}, 400

    item.faculty_id = user_id
    item.faculty_remarks = remarks

    if action == 'approve':
        item.status = 'Approved'
        # Find Warden for block
        warden = User.query.filter_by(role='warden', hostel_block=item.block).first()
        if warden:
            item.warden_id = warden.id
            db.session.add(Notification(
                message=f"Floor Coordinator approved complaint #{item.id} ({item.title}). Pending staff assignment.",
                user_id=warden.id
            ))
        
        # Notify student
        db.session.add(Notification(
            message=f"Your complaint #{item.id} was verified & approved by Floor Coordinator. Forwarded to Warden.",
            user_id=item.student_id
        ))
    else:
        item.status = 'Rejected'
        # Notify student
        db.session.add(Notification(
            message=f"Your complaint #{item.id} was rejected by Floor Coordinator. Reason: {remarks or 'Did not meet criteria'}",
            user_id=item.student_id
        ))

    db.session.commit()
    return {'message': f'Complaint #{item.id} {item.status.lower()}', 'complaint': serialize_complaint(item)}
