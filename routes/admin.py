from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, AuditLog, PeriodLock
from routes.auth import log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/audit-log')
@login_required
def audit_log():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity', '')
    
    query = AuditLog.query.filter_by(user_id=current_user.id)
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    if entity_filter:
        query = query.filter_by(entity_type=entity_filter)
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    actions = db.session.query(AuditLog.action).filter_by(user_id=current_user.id).distinct().all()
    actions = [a[0] for a in actions]
    
    entities = db.session.query(AuditLog.entity_type).filter_by(user_id=current_user.id).distinct().all()
    entities = [e[0] for e in entities]
    
    return render_template('admin/audit_log.html',
        logs=logs,
        actions=actions,
        entities=entities,
        current_action=action_filter,
        current_entity=entity_filter
    )

@admin_bp.route('/period-locks')
@login_required
def period_locks():
    locks = PeriodLock.query.filter_by(user_id=current_user.id).order_by(PeriodLock.year.desc(), PeriodLock.month.desc()).all()
    return render_template('admin/period_locks.html', locks=locks)

@admin_bp.route('/period-locks/create', methods=['POST'])
@login_required
def create_period_lock():
    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)
    remarks = request.form.get('remarks', '').strip()
    
    if not year or not month or month < 1 or month > 12:
        flash('Invalid year or month.', 'danger')
        return redirect(url_for('admin.period_locks'))
    
    existing = PeriodLock.query.filter_by(user_id=current_user.id, year=year, month=month).first()
    if existing:
        flash('This period is already locked.', 'warning')
        return redirect(url_for('admin.period_locks'))
    
    lock = PeriodLock(
        user_id=current_user.id,
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

@admin_bp.route('/period-locks/<int:id>/delete', methods=['POST'])
@login_required
def delete_period_lock(id):
    lock = PeriodLock.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    year, month = lock.year, lock.month
    db.session.delete(lock)
    db.session.commit()
    
    log_action('delete', 'period_lock', id, {'year': year, 'month': month}, None)
    
    flash(f'Period {month}/{year} unlocked successfully.', 'success')
    return redirect(url_for('admin.period_locks'))
