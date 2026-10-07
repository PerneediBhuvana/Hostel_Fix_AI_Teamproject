from flask import Blueprint, request
from sqlalchemy import func
from ..extensions import db
from ..models import Complaint, User, Notification
from ..utils import role_required, serialize_complaint, serialize_user, hash_password, ALLOWED_STATUSES

admin_bp = Blueprint('admin', __name__)

@admin_bp.get('/dashboard')
@role_required('admin')
def dashboard():
    total_users = User.query.count()
    students_count = User.query.filter_by(role='student').count()
    faculty_count = User.query.filter_by(role='faculty').count()
    warden_count = User.query.filter_by(role='warden').count()
    staff_count = User.query.filter_by(role='staff').count()

    total_complaints = Complaint.query.count()
    pending = Complaint.query.filter_by(status='Pending').count()
    approved = Complaint.query.filter_by(status='Approved').count()
    assigned = Complaint.query.filter_by(status='Assigned').count()
    in_progress = Complaint.query.filter_by(status='In Progress').count()
    resolved = Complaint.query.filter_by(status='Resolved').count()
    closed = Complaint.query.filter_by(status='Closed').count()
    rejected = Complaint.query.filter_by(status='Rejected').count()

    # Category counts
    cat_counts = db.session.query(Complaint.category, func.count(Complaint.id))\
        .group_by(Complaint.category).all()
    categories = [{'category': c[0], 'count': c[1]} for c in cat_counts]

    # Block breakdown
    block_counts = db.session.query(Complaint.block, func.count(Complaint.id))\
        .filter(Complaint.block.isnot(None))\
        .group_by(Complaint.block).all()
    blocks = [{'block': b[0] or 'Unassigned', 'count': b[1]} for b in block_counts]

    return {
        'stats': {
            'totalUsers': total_users,
            'students': students_count,
            'faculty': faculty_count,
            'wardens': warden_count,
            'staff': staff_count,
            'complaints': total_complaints,
            'pending': pending,
            'approved': approved,
            'assigned': assigned,
            'inProgress': in_progress,
            'resolved': resolved,
            'closed': closed,
            'rejected': rejected
        },
        'categories': categories,
        'blocks': blocks
    }

@admin_bp.get('/users')
@role_required('admin')
def list_users():
    role = request.args.get('role')
    query = User.query
    if role:
        query = query.filter_by(role=role.lower())
    users = query.order_by(User.name).all()
    return {'users': [serialize_user(u) for u in users]}

@admin_bp.get('/students')
@role_required('admin')
def students():
    users = User.query.filter_by(role='student').order_by(User.name).all()
    return {'students': [serialize_user(u) for u in users]}

@admin_bp.get('/staff')
@role_required('admin')
def staff():
    users = User.query.filter(User.role.in_(['staff', 'faculty', 'warden'])).order_by(User.name).all()
    return {'staff': [serialize_user(u) for u in users]}

@admin_bp.post('/users')
@role_required('admin')
def add_user():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    role = data.get('role', 'staff').lower().strip()

    if not name or not email or not password:
        return {'message': 'Name, email, and password are required'}, 400

    if role not in {'faculty', 'warden', 'staff', 'admin', 'student'}:
        return {'message': 'Invalid role specified'}, 400

    if User.query.filter_by(email=email).first():
        return {'message': 'User with this email already exists'}, 409

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        hostel_block=(data.get('hostelBlock') or data.get('hostel_block') or '').strip(),
        floor=str(data.get('floor') or '').strip(),
        room_no=(data.get('roomNo') or data.get('room_no') or '').strip(),
        department=(data.get('department') or data.get('specialty') or '').strip(),
        phone=data.get('phone', '').strip()
    )

    db.session.add(user)
    db.session.commit()
    return {'message': f'User account created ({role})', 'user': serialize_user(user)}, 201

@admin_bp.get('/reports')
@role_required('admin')
def reports():
    # Hostel Block breakdown
    block_report = db.session.query(
        Complaint.block,
        func.count(Complaint.id).label('total'),
        func.sum(db.case((Complaint.status.in_(['Pending', 'Approved', 'Assigned', 'In Progress']), 1), else_=0)).label('pending'),
        func.sum(db.case((Complaint.status.in_(['Resolved', 'Closed']), 1), else_=0)).label('resolved')
    ).group_by(Complaint.block).all()

    # Floor breakdown
    floor_report = db.session.query(
        Complaint.block,
        Complaint.floor,
        func.count(Complaint.id).label('total'),
        func.sum(db.case((Complaint.status.in_(['Resolved', 'Closed']), 1), else_=0)).label('resolved')
    ).group_by(Complaint.block, Complaint.floor).all()

    # Category breakdown
    category_report = db.session.query(
        Complaint.category,
        func.count(Complaint.id).label('total')
    ).group_by(Complaint.category).all()

    # Faculty performance
    faculty_report = db.session.query(
        User.name,
        func.count(Complaint.id).label('total_handled')
    ).join(Complaint, Complaint.faculty_id == User.id)\
     .group_by(User.id).all()

    # Staff resolution performance
    staff_report = db.session.query(
        User.name,
        func.count(Complaint.id).label('total_assigned'),
        func.sum(db.case((Complaint.status.in_(['Resolved', 'Closed']), 1), else_=0)).label('completed')
    ).join(Complaint, Complaint.staff_id == User.id)\
     .group_by(User.id).all()

    # Pending complaints list
    pending_items = Complaint.query.filter(Complaint.status.in_(['Pending', 'Approved', 'Assigned', 'In Progress']))\
        .order_by(Complaint.created_at.asc()).all()

    return {
        'blocks': [{'block': b[0] or 'General', 'total': b[1], 'pending': int(b[2] or 0), 'resolved': int(b[3] or 0)} for b in block_report],
        'floors': [{'block': f[0] or 'General', 'floor': f[1] or 'G', 'total': f[2], 'resolved': int(f[3] or 0)} for f in floor_report],
        'categories': [{'category': c[0], 'total': c[1]} for c in category_report],
        'facultyPerformance': [{'name': fac[0], 'handled': fac[1]} for fac in faculty_report],
        'staffPerformance': [{'name': s[0], 'assigned': s[1], 'completed': int(s[2] or 0)} for s in staff_report],
        'pendingComplaints': [serialize_complaint(p) for p in pending_items]
    }

