import random
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models import User, MealRecord
from app.utils import hash_password

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def seed_food_data():
    """Seeds ~60 days of realistic historical Lunch records so the Food Waste
    Predictor has enough data to train on right after setup. Idempotent —
    skips dates that already exist."""
    rng = random.Random(42)
    today = date.today()
    start = today - timedelta(days=60)

    # a couple of fixed "special" dates within the seeded window for variety
    holiday_offsets = {12, 33}
    event_offsets = {7, 25, 48}

    for offset in range(0, 60):
        d = start + timedelta(days=offset)
        if MealRecord.query.filter_by(record_date=d, meal_type='Lunch').first():
            continue

        weekday = d.weekday()  # 0=Mon ... 6=Sun
        is_holiday = offset in holiday_offsets
        is_special_event = offset in event_offsets
        weather = rng.choices(
            ['Normal', 'Sunny', 'Rainy', 'Cloudy', 'Hot', 'Cold'],
            weights=[35, 25, 15, 15, 5, 5]
        )[0]

        # baseline attendance: lower on weekends (students go home), normal on weekdays
        base = 300 if weekday < 5 else 190
        if is_holiday:
            base = int(base * 0.5)
        if is_special_event:
            base = int(base * 1.3)
        if weather == 'Rainy':
            base = int(base * 0.93)

        attendance = max(20, base + rng.randint(-15, 15))
        # consumption tracks attendance closely with small day-to-day noise
        consumed = max(15, attendance + rng.randint(-10, 5))
        # kitchen typically over-prepares by a margin (this margin IS the waste story)
        overprep_pct = rng.uniform(0.06, 0.16)
        prepared = int(consumed + max(10, consumed * overprep_pct))

        record = MealRecord(
            record_date=d,
            meal_type='Lunch',
            day_of_week=DAYS[weekday],
            weather=weather,
            is_holiday=is_holiday,
            is_special_event=is_special_event,
            attendance_count=attendance,
            prepared_count=prepared,
            consumed_count=consumed,
        )
        db.session.add(record)

    db.session.commit()

HISTORY_TEMPLATES = {
    'Electricity': ['Fan not working in room {r}', 'Tube light flickering in corridor', 'Switch board sparking in room {r}', 'Socket not giving power in room {r}'],
    'Plumbing': ['Tap leaking in washroom', 'Drain blocked near room {r}', 'Flush not working in washroom', 'Pipe leaking in bathroom'],
    'Water': ['No drinking water on the floor', 'Low water pressure in the morning', 'Water cooler not working', 'Dirty water from taps'],
    'Internet': ['WiFi not working in room {r}', 'Internet very slow in the evening', 'Router down on this floor', 'WiFi keeps disconnecting'],
    'Food': ['Stale food served at dinner', 'Undercooked rice in lunch', 'Breakfast was cold and tasteless', 'Insect found in mess curry'],
    'Cleaning': ['Washroom not cleaned for days', 'Garbage not cleared in corridor', 'Dustbin overflowing near stairs', 'Cockroaches in room {r}'],
    'Furniture': ['Study chair broken in room {r}', 'Cupboard door loose', 'Bed frame broken', 'Study table leg loose'],
    'Security': ['Guard absent at night', 'CCTV not working in corridor', 'Room lock broken in room {r}', 'Unknown person near the gate'],
}
BASE_HOURS = {'Electricity': 20, 'Plumbing': 26, 'Water': 18, 'Internet': 30, 'Food': 12, 'Cleaning': 8, 'Furniture': 72, 'Security': 10}
PRIORITY_FACTOR = {'Urgent': 0.4, 'High': 0.7, 'Medium': 1.0, 'Low': 1.6}


def seed_complaint_history():
    """Seeds ~140 demo complaints over the last 70 days, with two deliberate spikes
    (Internet in Block B, Water in Block A) in the last 2 weeks, so the AI Insights
    dashboard has something real to detect. Idempotent."""
    from datetime import datetime
    from app.models import Complaint, Feedback
    if User.query.filter_by(email='resident1@college.edu').first():
        return
    rng = random.Random(11)
    residents = []
    for i, block in enumerate(['Block A', 'Block A', 'Block B', 'Block B', 'Block C'], start=1):
        u = User(email=f'resident{i}@college.edu', name=f'Demo Resident {i}', role='student',
                 hostel_block=block, floor=str(1 + i % 3), room_no=str(100 + i * 7), phone='9000000000')
        u.password_hash = hash_password('Resident@2026')
        db.session.add(u)
        residents.append(u)
    db.session.flush()
    now = datetime.utcnow()
    cats = list(HISTORY_TEMPLATES)

    def add(category, block, created):
        resident = rng.choice([r for r in residents if r.hostel_block == block])
        title = rng.choice(HISTORY_TEMPLATES[category]).format(r=rng.randint(101, 320))
        priority = rng.choices(['Low', 'Medium', 'High', 'Urgent'], weights=[15, 50, 28, 7])[0]
        age_h = (now - created).total_seconds() / 3600
        hours = max(1.0, BASE_HOURS[category] * PRIORITY_FACTOR[priority] * rng.uniform(0.6, 1.5))
        if age_h > hours + 6:
            status = rng.choices(['Resolved', 'Closed'], weights=[55, 45])[0]
            updated = created + timedelta(hours=hours)
        else:
            status = rng.choice(['Pending', 'Approved', 'Assigned', 'In Progress'])
            updated = created
        c = Complaint(student_id=resident.id, title=title, description=f'{title}. Please fix this soon.',
                      category=category, priority=priority, status=status, block=block,
                      floor=resident.floor, room_no=resident.room_no, ai_category=category, ai_priority=priority,
                      created_at=created, updated_at=updated)
        db.session.add(c)
        db.session.flush()
        if status in ('Resolved', 'Closed') and rng.random() < 0.6:
            bad = category == 'Furniture'
            db.session.add(Feedback(complaint_id=c.id, student_id=resident.id,
                                    rating=rng.choice([2, 3, 3, 4]) if bad else rng.choice([3, 4, 4, 5, 5]),
                                    created_at=updated, updated_at=updated))

    # baseline: steady background volume with a mild upward drift
    for day in range(70, 0, -1):
        for _ in range(rng.choice([0, 1, 1, 2]) if day > 35 else rng.choice([1, 1, 2])):
            created = now - timedelta(days=day, hours=rng.randint(0, 20))
            add(rng.choice(cats), rng.choice(['Block A', 'Block B', 'Block C']), created)
    # spikes in the last 14 days
    for _ in range(9):
        add('Internet', 'Block B', now - timedelta(days=rng.randint(0, 12), hours=rng.randint(0, 20)))
    for _ in range(6):
        add('Water', 'Block A', now - timedelta(days=rng.randint(0, 12), hours=rng.randint(0, 20)))
    db.session.commit()


def seed_data():
    app = create_app()
    with app.app_context():
        # Admin
        admin = User.query.filter_by(email='admin@college.edu').first()
        if not admin:
            admin = User(email='admin@college.edu', name='HOSTELFIX Admin')
            db.session.add(admin)
        admin.password_hash = hash_password('Admin@12345')
        admin.role = 'admin'
        admin.phone = '9999999999'

        # Faculty (Floor Coordinators)
        faculties = [
            ('faculty1@college.edu', 'Dr. Smith', 'Block A', '1', 'Computer Science', 'Smith@2026'),
            ('faculty2@college.edu', 'Dr. Johnson', 'Block A', '2', 'Electronics', 'Johnson@2026'),
            ('faculty3@college.edu', 'Dr. Williams', 'Block B', '1', 'Mechanical', 'Williams@2026')
        ]
        for email, name, block, floor, dept, password in faculties:
            faculty = User.query.filter_by(email=email).first()
            if not faculty:
                faculty = User(email=email, name=name)
                db.session.add(faculty)
            faculty.password_hash = hash_password(password)
            faculty.role = 'faculty'
            faculty.hostel_block = block
            faculty.floor = floor
            faculty.department = dept
            faculty.phone = '9876543201'

        # Wardens
        wardens = [
            ('warden1@college.edu', 'Warden Block A', 'Block A', 'WardenA@2026'),
            ('warden2@college.edu', 'Warden Block B', 'Block B', 'WardenB@2026')
        ]
        for email, name, block, password in wardens:
            warden = User.query.filter_by(email=email).first()
            if not warden:
                warden = User(email=email, name=name)
                db.session.add(warden)
            warden.password_hash = hash_password(password)
            warden.role = 'warden'
            warden.hostel_block = block
            warden.phone = '9876543210'

        # Maintenance Staff
        staff_members = [
            ('staff1@college.edu', 'Rajesh Kumar', 'Plumbing', 'Staff1@2026'),
            ('staff2@college.edu', 'Suresh Verma', 'Electrical', 'Staff2@2026'),
            ('staff3@college.edu', 'Ramesh Gupta', 'General', 'Staff3@2026')
        ]
        for email, name, dept, password in staff_members:
            staff = User.query.filter_by(email=email).first()
            if not staff:
                staff = User(email=email, name=name)
                db.session.add(staff)
            staff.password_hash = hash_password(password)
            staff.role = 'staff'
            staff.department = dept
            staff.phone = '9876543220'

        # Demo Student
        student = User.query.filter_by(email='student@college.edu').first()
        if not student:
            student = User(email='student@college.edu', name='Rahul Verma')
            db.session.add(student)
        student.password_hash = hash_password('Student@12345')
        student.role = 'student'
        student.hostel_block = 'Block A'
        student.floor = '1'
        student.room_no = '101'
        student.department = 'Computer Science'
        student.phone = '9876543230'

        db.session.commit()
        seed_food_data()
        seed_complaint_history()
        print('Seeded HOSTELFIX AI system accounts successfully:')
        print(' - Admin: admin@college.edu / Admin@12345')
        print(' - Faculty Coordinators:')
        print('     faculty1@college.edu / Smith@2026')
        print('     faculty2@college.edu / Johnson@2026')
        print('     faculty3@college.edu / Williams@2026')
        print(' - Wardens:')
        print('     warden1@college.edu / WardenA@2026')
        print('     warden2@college.edu / WardenB@2026')
        print(' - Staff:')
        print('     staff1@college.edu / Staff1@2026')
        print('     staff2@college.edu / Staff2@2026')
        print('     staff3@college.edu / Staff3@2026')
        print(' - Student: student@college.edu / Student@12345')
        print(' - Demo residents (history data): resident1..5@college.edu / Resident@2026')


if __name__ == '__main__':
    seed_data()
