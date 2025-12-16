from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from models import (db, Income, Expense, Account, AccountType, FundType,
                   VerificationStatus, ApprovalStatus, IncomeCategory)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    today = datetime.utcnow().date()
    first_of_month = today.replace(day=1)
    
    cash_account = Account.query.filter_by(code='1000').first()
    cash_balance = cash_account.get_balance() if cash_account else Decimal('0')
    
    bank_accounts = Account.query.filter(
        Account.code.in_(['1010', '1020', '1030'])
    ).all()
    bank_balance = sum(acc.get_balance() for acc in bank_accounts)
    
    monthly_income = db.session.query(
        func.coalesce(func.sum(Income.amount), 0)
    ).filter(
        Income.date >= first_of_month,
        Income.is_reversed == False,
        Income.verification_status == VerificationStatus.VERIFIED
    ).scalar() or Decimal('0')
    
    monthly_expense = db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        Expense.date >= first_of_month,
        Expense.is_reversed == False,
        Expense.approval_status == ApprovalStatus.APPROVED
    ).scalar() or Decimal('0')
    
    pending_income_verification = Income.query.filter_by(
        verification_status=VerificationStatus.PENDING,
        is_reversed=False
    ).count()
    
    pending_expense_verification = Expense.query.filter_by(
        verification_status=VerificationStatus.PENDING,
        is_reversed=False
    ).count()
    
    pending_expense_approval = Expense.query.filter_by(
        verification_status=VerificationStatus.VERIFIED,
        approval_status=ApprovalStatus.PENDING,
        is_reversed=False
    ).count()
    
    zakat_collected = db.session.query(
        func.coalesce(func.sum(Income.amount), 0)
    ).filter(
        Income.category.in_([IncomeCategory.ZAKAT, IncomeCategory.FITRAH]),
        Income.is_reversed == False,
        Income.verification_status == VerificationStatus.VERIFIED
    ).scalar() or Decimal('0')
    
    zakat_distributed = db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        Expense.fund_type == FundType.ZAKAT,
        Expense.is_reversed == False,
        Expense.approval_status == ApprovalStatus.APPROVED
    ).scalar() or Decimal('0')
    
    recent_income = Income.query.filter_by(is_reversed=False).order_by(
        Income.created_at.desc()
    ).limit(5).all()
    
    recent_expenses = Expense.query.filter_by(is_reversed=False).order_by(
        Expense.created_at.desc()
    ).limit(5).all()
    
    months = []
    income_data = []
    expense_data = []
    
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=30 * i)
        month_start = target_date.replace(day=1)
        if target_date.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        
        months.append(month_start.strftime('%b %Y'))
        
        month_income = db.session.query(
            func.coalesce(func.sum(Income.amount), 0)
        ).filter(
            Income.date >= month_start,
            Income.date <= month_end,
            Income.is_reversed == False,
            Income.verification_status == VerificationStatus.VERIFIED
        ).scalar() or Decimal('0')
        income_data.append(float(month_income))
        
        month_expense = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.date >= month_start,
            Expense.date <= month_end,
            Expense.is_reversed == False,
            Expense.approval_status == ApprovalStatus.APPROVED
        ).scalar() or Decimal('0')
        expense_data.append(float(month_expense))
    
    alerts = []
    if zakat_collected > 0 and zakat_distributed / zakat_collected < Decimal('0.5'):
        alerts.append({
            'type': 'warning',
            'message': f'Zakat distribution ({zakat_distributed:,.2f}) is less than 50% of collection ({zakat_collected:,.2f})'
        })
    
    if pending_expense_approval > 5:
        alerts.append({
            'type': 'info',
            'message': f'{pending_expense_approval} expenses pending approval'
        })
    
    return render_template('dashboard/index.html',
        cash_balance=cash_balance,
        bank_balance=bank_balance,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        pending_income_verification=pending_income_verification,
        pending_expense_verification=pending_expense_verification,
        pending_expense_approval=pending_expense_approval,
        zakat_collected=zakat_collected,
        zakat_distributed=zakat_distributed,
        recent_income=recent_income,
        recent_expenses=recent_expenses,
        chart_months=months,
        chart_income=income_data,
        chart_expense=expense_data,
        alerts=alerts
    )
