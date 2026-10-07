CREATE DATABASE IF NOT EXISTS hostel_complaints CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hostel_complaints;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    hostel_block VARCHAR(30),
    floor VARCHAR(20),
    room_no VARCHAR(20),
    department VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    faculty_id INT,
    warden_id INT,
    staff_id INT,
    title VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(60) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    block VARCHAR(30),
    floor VARCHAR(20),
    room_no VARCHAR(20),
    image_url VARCHAR(255),
    completion_image_url VARCHAR(255),
    ai_category VARCHAR(60),
    ai_priority VARCHAR(20),
    duplicate_of_id INT,
    affected_students INT NOT NULL DEFAULT 1,
    faculty_remarks TEXT,
    warden_remarks TEXT,
    staff_remarks TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_complaint_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_complaint_faculty FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_complaint_warden FOREIGN KEY (warden_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_complaint_staff FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_duplicate_complaint FOREIGN KEY (duplicate_of_id) REFERENCES complaints(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message VARCHAR(255) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL UNIQUE,
    student_id INT NOT NULL,
    rating INT NOT NULL,
    comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    actor_id INT,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'user',
    action VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
);

INSERT IGNORE INTO categories (name) VALUES ('Water'), ('Electricity'), ('WiFi'), ('Food'), ('Cleaning'), ('Plumbing'), ('Furniture'), ('Others');
