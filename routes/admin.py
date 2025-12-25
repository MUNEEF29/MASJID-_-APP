from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, User, AuditLog, PeriodLock, AppSettings, Income, Expense, Account, Transaction, JournalEntry, AIChatHistory, create_default_accounts_for_user
from routes.auth import log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/clear-data', methods=['POST'])
@login_required
def clear_data():
    confirmation = request.form.get('confirmation')
    if confirmation != 'DELETE ALL':
        flash('Data clearing cancelled. Please type the exact confirmation phrase.', 'warning')
        return redirect(url_for('admin.settings'))
    
    try:
        # We preserve the User and AppSettings
        # Delete related data for the current user
        Income.query.filter_by(user_id=current_user.id).delete()
        Expense.query.filter_by(user_id=current_user.id).delete()
        JournalEntry.query.join(Account).filter(Account.user_id == current_user.id).delete()
        Transaction.query.filter_by(user_id=current_user.id).delete()
        PeriodLock.query.filter_by(user_id=current_user.id).delete()
        AIChatHistory.query.filter_by(user_id=current_user.id).delete()
        AuditLog.query.filter_by(user_id=current_user.id).delete()
        
        # Delete accounts but recreate defaults
        Account.query.filter_by(user_id=current_user.id).delete()
        
        db.session.commit()
        
        # Recreate defaults
        create_default_accounts_for_user(current_user.id)
        
        log_action('clear_data', 'system', None, None, None, 'Cleared all transactional data')
        flash('All transaction data has been cleared. Accounts have been reset to default.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while clearing data: {str(e)}', 'danger')
        
    return redirect(url_for('admin.settings'))

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


@admin_bp.route('/settings')
@login_required
def settings():
    settings = AppSettings.get_all_settings()
    return render_template('admin/settings.html', settings=settings)


@admin_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    app_name = request.form.get('app_name', '').strip()
    app_name_arabic = request.form.get('app_name_arabic', '').strip()
    app_tagline = request.form.get('app_tagline', '').strip()
    currency_symbol = request.form.get('currency_symbol', '').strip()
    currency_code = request.form.get('currency_code', '').strip()
    
    old_settings = AppSettings.get_all_settings()
    
    if app_name:
        AppSettings.set_setting('app_name', app_name)
    if app_name_arabic:
        AppSettings.set_setting('app_name_arabic', app_name_arabic)
    if app_tagline:
        AppSettings.set_setting('app_tagline', app_tagline)
    if currency_symbol:
        AppSettings.set_setting('currency_symbol', currency_symbol)
    if currency_code:
        AppSettings.set_setting('currency_code', currency_code)
    
    new_settings = AppSettings.get_all_settings()
    log_action('update', 'app_settings', None, old_settings, new_settings, 'Updated application settings')
    
    flash('Settings updated successfully.', 'success')
    return redirect(url_for('admin.settings'))
