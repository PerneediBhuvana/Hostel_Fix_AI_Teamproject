import os
from flask import Flask, send_from_directory, make_response, request
from flask_jwt_extended import JWTManager
from .extensions import db
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(os.path.join(app.root_path, '..', app.config['UPLOAD_FOLDER']), exist_ok=True)

    @app.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, PUT, POST, DELETE, OPTIONS, PATCH'
        return response

    @app.before_request
    def handle_preflight():
        if request.method == 'OPTIONS':
            response = make_response('', 204)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '3600'
            return response
    
    db.init_app(app)
    JWTManager(app)

    from .routes.auth import auth_bp
    from .routes.complaints import complaints_bp
    from .routes.faculty import faculty_bp
    from .routes.warden import warden_bp
    from .routes.admin import admin_bp
    from .routes.staff import staff_bp
    from .routes.notifications import notifications_bp
    from .routes.food import food_bp
    from .routes.ai import ai_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(complaints_bp, url_prefix='/api/complaints')
    app.register_blueprint(faculty_bp, url_prefix='/api/faculty')
    app.register_blueprint(warden_bp, url_prefix='/api/warden')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(staff_bp, url_prefix='/api/staff')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(food_bp, url_prefix='/api/food')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')

    with app.app_context():
        from . import models
        db.create_all()

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'service': 'HOSTELFIX AI Backend Service'}

    @app.get('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(os.path.join(app.root_path, '..', app.config['UPLOAD_FOLDER']), filename)

    return app

