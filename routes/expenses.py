import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import (db, Expense, Transaction, JournalEntry, Account, AuditLog,
                   ExpenseCategory, PaymentMode, FundType, VerificationStatus,
                   ApprovalStatus, PeriodLock)
from routes.auth import permission_required, read_only_check, log_action

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_expense_accounts(user_id, category, payment_mode, fund_type):
    category_to_account = {
        ExpenseCategory.ZAKAT_DISBURSEMENT: '5000',
        ExpenseCategory.SADAQAH_DISBURSEMENT: '5010',
        ExpenseCategory.SALARIES: '5020',
        ExpenseCategory.UTILITIES: '5030',
        ExpenseCategory.MAINTENANCE: '5040',
        ExpenseCategory.CONSTRUCTION: '5050',
        ExpenseCategory.EDUCATION: '5060',
        ExpenseCategory.EVENTS: '5070',
        ExpenseCategory.FOOD: '5080',
        ExpenseCategory.SUPPLIES: '5090',
        ExpenseCategory.OTHER: '5100',
        ExpenseCategory.POOR_NEEDY: '5010',
        ExpenseCategory.FUNERAL: '5070',
    }
    expense_account = Account.query.filter_by(
        user_id=user_id,
        code=category_to_account.get(category, '5100')
    ).first()
    
    if payment_mode == PaymentMode.CASH:
        asset_account = Account.query.filter_by(user_id=user_id, code='1000').first()
    else:
        if fund_type == FundType.ZAKAT:
            asset_account = Account.query.filter_by(user_id=user_id, code='1020').first()
        elif fund_type == FundType.SADAQAH:
            asset_account = Account.query.filter_by(user_id=user_id, code='1030').first()
        elif fund_type == FundType.AMANAH:
            asset_account = Account.query.filter_by(user_id=user_id, code='1040').first()
        elif fund_type == FundType.LILLAH:
            asset_account = Account.query.filter_by(user_id=user_id, code='1050').first()
        else:
            asset_account = Account.query.filter_by(user_id=user_id, code='1010').first()
    
    return expense_account, asset_account

@expenses_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    approval_filter = request.args.get('approval', '')
    category_filter = request.args.get('category', '')
    fund_filter = request.args.get('fund', '')
    
    query = Expense.query.filter_by(user_id=current_user.id, is_reversed=False)
    
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
            
            if PeriodLock.is_period_locked(current_user.id, date):
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
            
            voucher_number = Expense.generate_voucher_number(current_user.id)
            
            expense = Expense(
                user_id=current_user.id,
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
            
            expense_account, asset_account = get_expense_accounts(current_user.id, category, payment_mode, fund_type)
            
            if expense_account and asset_account:
                transaction = Transaction(
                    user_id=current_user.id,
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
            
            flash(f'Expense entry created successfully. Voucher: {voucher_number}', 'success')
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
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
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

@expenses_bp.route('/<int:id>/reverse', methods=['POST'])
@login_required
@read_only_check
@permission_required('create_expense')
def reverse(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if expense.is_reversed:
        flash('This expense entry has already been reversed.', 'warning')
        return redirect(url_for('expenses.view', id=id))
    
    if PeriodLock.is_period_locked(current_user.id, expense.date):
        flash('Cannot reverse entry in a locked period.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    remarks = request.form.get('remarks', '').strip()
    if not remarks:
        flash('Reversal remarks are required.', 'danger')
        return redirect(url_for('expenses.view', id=id))
    
    reversal = Expense(
        user_id=current_user.id,
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
            current_user.id, expense.category, expense.payment_mode, expense.fund_type
        )
        
        if expense_account and asset_account:
            rev_transaction = Transaction(
                user_id=current_user.id,
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
