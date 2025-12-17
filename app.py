import os
from datetime import datetime
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User

login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.income import income_bp
    from routes.expenses import expenses_bp
    from routes.accounts import accounts_bp
    from routes.reports import reports_bp
    from routes.admin import admin_bp
    from routes.ai_assistant import ai_assistant_bp
    from google_auth import google_auth
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_assistant_bp)
    app.register_blueprint(google_auth)
    
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}
    
    @app.context_processor
    def inject_app_settings():
        from models import AppSettings
        try:
            settings = AppSettings.get_all_settings()
        except:
            settings = {}
        return {'app_settings': settings}
    
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
    
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
