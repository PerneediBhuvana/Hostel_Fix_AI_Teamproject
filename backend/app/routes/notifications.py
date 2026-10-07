from flask import Blueprint
from flask_jwt_extended import get_jwt_identity
from ..models import Notification
from ..extensions import db
from ..utils import role_required

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.get('')
@role_required('student', 'faculty', 'warden', 'staff', 'admin')
def notifications():
    user_id = int(get_jwt_identity())
    items = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    return {'notifications': [{'id': item.id, 'message': item.message, 'isRead': item.is_read, 'createdAt': item.created_at.isoformat()} for item in items]}

@notifications_bp.post('/<int:notification_id>/read')
@role_required('student', 'faculty', 'warden', 'staff', 'admin')
def mark_read(notification_id):
    user_id = int(get_jwt_identity())
    item = Notification.query.filter_by(id=notification_id, user_id=user_id).first_or_404()
    item.is_read = True
    db.session.commit()
    return {'message': 'Notification marked as read'}

