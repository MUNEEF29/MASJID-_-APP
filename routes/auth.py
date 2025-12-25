from datetime import datetime
from functools import wraps
import json
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, AuditLog, create_default_accounts_for_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def log_action(action, entity_type, entity_id=None, old_values=None, new_values=None, remarks=None):
    if current_user.is_authenticated:
        from models import AuditLog
        log = AuditLog(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            remarks=remarks,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:255] if request.user_agent.string else None
        )
        db.session.add(log)
        db.session.commit()

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def read_only_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Hardcoded for personal use as requested
        # For security, the user should change this in the source or via secrets
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@admin.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if email == admin_email and password == admin_password:
            from models import User, create_default_accounts_for_user
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create the one user if they don't exist
                user = User(
                    username='admin',
                    email=email,
                    full_name='Mr. Shakir',
                    is_active=True
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                create_default_accounts_for_user(user.id)
            
            login_user(user, remember=remember == 'true' or remember is True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_action('login', 'user', user.id)
            
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid access credentials.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    flash('Registration is disabled for this personal application.', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    log_action('logout', 'user', current_user.id)
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))
