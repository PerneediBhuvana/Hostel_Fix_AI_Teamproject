from datetime import datetime
from .extensions import db

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class User(TimestampMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student') # 'student', 'faculty', 'warden', 'staff', 'admin'
    hostel_block = db.Column(db.String(30))
    floor = db.Column(db.String(20))
    room_no = db.Column(db.String(20))
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)

class Complaint(TimestampMixin, db.Model):
    __tablename__ = 'complaints'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    warden_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    status = db.Column(db.String(30), nullable=False, default='Pending') # 'Pending', 'Approved', 'Rejected', 'Assigned', 'In Progress', 'Resolved', 'Closed'
    
    block = db.Column(db.String(30))
    floor = db.Column(db.String(20))
    room_no = db.Column(db.String(20))
    
    image_url = db.Column(db.String(255))
    completion_image_url = db.Column(db.String(255))
    
    ai_category = db.Column(db.String(60))
    ai_priority = db.Column(db.String(20))
    duplicate_of_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=True)
    affected_students = db.Column(db.Integer, default=1, nullable=False)
    
    faculty_remarks = db.Column(db.Text)
    warden_remarks = db.Column(db.Text)
    staff_remarks = db.Column(db.Text)

    student = db.relationship('User', foreign_keys=[student_id], backref='raised_complaints')
    faculty = db.relationship('User', foreign_keys=[faculty_id], backref='assigned_faculty_complaints')
    warden = db.relationship('User', foreign_keys=[warden_id], backref='assigned_warden_complaints')
    staff = db.relationship('User', foreign_keys=[staff_id], backref='assigned_staff_complaints')
    feedback = db.relationship('Feedback', backref='complaint', uselist=False, cascade='all, delete-orphan')

class Notification(TimestampMixin, db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='notifications')

class Feedback(TimestampMixin, db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)

class MealRecord(TimestampMixin, db.Model):
    __tablename__ = 'meal_records'
    id = db.Column(db.Integer, primary_key=True)
    record_date = db.Column(db.Date, nullable=False, index=True)
    meal_type = db.Column(db.String(20), nullable=False, default='Lunch')  # Breakfast, Lunch, Dinner
    day_of_week = db.Column(db.String(10), nullable=False)
    weather = db.Column(db.String(20), nullable=False, default='Normal')  # Sunny, Rainy, Cloudy, Hot, Cold, Normal
    is_holiday = db.Column(db.Boolean, default=False, nullable=False)
    is_special_event = db.Column(db.Boolean, default=False, nullable=False)

    attendance_count = db.Column(db.Integer)     # students expected/present that day
    predicted_count = db.Column(db.Integer)      # model's predicted demand
    prepared_count = db.Column(db.Integer)       # meals actually cooked
    consumed_count = db.Column(db.Integer)       # meals actually eaten (ground truth)

    logged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    logged_by = db.relationship('User', foreign_keys=[logged_by_id])

    __table_args__ = (db.UniqueConstraint('record_date', 'meal_type', name='uq_meal_date_type'),)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    actor_type = db.Column(db.String(20), nullable=False, default='user')
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
