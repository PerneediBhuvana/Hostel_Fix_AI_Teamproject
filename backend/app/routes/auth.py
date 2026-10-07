from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from ..extensions import db
from ..models import User
from ..utils import check_password, hash_password, serialize_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    role = data.get('role', 'student').lower().strip()
    email = data.get('email', '').lower().strip()
    name = data.get('name', '').strip()
    password = data.get('password', '')

    if role != 'student':
        return {'message': 'Self-registration is restricted to students. Faculty, Warden, Staff, and Admin accounts are pre-provisioned by college administration.'}, 403

    if not name or not email or not password:
        return {'message': 'Name, email, and password are required'}, 400

    room_number = data.get('roomNumber') or data.get('room_no') or ''
    hostel_block = data.get('hostelBlock') or data.get('hostel_block') or ''
    floor = str(data.get('floor') or '')
    phone = data.get('phone', '').strip()
    department = data.get('department', '').strip()

    if not room_number or not hostel_block or not phone:
        return {'message': 'Room number, hostel block, and phone number are required for student registration'}, 400

    if User.query.filter_by(email=email).first():
        return {'message': 'Email is already registered'}, 409

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role='student',
        hostel_block=hostel_block.strip(),
        floor=floor.strip(),
        room_no=room_number.strip(),
        phone=phone,
        department=department
    )

    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id), additional_claims={'role': 'student', 'name': user.name})
    return {'accessToken': token, 'user': serialize_user(user)}, 201

@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    requested_role = data.get('role')

    if not email or not password:
        return {'message': 'Email and password are required'}, 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password(password, user.password_hash):
        return {'message': 'Invalid email or password'}, 401

    if requested_role and user.role.lower() != requested_role.lower():
        return {'message': f'Account exists but role is "{user.role}". Please select the correct role tab.'}, 401

    if not user.is_active:
        return {'message': 'Your account has been deactivated. Please contact administration.'}, 403

    token = create_access_token(identity=str(user.id), additional_claims={'role': user.role, 'name': user.name})
    return {'accessToken': token, 'user': serialize_user(user)}

@auth_bp.get('/me')
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return {'message': 'User not found'}, 404
    return {'user': serialize_user(user)}

@auth_bp.post('/forgot-password')
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').lower().strip()
    new_password = data.get('newPassword') or data.get('password')

    if not email or not new_password:
        return {'message': 'Email and new password are required'}, 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return {'message': f'No account found with email {email}'}, 404

    user.password_hash = hash_password(new_password)
    db.session.commit()
    return {'message': 'Password reset successful. You can now sign in with your new password.'}, 200

@auth_bp.post('/logout')
@jwt_required()
def logout():
    return {'message': 'Logged out successfully'}

