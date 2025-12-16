import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import (db, Expense, Transaction, JournalEntry, Account, AuditLog,
                   ExpenseCategory, PaymentMode, FundType, VerificationStatus,
                   ApprovalStatus, PeriodLock, Role)
from routes.auth import permission_required, read_only_check, log_action

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_expense_accounts(category, payment_mode, fund_type):
    category_to_account = {
        ExpenseCategory.SALARY: '5000',
        ExpenseCategory.UTILITIES: '5010',
        ExpenseCategory.MAINTENANCE: '5020',
        ExpenseCategory.VENDOR: '5030',
        ExpenseCategory.CHARITY: '5041' if fund_type == FundType.ZAKAT else '5040',
        ExpenseCategory.ASSET: '5050',
        ExpenseCategory.OTHER: '5060',
    }
    expense_account = Account.query.filter_by(code=category_to_account.get(category, '5060')).first()
    
    if payment_mode == PaymentMode.CASH:
        asset_account = Account.query.filter_by(code='1000').first()
    else:
        if fund_type == FundType.ZAKAT:
            asset_account = Account.query.filter_by(code='1020').first()
        elif fund_type == FundType.AMANAH:
            asset_account = Account.query.filter_by(code='1030').first()
        else:
            asset_account = Account.query.filter_by(code='1010').first()
    
    return expense_account, asset_account

@expenses_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    approval_filter = request.args.get('approval', '')
    category_filter = request.args.get('category', '')
    fund_filter = request.args.get('fund', '')
    
    query = Expense.query.filter_by(is_reversed=False)
    
    if status_filter:
        query = query.filter_by(verification_status=status_filter)
    if approval_filter:
        query = query.filter_by(approval_status=approval_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if fund_filter:
        query = query.filter_by(fund_type=fund_filter)
    
    expenses = query.order_by(Expense.date.desc(), Expense.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('expenses/index.html',
        expenses=expenses,
        categories=ExpenseCategory.ALL_CATEGORIES,
        category_names=ExpenseCategory.CATEGORY_NAMES,
        funds=FundType.ALL_FUNDS,
        fund_names=FundType.FUND_NAMES,
        verification_statuses=VerificationStatus.ALL_STATUSES,
        approval_statuses=ApprovalStatus.ALL_STATUSES,
        current_status=status_filter,
        current_approval=approval_filter,
        current_category=category_filter,
        current_fund=fund_filter
    )

@expenses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@read_only_check
@permission_required('create_expense')
def create():
    if request.method == 'POST':
        try:
            date_str = request.form.get('date', '')
            category = request.form.get('category', '')
            fund_type = request.form.get('fund_type', FundType.GENERAL)
            payee = request.form.get('payee', '').strip()
            description = request.form.get('description', '').strip()
            amount_str = request.form.get('amount', '')
            payment_mode = request.form.get('payment_mode', '')
            payment_reference = request.form.get('payment_reference', '').strip()
            
            if not all([date_str, category, payee, description, amount_str, payment_mode]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('expenses/create.html',
                    categories=ExpenseCategory.ALL_CATEGORIES,
                    category_names=ExpenseCategory.CATEGORY_NAMES,
                    funds=FundType.ALL_FUNDS,
                    fund_names=FundType.FUND_NAMES,
                    payment_modes=PaymentMode.ALL_MODES,
                    payment_mode_names=PaymentMode.MODE_NAMES
                )
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return render_template('expenses/create.html',
                    categories=ExpenseCategory.ALL_CATEGORIES,
                    category_names=ExpenseCategory.CATEGORY_NAMES,
                    funds=FundType.ALL_FUNDS,
                    fund_names=FundType.FUND_NAMES,
                    payment_modes=PaymentMode.ALL_MODES,
                    payment_mode_names=PaymentMode.MODE_NAMES
                )
            
            if PeriodLock.is_period_locked(date):
                flash('Cannot create entry for a locked period.', 'danger')
                return redirect(url_for('expenses.index'))
            
            try:
                amount = Decimal(amount_str)
                if amount <= 0:
                    raise InvalidOperation()
            except InvalidOperation:
                flash('Invalid amount. Please enter a positive number.', 'danger')
                return render_template('expenses/create.html',
                    categories=ExpenseCategory.ALL_CATEGORIES,
                    category_names=ExpenseCategory.CATEGORY_NAMES,
                    funds=FundType.ALL_FUNDS,
                    fund_names=FundType.FUND_NAMES,
                    payment_modes=PaymentMode.ALL_MODES,
                    payment_mode_names=PaymentMode.MODE_NAMES
                )
            
            if category == ExpenseCategory.CHARITY and fund_type == FundType.ZAKAT:
                pass
            
            voucher_number = Expense.generate_voucher_number()
            
            expense = Expense(
                voucher_number=voucher_number,
                date=date,
                category=category,
                fund_type=fund_type,
                payee=payee,
                description=description,
                amount=amount,
                payment_mode=payment_mode,
                payment_reference=payment_reference or None,
                verification_status=VerificationStatus.VERIFIED,
                verified_by_id=current_user.id,
                verified_at=datetime.utcnow(),
                verification_remarks="Auto-verified on creation",
                approval_status=ApprovalStatus.APPROVED,
                approved_by_id=current_user.id,
                approved_at=datetime.utcnow(),
                approval_remarks="Auto-approved on creation",
                entered_by_id=current_user.id
            )
            
            if 'supporting_document' in request.files:
                file = request.files['supporting_document']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{voucher_number}_{file.filename}")
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    expense.supporting_document = filename
            
            db.session.add(expense)
            db.session.flush()
            
            expense_account, asset_account = get_expense_accounts(category, payment_mode, fund_type)
            
            transaction = Transaction(
                reference_number=f"TXN-{voucher_number}",
                transaction_type='expense',
                date=date,
                description=f"Expense: {payee} - {ExpenseCategory.CATEGORY_NAMES.get(category, category)}",
                fund_type=fund_type,
                total_amount=amount,
                created_by_id=current_user.id
            )
            db.session.add(transaction)
            db.session.flush()
            
            debit_entry = JournalEntry(
                transaction_id=transaction.id,
                account_id=expense_account.id,
                debit_amount=amount,
                credit_amount=Decimal('0'),
                date=date,
                description=f"Voucher: {voucher_number}"
            )
            
            credit_entry = JournalEntry(
                transaction_id=transaction.id,
                account_id=asset_account.id,
                debit_amount=Decimal('0'),
                credit_amount=amount,
                date=date,
                description=f"Voucher: {voucher_number}"
            )
            
            db.session.add(debit_entry)
            db.session.add(credit_entry)
            
            expense.transaction_id = transaction.id
            
            db.session.commit()
            
            log_action('create', 'expense', expense.id, None, {
                'voucher_number': voucher_number,
                'amount': str(amount),
                'category': category
            })
            
            flash(f'Expense entry created and posted to accounts. Voucher: {voucher_number}', 'success')
            return redirect(url_for('expenses.view', id=expense.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating expense entry: {str(e)}', 'danger')
    
    return render_template('expenses/create.html',
        categories=ExpenseCategory.ALL_CATEGORIES,
        category_names=ExpenseCategory.CATEGORY_NAMES,
        funds=FundType.ALL_FUNDS,
        fund_names=FundType.FUND_NAMES,
        payment_modes=PaymentMode.ALL_MODES,
        payment_mode_names=PaymentMode.MODE_NAMES
    )

@expenses_bp.route('/<int:id>')
@login_required
def view(id):
    expense = Expense.query.get_or_404(id)
    return render_template('expenses/view.html',
        expense=expense,
        category_names=ExpenseCategory.CATEGORY_NAMES,
        fund_names=FundType.FUND_NAMES,
        payment_mode_names=PaymentMode.MODE_NAMES
    )

@expenses_bp.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@expenses_bp.route('/<int:id>/verify', methods=['POST'])
@login_required
@read_only_check
@permission_required('verify_expense')
def verify(id):
    expense = Expense.query.get_or_404(id)
    
    if expense.verification_status != VerificationStatus.PENDING:
        flash('This expense entry has already been processed.', 'warning')
        return redirect(url_for('expenses.view', id=id))
    
    if expense.entered_by_id == current_user.id and current_user.role != Role.ADMIN:
        flash('You cannot verify your own entry.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    action = request.form.get('action')
    remarks = request.form.get('remarks', '').strip()
    
    if not remarks:
        flash('Verification remarks are required.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    old_status = expense.verification_status
    
    if action == 'verify':
        expense.verification_status = VerificationStatus.VERIFIED
        expense.verified_by_id = current_user.id
        expense.verified_at = datetime.utcnow()
        expense.verification_remarks = remarks
        flash('Expense entry verified. Pending approval.', 'success')
        
    elif action == 'reject':
        expense.verification_status = VerificationStatus.REJECTED
        expense.verified_by_id = current_user.id
        expense.verified_at = datetime.utcnow()
        expense.verification_remarks = remarks
        flash('Expense entry rejected.', 'warning')
    
    db.session.commit()
    
    log_action('verify', 'expense', expense.id,
              {'status': old_status},
              {'status': expense.verification_status, 'remarks': remarks})
    
    return redirect(url_for('expenses.view', id=id))

@expenses_bp.route('/<int:id>/approve', methods=['POST'])
@login_required
@read_only_check
@permission_required('approve_expense')
def approve(id):
    expense = Expense.query.get_or_404(id)
    
    if expense.verification_status != VerificationStatus.VERIFIED:
        flash('This expense must be verified before approval.', 'warning')
        return redirect(url_for('expenses.view', id=id))
    
    if expense.approval_status != ApprovalStatus.PENDING:
        flash('This expense entry has already been processed.', 'warning')
        return redirect(url_for('expenses.view', id=id))
    
    if expense.entered_by_id == current_user.id and current_user.role != Role.ADMIN:
        flash('You cannot approve your own entry.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    action = request.form.get('action')
    remarks = request.form.get('remarks', '').strip()
    
    if not remarks:
        flash('Approval remarks are required.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    old_status = expense.approval_status
    
    if action == 'approve':
        expense.approval_status = ApprovalStatus.APPROVED
        expense.approved_by_id = current_user.id
        expense.approved_at = datetime.utcnow()
        expense.approval_remarks = remarks
        
        expense_account, asset_account = get_expense_accounts(
            expense.category, expense.payment_mode, expense.fund_type
        )
        
        transaction = Transaction(
            reference_number=f"TXN-{expense.voucher_number}",
            transaction_type='expense',
            date=expense.date,
            description=f"Expense: {expense.payee} - {ExpenseCategory.CATEGORY_NAMES.get(expense.category, expense.category)}",
            fund_type=expense.fund_type,
            total_amount=expense.amount,
            created_by_id=current_user.id
        )
        db.session.add(transaction)
        db.session.flush()
        
        debit_entry = JournalEntry(
            transaction_id=transaction.id,
            account_id=expense_account.id,
            debit_amount=expense.amount,
            credit_amount=Decimal('0'),
            date=expense.date,
            description=f"Voucher: {expense.voucher_number}"
        )
        
        credit_entry = JournalEntry(
            transaction_id=transaction.id,
            account_id=asset_account.id,
            debit_amount=Decimal('0'),
            credit_amount=expense.amount,
            date=expense.date,
            description=f"Voucher: {expense.voucher_number}"
        )
        
        db.session.add(debit_entry)
        db.session.add(credit_entry)
        
        expense.transaction_id = transaction.id
        
        flash('Expense approved and posted to accounts.', 'success')
        
    elif action == 'reject':
        expense.approval_status = ApprovalStatus.REJECTED
        expense.approved_by_id = current_user.id
        expense.approved_at = datetime.utcnow()
        expense.approval_remarks = remarks
        flash('Expense entry rejected.', 'warning')
    
    db.session.commit()
    
    log_action('approve', 'expense', expense.id,
              {'status': old_status},
              {'status': expense.approval_status, 'remarks': remarks})
    
    return redirect(url_for('expenses.view', id=id))

@expenses_bp.route('/<int:id>/reverse', methods=['POST'])
@login_required
@read_only_check
@permission_required('create_expense')
def reverse(id):
    expense = Expense.query.get_or_404(id)
    
    if expense.is_reversed:
        flash('This expense entry has already been reversed.', 'warning')
        return redirect(url_for('expenses.view', id=id))
    
    if PeriodLock.is_period_locked(expense.date):
        flash('Cannot reverse entry in a locked period.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    remarks = request.form.get('remarks', '').strip()
    if not remarks:
        flash('Reversal remarks are required.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    reversal = Expense(
        voucher_number=f"REV-{expense.voucher_number}",
        date=datetime.utcnow().date(),
        category=expense.category,
        fund_type=expense.fund_type,
        payee=f"Reversal of {expense.voucher_number}",
        description=f"Reversal: {remarks}",
        amount=-expense.amount,
        payment_mode=expense.payment_mode,
        verification_status=VerificationStatus.VERIFIED,
        verified_by_id=current_user.id,
        verified_at=datetime.utcnow(),
        verification_remarks=f"Auto-verified reversal",
        approval_status=ApprovalStatus.APPROVED,
        approved_by_id=current_user.id,
        approved_at=datetime.utcnow(),
        approval_remarks=f"Auto-approved reversal: {remarks}",
        entered_by_id=current_user.id,
        reversal_of_id=expense.id
    )
    
    expense.is_reversed = True
    
    if expense.transaction_id:
        expense_account, asset_account = get_expense_accounts(
            expense.category, expense.payment_mode, expense.fund_type
        )
        
        rev_transaction = Transaction(
            reference_number=f"TXN-REV-{expense.voucher_number}",
            transaction_type='expense_reversal',
            date=datetime.utcnow().date(),
            description=f"Reversal of Expense: {expense.voucher_number}",
            fund_type=expense.fund_type,
            total_amount=expense.amount,
            created_by_id=current_user.id,
            reversal_of_id=expense.transaction_id
        )
        db.session.add(rev_transaction)
        db.session.flush()
        
        debit_entry = JournalEntry(
            transaction_id=rev_transaction.id,
            account_id=asset_account.id,
            debit_amount=expense.amount,
            credit_amount=Decimal('0'),
            date=datetime.utcnow().date(),
            description=f"Reversal of Voucher: {expense.voucher_number}"
        )
        
        credit_entry = JournalEntry(
            transaction_id=rev_transaction.id,
            account_id=expense_account.id,
            debit_amount=Decimal('0'),
            credit_amount=expense.amount,
            date=datetime.utcnow().date(),
            description=f"Reversal of Voucher: {expense.voucher_number}"
        )
        
        db.session.add(debit_entry)
        db.session.add(credit_entry)
        reversal.transaction_id = rev_transaction.id
        
        expense.transaction.is_reversed = True
    
    db.session.add(reversal)
    db.session.commit()
    
    log_action('reverse', 'expense', expense.id, None, {'reversal_id': reversal.id, 'remarks': remarks})
    
    flash(f'Expense entry reversed. Reversal voucher: {reversal.voucher_number}', 'success')
    return redirect(url_for('expenses.view', id=id))
