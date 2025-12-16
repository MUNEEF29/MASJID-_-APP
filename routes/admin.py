from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, AuditLog, PeriodLock, Role
from routes.auth import role_required, log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@role_required(Role.ADMIN)
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/index.html', users=users, roles=Role.ALL_ROLES)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required(Role.ADMIN)
def create_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', Role.ACCOUNTANT)
        
        if not all([username, email, full_name, password]):
            flash('All fields are required.', 'danger')
            return render_template('admin/create_user.html', roles=Role.ALL_ROLES)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('admin/create_user.html', roles=Role.ALL_ROLES)
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('admin/create_user.html', roles=Role.ALL_ROLES)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return render_template('admin/create_user.html', roles=Role.ALL_ROLES)
        
        if role not in Role.ALL_ROLES:
            flash('Invalid role selected.', 'danger')
            return render_template('admin/create_user.html', roles=Role.ALL_ROLES)
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_action('create', 'user', user.id, None, {
            'username': username,
            'email': email,
            'role': role
        })
        
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('admin.index'))
    
    return render_template('admin/create_user.html', roles=Role.ALL_ROLES)

@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(Role.ADMIN)
def edit_user(id):
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update':
            email = request.form.get('email', '').strip()
            full_name = request.form.get('full_name', '').strip()
            role = request.form.get('role', user.role)
            is_active = request.form.get('is_active') == 'on'
            
            if not all([email, full_name]):
                flash('Email and full name are required.', 'danger')
                return render_template('admin/edit_user.html', user=user, roles=Role.ALL_ROLES)
            
            existing = User.query.filter(User.email == email, User.id != user.id).first()
            if existing:
                flash('Email already in use.', 'danger')
                return render_template('admin/edit_user.html', user=user, roles=Role.ALL_ROLES)
            
            old_values = {
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active
            }
            
            user.email = email
            user.full_name = full_name
            user.role = role
            user.is_active = is_active
            
            db.session.commit()
            
            log_action('update', 'user', user.id, old_values, {
                'email': email,
                'full_name': full_name,
                'role': role,
                'is_active': is_active
            })
            
            flash('User updated successfully.', 'success')
            
        elif action == 'reset_password':
            new_password = request.form.get('new_password', '')
            
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long.', 'danger')
                return render_template('admin/edit_user.html', user=user, roles=Role.ALL_ROLES)
            
            user.set_password(new_password)
            db.session.commit()
            
            log_action('reset_password', 'user', user.id)
            
            flash('Password reset successfully.', 'success')
        
        return redirect(url_for('admin.edit_user', id=id))
    
    return render_template('admin/edit_user.html', user=user, roles=Role.ALL_ROLES)

@admin_bp.route('/audit-log')
@login_required
@role_required(Role.ADMIN, Role.AUDITOR)
def audit_log():
    page = request.args.get('page', 1, type=int)
    user_id = request.args.get('user_id', type=int)
    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity', '')
    
    query = AuditLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action_filter:
        query = query.filter_by(action=action_filter)
    if entity_filter:
        query = query.filter_by(entity_type=entity_filter)
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    users = User.query.order_by(User.full_name).all()
    
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions]
    
    entities = db.session.query(AuditLog.entity_type).distinct().all()
    entities = [e[0] for e in entities]
    
    return render_template('admin/audit_log.html',
        logs=logs,
        users=users,
        actions=actions,
        entities=entities,
        current_user_id=user_id,
        current_action=action_filter,
        current_entity=entity_filter
    )

@admin_bp.route('/period-locks')
@login_required
@role_required(Role.ADMIN, Role.TREASURER)
def period_locks():
    locks = PeriodLock.query.order_by(PeriodLock.year.desc(), PeriodLock.month.desc()).all()
    return render_template('admin/period_locks.html', locks=locks)

@admin_bp.route('/period-locks/create', methods=['POST'])
@login_required
@role_required(Role.ADMIN, Role.TREASURER)
def create_period_lock():
    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)
    remarks = request.form.get('remarks', '').strip()
    
    if not year or not month or month < 1 or month > 12:
        flash('Invalid year or month.', 'danger')
        return redirect(url_for('admin.period_locks'))
    
    existing = PeriodLock.query.filter_by(year=year, month=month).first()
    if existing:
        flash('This period is already locked.', 'warning')
        return redirect(url_for('admin.period_locks'))
    
    lock = PeriodLock(
        year=year,
        month=month,
        locked_by_id=current_user.id,
        remarks=remarks or None
    )
    
    db.session.add(lock)
    db.session.commit()
    
    log_action('create', 'period_lock', lock.id, None, {
        'year': year,
        'month': month
    })
    
    flash(f'Period {month}/{year} locked successfully.', 'success')
    return redirect(url_for('admin.period_locks'))
