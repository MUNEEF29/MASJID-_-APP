from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import (db, Income, Transaction, JournalEntry, Account, AuditLog,
                   IncomeCategory, PaymentMode, FundType, VerificationStatus,
                   PeriodLock, Role)
from routes.auth import permission_required, read_only_check, log_action

income_bp = Blueprint('income', __name__, url_prefix='/income')

def get_income_accounts(category, payment_mode):
    fund_type = IncomeCategory.FUND_MAPPING.get(category, FundType.GENERAL)
    
    category_to_account = {
        IncomeCategory.DONATION: '4000',
        IncomeCategory.ZAKAT: '4010',
        IncomeCategory.SADAQAH: '4020',
        IncomeCategory.FITRAH: '4030',
        IncomeCategory.SPECIAL_COLLECTION: '4040',
        IncomeCategory.RENTAL: '4050',
        IncomeCategory.OTHER: '4060',
    }
    income_account = Account.query.filter_by(code=category_to_account.get(category, '4060')).first()
    
    if payment_mode == PaymentMode.CASH:
        asset_account = Account.query.filter_by(code='1000').first()
    else:
        if fund_type == FundType.ZAKAT:
            asset_account = Account.query.filter_by(code='1020').first()
        elif fund_type == FundType.AMANAH:
            asset_account = Account.query.filter_by(code='1030').first()
        else:
            asset_account = Account.query.filter_by(code='1010').first()
    
    return income_account, asset_account

@income_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    fund_filter = request.args.get('fund', '')
    
    query = Income.query.filter_by(is_reversed=False)
    
    if status_filter:
        query = query.filter_by(verification_status=status_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if fund_filter:
        query = query.filter_by(fund_type=fund_filter)
    
    incomes = query.order_by(Income.date.desc(), Income.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('income/index.html',
        incomes=incomes,
        categories=IncomeCategory.ALL_CATEGORIES,
        category_names=IncomeCategory.CATEGORY_NAMES,
        funds=FundType.ALL_FUNDS,
        fund_names=FundType.FUND_NAMES,
        statuses=VerificationStatus.ALL_STATUSES,
        current_status=status_filter,
        current_category=category_filter,
        current_fund=fund_filter
    )

@income_bp.route('/create', methods=['GET', 'POST'])
@login_required
@read_only_check
@permission_required('create_income')
def create():
    if request.method == 'POST':
        try:
            date_str = request.form.get('date', '')
            time_str = request.form.get('time', '')
            category = request.form.get('category', '')
            source = request.form.get('source', '').strip()
            donor_name = request.form.get('donor_name', '').strip()
            donor_contact = request.form.get('donor_contact', '').strip()
            payment_mode = request.form.get('payment_mode', '')
            payment_reference = request.form.get('payment_reference', '').strip()
            amount_str = request.form.get('amount', '')
            description = request.form.get('description', '').strip()
            
            if not all([date_str, time_str, category, source, payment_mode, amount_str]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('income/create.html',
                    categories=IncomeCategory.ALL_CATEGORIES,
                    category_names=IncomeCategory.CATEGORY_NAMES,
                    payment_modes=PaymentMode.ALL_MODES,
                    payment_mode_names=PaymentMode.MODE_NAMES
                )
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                time = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid date or time format.', 'danger')
                return render_template('income/create.html',
                    categories=IncomeCategory.ALL_CATEGORIES,
                    category_names=IncomeCategory.CATEGORY_NAMES,
                    payment_modes=PaymentMode.ALL_MODES,
                    payment_mode_names=PaymentMode.MODE_NAMES
                )
            
            if PeriodLock.is_period_locked(date):
                flash('Cannot create entry for a locked period.', 'danger')
                return redirect(url_for('income.index'))
            
            try:
                amount = Decimal(amount_str)
                if amount <= 0:
                    raise InvalidOperation()
            except InvalidOperation:
                flash('Invalid amount. Please enter a positive number.', 'danger')
                return render_template('income/create.html',
                    categories=IncomeCategory.ALL_CATEGORIES,
                    category_names=IncomeCategory.CATEGORY_NAMES,
                    payment_modes=PaymentMode.ALL_MODES,
                    payment_mode_names=PaymentMode.MODE_NAMES
                )
            
            fund_type = IncomeCategory.FUND_MAPPING.get(category, FundType.GENERAL)
            receipt_number = Income.generate_receipt_number()
            
            income = Income(
                receipt_number=receipt_number,
                date=date,
                time=time,
                category=category,
                fund_type=fund_type,
                source=source,
                donor_name=donor_name or None,
                donor_contact=donor_contact or None,
                payment_mode=payment_mode,
                payment_reference=payment_reference or None,
                amount=amount,
                description=description or None,
                verification_status=VerificationStatus.VERIFIED,
                verified_by_id=current_user.id,
                verified_at=datetime.utcnow(),
                verification_remarks="Auto-verified on creation",
                entered_by_id=current_user.id
            )
            
            db.session.add(income)
            db.session.flush()
            
            income_account, asset_account = get_income_accounts(category, payment_mode)
            
            transaction = Transaction(
                reference_number=f"TXN-{receipt_number}",
                transaction_type='income',
                date=date,
                description=f"Income: {source} - {IncomeCategory.CATEGORY_NAMES.get(category, category)}",
                fund_type=fund_type,
                total_amount=amount,
                created_by_id=current_user.id
            )
            db.session.add(transaction)
            db.session.flush()
            
            debit_entry = JournalEntry(
                transaction_id=transaction.id,
                account_id=asset_account.id,
                debit_amount=amount,
                credit_amount=Decimal('0'),
                date=date,
                description=f"Receipt: {receipt_number}"
            )
            
            credit_entry = JournalEntry(
                transaction_id=transaction.id,
                account_id=income_account.id,
                debit_amount=Decimal('0'),
                credit_amount=amount,
                date=date,
                description=f"Receipt: {receipt_number}"
            )
            
            db.session.add(debit_entry)
            db.session.add(credit_entry)
            
            income.transaction_id = transaction.id
            
            db.session.commit()
            
            log_action('create', 'income', income.id, None, {
                'receipt_number': receipt_number,
                'amount': str(amount),
                'category': category
            })
            
            flash(f'Income entry created and posted to accounts. Receipt: {receipt_number}', 'success')
            return redirect(url_for('income.view', id=income.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating income entry: {str(e)}', 'danger')
    
    return render_template('income/create.html',
        categories=IncomeCategory.ALL_CATEGORIES,
        category_names=IncomeCategory.CATEGORY_NAMES,
        payment_modes=PaymentMode.ALL_MODES,
        payment_mode_names=PaymentMode.MODE_NAMES
    )

@income_bp.route('/<int:id>')
@login_required
def view(id):
    income = Income.query.get_or_404(id)
    return render_template('income/view.html',
        income=income,
        category_names=IncomeCategory.CATEGORY_NAMES,
        fund_names=FundType.FUND_NAMES,
        payment_mode_names=PaymentMode.MODE_NAMES
    )

@income_bp.route('/<int:id>/verify', methods=['POST'])
@login_required
@read_only_check
@permission_required('verify_income')
def verify(id):
    income = Income.query.get_or_404(id)
    
    if income.verification_status != VerificationStatus.PENDING:
        flash('This income entry has already been processed.', 'warning')
        return redirect(url_for('income.view', id=id))
    
    if income.entered_by_id == current_user.id and current_user.role != Role.ADMIN:
        flash('You cannot verify your own entry.', 'danger')
        return redirect(url_for('income.view', id=id))
    
    action = request.form.get('action')
    remarks = request.form.get('remarks', '').strip()
    
    if not remarks:
        flash('Verification remarks are required.', 'danger')
        return redirect(url_for('income.view', id=id))
    
    old_status = income.verification_status
    
    if action == 'verify':
        income.verification_status = VerificationStatus.VERIFIED
        income.verified_by_id = current_user.id
        income.verified_at = datetime.utcnow()
        income.verification_remarks = remarks
        
        income_account, asset_account = get_income_accounts(income.category, income.payment_mode)
        
        transaction = Transaction(
            reference_number=f"TXN-{income.receipt_number}",
            transaction_type='income',
            date=income.date,
            description=f"Income: {income.source} - {IncomeCategory.CATEGORY_NAMES.get(income.category, income.category)}",
            fund_type=income.fund_type,
            total_amount=income.amount,
            created_by_id=current_user.id
        )
        db.session.add(transaction)
        db.session.flush()
        
        debit_entry = JournalEntry(
            transaction_id=transaction.id,
            account_id=asset_account.id,
            debit_amount=income.amount,
            credit_amount=Decimal('0'),
            date=income.date,
            description=f"Receipt: {income.receipt_number}"
        )
        
        credit_entry = JournalEntry(
            transaction_id=transaction.id,
            account_id=income_account.id,
            debit_amount=Decimal('0'),
            credit_amount=income.amount,
            date=income.date,
            description=f"Receipt: {income.receipt_number}"
        )
        
        db.session.add(debit_entry)
        db.session.add(credit_entry)
        
        income.transaction_id = transaction.id
        
        flash('Income entry verified and posted to accounts.', 'success')
        
    elif action == 'reject':
        income.verification_status = VerificationStatus.REJECTED
        income.verified_by_id = current_user.id
        income.verified_at = datetime.utcnow()
        income.verification_remarks = remarks
        
        flash('Income entry rejected.', 'warning')
    
    db.session.commit()
    
    log_action('verify', 'income', income.id, 
              {'status': old_status}, 
              {'status': income.verification_status, 'remarks': remarks})
    
    return redirect(url_for('income.view', id=id))

@income_bp.route('/<int:id>/reverse', methods=['POST'])
@login_required
@read_only_check
@permission_required('create_income')
def reverse(id):
    income = Income.query.get_or_404(id)
    
    if income.is_reversed:
        flash('This income entry has already been reversed.', 'warning')
        return redirect(url_for('income.view', id=id))
    
    if PeriodLock.is_period_locked(income.date):
        flash('Cannot reverse entry in a locked period.', 'danger')
        return redirect(url_for('income.view', id=id))
    
    remarks = request.form.get('remarks', '').strip()
    if not remarks:
        flash('Reversal remarks are required.', 'danger')
        return redirect(url_for('income.view', id=id))
    
    reversal = Income(
        receipt_number=f"REV-{income.receipt_number}",
        date=datetime.utcnow().date(),
        time=datetime.utcnow().time(),
        category=income.category,
        fund_type=income.fund_type,
        source=f"Reversal of {income.receipt_number}",
        donor_name=income.donor_name,
        payment_mode=income.payment_mode,
        amount=-income.amount,
        description=f"Reversal: {remarks}",
        verification_status=VerificationStatus.VERIFIED,
        verified_by_id=current_user.id,
        verified_at=datetime.utcnow(),
        verification_remarks=f"Auto-verified reversal: {remarks}",
        entered_by_id=current_user.id,
        reversal_of_id=income.id
    )
    
    income.is_reversed = True
    
    if income.transaction_id:
        income_account, asset_account = get_income_accounts(income.category, income.payment_mode)
        
        rev_transaction = Transaction(
            reference_number=f"TXN-REV-{income.receipt_number}",
            transaction_type='income_reversal',
            date=datetime.utcnow().date(),
            description=f"Reversal of Income: {income.receipt_number}",
            fund_type=income.fund_type,
            total_amount=income.amount,
            created_by_id=current_user.id,
            reversal_of_id=income.transaction_id
        )
        db.session.add(rev_transaction)
        db.session.flush()
        
        debit_entry = JournalEntry(
            transaction_id=rev_transaction.id,
            account_id=income_account.id,
            debit_amount=income.amount,
            credit_amount=Decimal('0'),
            date=datetime.utcnow().date(),
            description=f"Reversal of Receipt: {income.receipt_number}"
        )
        
        credit_entry = JournalEntry(
            transaction_id=rev_transaction.id,
            account_id=asset_account.id,
            debit_amount=Decimal('0'),
            credit_amount=income.amount,
            date=datetime.utcnow().date(),
            description=f"Reversal of Receipt: {income.receipt_number}"
        )
        
        db.session.add(debit_entry)
        db.session.add(credit_entry)
        reversal.transaction_id = rev_transaction.id
        
        income.transaction.is_reversed = True
    
    db.session.add(reversal)
    db.session.commit()
    
    log_action('reverse', 'income', income.id, None, {'reversal_id': reversal.id, 'remarks': remarks})
    
    flash(f'Income entry reversed. Reversal receipt: {reversal.receipt_number}', 'success')
    return redirect(url_for('income.view', id=id))
