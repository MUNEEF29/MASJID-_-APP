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
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create the one user if they don't exist
                user = User(
                    username='admin',
                    email=email,
                    full_name='Personal Administrator',
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

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            
            if not full_name or not email:
                flash('Full name and email are required.', 'danger')
                return render_template('auth/profile.html')
            
            existing = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing:
                flash('Email is already in use by another account.', 'danger')
                return render_template('auth/profile.html')
            
            old_values = {'full_name': current_user.full_name, 'email': current_user.email}
            current_user.full_name = full_name
            current_user.email = email
            db.session.commit()
            
            log_action('update_profile', 'user', current_user.id, old_values, 
                      {'full_name': full_name, 'email': email})
            flash('Profile updated successfully.', 'success')
        
        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if current_user.google_id and not current_user.password_hash:
                if len(new_password) < 8:
                    flash('New password must be at least 8 characters long.', 'danger')
                    return render_template('auth/profile.html')
                
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return render_template('auth/profile.html')
                
                current_user.set_password(new_password)
                db.session.commit()
                
                log_action('set_password', 'user', current_user.id)
                flash('Password has been set successfully. You can now login with email/password.', 'success')
            else:
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect.', 'danger')
                    return render_template('auth/profile.html')
                
                if len(new_password) < 8:
                    flash('New password must be at least 8 characters long.', 'danger')
                    return render_template('auth/profile.html')
                
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return render_template('auth/profile.html')
                
                current_user.set_password(new_password)
                db.session.commit()
                
                log_action('change_password', 'user', current_user.id)
                flash('Password changed successfully.', 'success')
    
    return render_template('auth/profile.html')
