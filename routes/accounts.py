from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import (db, Account, JournalEntry, AccountType, FundType)
from routes.auth import permission_required, read_only_check, log_action

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/')
@login_required
def index():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).order_by(Account.code).all()
    
    grouped_accounts = {}
    for acc_type in AccountType.ALL_TYPES:
        grouped_accounts[acc_type] = [a for a in accounts if a.account_type == acc_type]
    
    return render_template('accounts/index.html',
        grouped_accounts=grouped_accounts,
        account_types=AccountType.ALL_TYPES,
        fund_names=FundType.FUND_NAMES
    )

@accounts_bp.route('/<int:id>/ledger')
@login_required
def ledger(id):
    account = Account.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = JournalEntry.query.filter_by(account_id=account.id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(JournalEntry.date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(JournalEntry.date <= end)
        except ValueError:
            pass
    
    entries = query.order_by(JournalEntry.date.desc(), JournalEntry.id.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    opening_balance = Decimal('0')
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            opening_balance = account.get_balance(end_date=start)
        except ValueError:
            pass
    
    running_balance = opening_balance
    entries_with_balance = []
    for entry in entries.items:
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            running_balance += (entry.debit_amount or Decimal('0')) - (entry.credit_amount or Decimal('0'))
        else:
            running_balance += (entry.credit_amount or Decimal('0')) - (entry.debit_amount or Decimal('0'))
        entries_with_balance.append((entry, running_balance))
    
    return render_template('accounts/ledger.html',
        account=account,
        entries=entries,
        entries_with_balance=entries_with_balance,
        opening_balance=opening_balance,
        current_balance=account.get_balance(),
        start_date=start_date,
        end_date=end_date,
        fund_names=FundType.FUND_NAMES
    )

@accounts_bp.route('/trial-balance')
@login_required
def trial_balance():
    as_of_date = request.args.get('as_of_date', '')
    
    end_date = None
    if as_of_date:
        try:
            end_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).order_by(Account.code).all()
    
    trial_data = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    
    for account in accounts:
        balance = account.get_balance(end_date=end_date)
        
        if balance != 0:
            if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                if balance >= 0:
                    debit = balance
                    credit = Decimal('0')
                else:
                    debit = Decimal('0')
                    credit = abs(balance)
            else:
                if balance >= 0:
                    debit = Decimal('0')
                    credit = balance
                else:
                    debit = abs(balance)
                    credit = Decimal('0')
            
            trial_data.append({
                'account': account,
                'debit': debit,
                'credit': credit
            })
            total_debit += debit
            total_credit += credit
    
    return render_template('accounts/trial_balance.html',
        trial_data=trial_data,
        total_debit=total_debit,
        total_credit=total_credit,
        as_of_date=as_of_date,
        is_balanced=abs(total_debit - total_credit) < Decimal('0.01'),
        fund_names=FundType.FUND_NAMES
    )

@accounts_bp.route('/income-expenditure')
@login_required
def income_expenditure():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    fund_filter = request.args.get('fund', '')
    
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    income_accounts = Account.query.filter_by(
        user_id=current_user.id,
        account_type=AccountType.INCOME,
        is_active=True
    )
    expense_accounts = Account.query.filter_by(
        user_id=current_user.id,
        account_type=AccountType.EXPENSE,
        is_active=True
    )
    
    if fund_filter:
        income_accounts = income_accounts.filter_by(fund_type=fund_filter)
        expense_accounts = expense_accounts.filter_by(fund_type=fund_filter)
    
    income_data = []
    total_income = Decimal('0')
    for account in income_accounts.order_by(Account.code).all():
        balance = account.get_balance(start_date=start, end_date=end)
        if balance != 0:
            income_data.append({'account': account, 'amount': balance})
            total_income += balance
    
    expense_data = []
    total_expense = Decimal('0')
    for account in expense_accounts.order_by(Account.code).all():
        balance = account.get_balance(start_date=start, end_date=end)
        if balance != 0:
            expense_data.append({'account': account, 'amount': balance})
            total_expense += balance
    
    surplus_deficit = total_income - total_expense
    
    return render_template('accounts/income_expenditure.html',
        income_data=income_data,
        expense_data=expense_data,
        total_income=total_income,
        total_expense=total_expense,
        surplus_deficit=surplus_deficit,
        start_date=start_date,
        end_date=end_date,
        fund_filter=fund_filter,
        funds=FundType.ALL_FUNDS,
        fund_names=FundType.FUND_NAMES
    )

@accounts_bp.route('/balance-sheet')
@login_required
def balance_sheet():
    as_of_date = request.args.get('as_of_date', '')
    
    end_date = None
    if as_of_date:
        try:
            end_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    asset_accounts = Account.query.filter_by(
        user_id=current_user.id,
        account_type=AccountType.ASSET,
        is_active=True
    ).order_by(Account.code).all()
    
    liability_accounts = Account.query.filter_by(
        user_id=current_user.id,
        account_type=AccountType.LIABILITY,
        is_active=True
    ).order_by(Account.code).all()
    
    equity_accounts = Account.query.filter_by(
        user_id=current_user.id,
        account_type=AccountType.EQUITY,
        is_active=True
    ).order_by(Account.code).all()
    
    asset_data = []
    total_assets = Decimal('0')
    for account in asset_accounts:
        balance = account.get_balance(end_date=end_date)
        asset_data.append({'account': account, 'balance': balance})
        total_assets += balance
    
    liability_data = []
    total_liabilities = Decimal('0')
    for account in liability_accounts:
        balance = account.get_balance(end_date=end_date)
        liability_data.append({'account': account, 'balance': balance})
        total_liabilities += balance
    
    equity_data = []
    total_equity = Decimal('0')
    for account in equity_accounts:
        balance = account.get_balance(end_date=end_date)
        equity_data.append({'account': account, 'balance': balance})
        total_equity += balance
    
    income_accounts = Account.query.filter_by(user_id=current_user.id, account_type=AccountType.INCOME, is_active=True).all()
    expense_accounts = Account.query.filter_by(user_id=current_user.id, account_type=AccountType.EXPENSE, is_active=True).all()
    
    total_income = sum(acc.get_balance(end_date=end_date) for acc in income_accounts)
    total_expense = sum(acc.get_balance(end_date=end_date) for acc in expense_accounts)
    current_surplus = total_income - total_expense
    
    total_equity_with_surplus = total_equity + current_surplus
    
    return render_template('accounts/balance_sheet.html',
        asset_data=asset_data,
        liability_data=liability_data,
        equity_data=equity_data,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        current_surplus=current_surplus,
        total_equity_with_surplus=total_equity_with_surplus,
        as_of_date=as_of_date,
        is_balanced=abs(total_assets - (total_liabilities + total_equity_with_surplus)) < Decimal('0.01'),
        fund_names=FundType.FUND_NAMES
    )
