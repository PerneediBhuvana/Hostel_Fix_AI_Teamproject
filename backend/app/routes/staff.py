import os
from flask import Blueprint, request, current_app
from flask_jwt_extended import get_jwt_identity
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import Complaint, Notification, User
from ..utils import role_required, serialize_complaint, ALLOWED_STATUSES

staff_bp = Blueprint('staff', __name__)

@staff_bp.get('/complaints')
@role_required('staff')
def assigned_complaints():
    user_id = int(get_jwt_identity())
    items = Complaint.query.filter_by(staff_id=user_id).order_by(Complaint.created_at.desc()).all()
    return {'complaints': [serialize_complaint(item) for item in items]}

@staff_bp.patch('/complaints/<int:complaint_id>')
@role_required('staff')
def update_assigned_complaint(complaint_id):
    user_id = int(get_jwt_identity())
    item = Complaint.query.filter_by(id=complaint_id, staff_id=user_id).first_or_404()
    data = request.form or request.get_json() or {}

    new_status = data.get('status')
    if new_status and new_status not in ALLOWED_STATUSES:
        return {'message': 'Invalid status specified'}, 400

    if new_status:
        item.status = new_status

    remarks = data.get('remarks') or data.get('staffRemarks')
    if remarks:
        item.staff_remarks = remarks.strip()

    image = request.files.get('completionImage')
    if image and image.filename:
        if image.mimetype not in {'image/jpeg', 'image/png', 'image/webp'}:
            return {'message': 'Only image files (JPG, PNG, WEBP) are allowed'}, 400
        filename = secure_filename(f'complete_{item.id}_{image.filename}')
        image.save(os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'], filename))
        item.completion_image_url = f'/uploads/{filename}'

    # Notify student
    db.session.add(Notification(
        message=f"Complaint #{item.id} status changed to '{item.status}' by Maintenance Staff.",
        user_id=item.student_id
    ))

    # Notify Warden if assigned
    if item.warden_id:
        db.session.add(Notification(
            message=f"Staff updated complaint #{item.id} status to '{item.status}'.",
            user_id=item.warden_id
        ))

    db.session.commit()
    return {'message': 'Complaint status updated', 'complaint': serialize_complaint(item)}

