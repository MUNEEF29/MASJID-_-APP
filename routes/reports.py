import io
import csv
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, make_response, send_file
from flask_login import login_required
from sqlalchemy import func
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from models import (db, Income, Expense, Account, AccountType, FundType,
                   IncomeCategory, ExpenseCategory, VerificationStatus, ApprovalStatus)

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/daily')
@login_required
def daily():
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = datetime.utcnow().date()
    
    incomes = Income.query.filter(
        Income.date == report_date,
        Income.is_reversed == False
    ).order_by(Income.created_at).all()
    
    expenses = Expense.query.filter(
        Expense.date == report_date,
        Expense.is_reversed == False
    ).order_by(Expense.created_at).all()
    
    total_income = sum(i.amount for i in incomes if i.verification_status == VerificationStatus.VERIFIED)
    total_expense = sum(e.amount for e in expenses if e.approval_status == ApprovalStatus.APPROVED)
    
    return render_template('reports/daily.html',
        report_date=report_date,
        incomes=incomes,
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        category_names={**IncomeCategory.CATEGORY_NAMES, **ExpenseCategory.CATEGORY_NAMES}
    )

@reports_bp.route('/monthly')
@login_required
def monthly():
    year = request.args.get('year', datetime.utcnow().year, type=int)
    month = request.args.get('month', datetime.utcnow().month, type=int)
    
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    
    income_by_category = db.session.query(
        Income.category,
        func.sum(Income.amount).label('total')
    ).filter(
        Income.date >= start_date,
        Income.date < end_date,
        Income.is_reversed == False,
        Income.verification_status == VerificationStatus.VERIFIED
    ).group_by(Income.category).all()
    
    expense_by_category = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.date >= start_date,
        Expense.date < end_date,
        Expense.is_reversed == False,
        Expense.approval_status == ApprovalStatus.APPROVED
    ).group_by(Expense.category).all()
    
    total_income = sum(i.total or 0 for i in income_by_category)
    total_expense = sum(e.total or 0 for e in expense_by_category)
    
    return render_template('reports/monthly.html',
        year=year,
        month=month,
        start_date=start_date,
        income_by_category=income_by_category,
        expense_by_category=expense_by_category,
        total_income=total_income,
        total_expense=total_expense,
        income_category_names=IncomeCategory.CATEGORY_NAMES,
        expense_category_names=ExpenseCategory.CATEGORY_NAMES
    )

@reports_bp.route('/donor')
@login_required
def donor():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Income.query.filter(
        Income.is_reversed == False,
        Income.verification_status == VerificationStatus.VERIFIED,
        Income.donor_name.isnot(None),
        Income.donor_name != ''
    )
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Income.date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Income.date <= end)
        except ValueError:
            pass
    
    donor_totals = db.session.query(
        Income.donor_name,
        func.count(Income.id).label('count'),
        func.sum(Income.amount).label('total')
    ).filter(
        Income.is_reversed == False,
        Income.verification_status == VerificationStatus.VERIFIED,
        Income.donor_name.isnot(None),
        Income.donor_name != ''
    )
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            donor_totals = donor_totals.filter(Income.date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            donor_totals = donor_totals.filter(Income.date <= end)
        except ValueError:
            pass
    
    donor_totals = donor_totals.group_by(Income.donor_name).order_by(func.sum(Income.amount).desc()).all()
    
    return render_template('reports/donor.html',
        donor_totals=donor_totals,
        start_date=start_date,
        end_date=end_date
    )

@reports_bp.route('/fund-summary')
@login_required
def fund_summary():
    fund_data = {}
    
    for fund_type in FundType.ALL_FUNDS:
        income_accounts = Account.query.filter_by(
            account_type=AccountType.INCOME,
            fund_type=fund_type,
            is_active=True
        ).all()
        
        expense_accounts = Account.query.filter_by(
            account_type=AccountType.EXPENSE,
            fund_type=fund_type,
            is_active=True
        ).all()
        
        asset_accounts = Account.query.filter_by(
            account_type=AccountType.ASSET,
            fund_type=fund_type,
            is_active=True
        ).all()
        
        total_income = sum(acc.get_balance() for acc in income_accounts)
        total_expense = sum(acc.get_balance() for acc in expense_accounts)
        total_assets = sum(acc.get_balance() for acc in asset_accounts)
        
        fund_data[fund_type] = {
            'name': FundType.FUND_NAMES.get(fund_type, fund_type),
            'total_income': total_income,
            'total_expense': total_expense,
            'surplus': total_income - total_expense,
            'assets': total_assets
        }
    
    return render_template('reports/fund_summary.html', fund_data=fund_data)

@reports_bp.route('/export/income-csv')
@login_required
def export_income_csv():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Income.query.filter_by(is_reversed=False)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Income.date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Income.date <= end)
        except ValueError:
            pass
    
    incomes = query.order_by(Income.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Receipt Number', 'Date', 'Time', 'Category', 'Fund Type',
        'Source', 'Donor Name', 'Payment Mode', 'Amount',
        'Verification Status', 'Entered By'
    ])
    
    for income in incomes:
        writer.writerow([
            income.receipt_number,
            income.date.strftime('%Y-%m-%d'),
            income.time.strftime('%H:%M'),
            IncomeCategory.CATEGORY_NAMES.get(income.category, income.category),
            FundType.FUND_NAMES.get(income.fund_type, income.fund_type),
            income.source,
            income.donor_name or '',
            income.payment_mode,
            float(income.amount),
            income.verification_status,
            income.entered_by.full_name
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=income_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    
    return response

@reports_bp.route('/export/expense-csv')
@login_required
def export_expense_csv():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = Expense.query.filter_by(is_reversed=False)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= end)
        except ValueError:
            pass
    
    expenses = query.order_by(Expense.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Voucher Number', 'Date', 'Category', 'Fund Type',
        'Payee', 'Description', 'Payment Mode', 'Amount',
        'Verification Status', 'Approval Status', 'Entered By'
    ])
    
    for expense in expenses:
        writer.writerow([
            expense.voucher_number,
            expense.date.strftime('%Y-%m-%d'),
            ExpenseCategory.CATEGORY_NAMES.get(expense.category, expense.category),
            FundType.FUND_NAMES.get(expense.fund_type, expense.fund_type),
            expense.payee,
            expense.description,
            expense.payment_mode,
            float(expense.amount),
            expense.verification_status,
            expense.approval_status,
            expense.entered_by.full_name
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    
    return response

@reports_bp.route('/export/trial-balance-pdf')
@login_required
def export_trial_balance_pdf():
    as_of_date = request.args.get('as_of_date', '')
    
    end_date = None
    if as_of_date:
        try:
            end_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1
    )
    
    elements.append(Paragraph("Masjid Accounting System", title_style))
    elements.append(Paragraph("Trial Balance", styles['Heading2']))
    
    if end_date:
        elements.append(Paragraph(f"As of: {end_date.strftime('%d %B %Y')}", styles['Normal']))
    else:
        elements.append(Paragraph(f"As of: {datetime.utcnow().strftime('%d %B %Y')}", styles['Normal']))
    
    elements.append(Spacer(1, 20))
    
    data = [['Account Code', 'Account Name', 'Debit', 'Credit']]
    
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
            
            data.append([
                account.code,
                account.name,
                f"{debit:,.2f}" if debit else '',
                f"{credit:,.2f}" if credit else ''
            ])
            total_debit += debit
            total_credit += credit
    
    data.append(['', 'Total', f"{total_debit:,.2f}", f"{total_credit:,.2f}"])
    
    table = Table(data, colWidths=[80, 250, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'trial_balance_{datetime.utcnow().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )
