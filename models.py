from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Role:
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'
    VERIFIER = 'verifier'
    TREASURER = 'treasurer'
    AUDITOR = 'auditor'
    
    ALL_ROLES = [ADMIN, ACCOUNTANT, VERIFIER, TREASURER, AUDITOR]
    
    ROLE_PERMISSIONS = {
        ADMIN: ['all'],
        ACCOUNTANT: ['create_income', 'create_expense', 'view_reports', 'view_dashboard'],
        VERIFIER: ['verify_income', 'verify_expense', 'view_reports', 'view_dashboard'],
        TREASURER: ['approve_expense', 'view_reports', 'view_dashboard', 'close_period'],
        AUDITOR: ['view_reports', 'view_dashboard', 'view_audit_trail']
    }


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.ACCOUNTANT)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        if self.role == Role.ADMIN:
            return True
        return permission in Role.ROLE_PERMISSIONS.get(self.role, [])
    
    def is_read_only(self):
        return self.role == Role.AUDITOR


class FundType:
    GENERAL = 'general'
    ZAKAT = 'zakat'
    AMANAH = 'amanah'
    
    ALL_FUNDS = [GENERAL, ZAKAT, AMANAH]
    
    FUND_NAMES = {
        GENERAL: 'General Masjid Fund',
        ZAKAT: 'Zakat Fund (Ring-fenced)',
        AMANAH: 'Amanah / Trust Fund'
    }


class AccountType:
    ASSET = 'asset'
    LIABILITY = 'liability'
    EQUITY = 'equity'
    INCOME = 'income'
    EXPENSE = 'expense'
    
    ALL_TYPES = [ASSET, LIABILITY, EQUITY, INCOME, EXPENSE]


class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    fund_type = db.Column(db.String(20), nullable=False, default=FundType.GENERAL)
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    parent = db.relationship('Account', remote_side=[id], backref='children')
    journal_entries = db.relationship('JournalEntry', backref='account', lazy='dynamic')
    
    def get_balance(self, start_date=None, end_date=None):
        query = JournalEntry.query.filter_by(account_id=self.id)
        if start_date:
            query = query.filter(JournalEntry.date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.date <= end_date)
        
        entries = query.all()
        total_debit = sum(e.debit_amount or Decimal('0') for e in entries)
        total_credit = sum(e.credit_amount or Decimal('0') for e in entries)
        
        if self.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            return total_debit - total_credit
        else:
            return total_credit - total_debit


class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit_amount = db.Column(db.Numeric(15, 2), default=Decimal('0'))
    credit_amount = db.Column(db.Numeric(15, 2), default=Decimal('0'))
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    fund_type = db.Column(db.String(20), nullable=False, default=FundType.GENERAL)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    reversal_of = db.relationship('Transaction', remote_side=[id], backref='reversed_by')
    journal_entries = db.relationship('JournalEntry', backref='transaction', lazy='dynamic', cascade='all, delete-orphan')


class IncomeCategory:
    DONATION = 'donation'
    ZAKAT = 'zakat'
    SADAQAH = 'sadaqah'
    FITRAH = 'fitrah'
    SPECIAL_COLLECTION = 'special_collection'
    RENTAL = 'rental'
    OTHER = 'other'
    
    ALL_CATEGORIES = [DONATION, ZAKAT, SADAQAH, FITRAH, SPECIAL_COLLECTION, RENTAL, OTHER]
    
    CATEGORY_NAMES = {
        DONATION: 'Donation',
        ZAKAT: 'Zakat',
        SADAQAH: 'Sadaqah',
        FITRAH: 'Fitrah',
        SPECIAL_COLLECTION: 'Special Collection',
        RENTAL: 'Rental Income',
        OTHER: 'Other Income'
    }
    
    FUND_MAPPING = {
        DONATION: FundType.GENERAL,
        ZAKAT: FundType.ZAKAT,
        SADAQAH: FundType.GENERAL,
        FITRAH: FundType.ZAKAT,
        SPECIAL_COLLECTION: FundType.AMANAH,
        RENTAL: FundType.GENERAL,
        OTHER: FundType.GENERAL
    }


class PaymentMode:
    CASH = 'cash'
    BANK = 'bank'
    UPI = 'upi'
    CHEQUE = 'cheque'
    
    ALL_MODES = [CASH, BANK, UPI, CHEQUE]
    
    MODE_NAMES = {
        CASH: 'Cash',
        BANK: 'Bank Transfer',
        UPI: 'UPI',
        CHEQUE: 'Cheque'
    }


class VerificationStatus:
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'
    
    ALL_STATUSES = [PENDING, VERIFIED, REJECTED]


class ApprovalStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    ALL_STATUSES = [PENDING, APPROVED, REJECTED]


class Income(db.Model):
    __tablename__ = 'incomes'
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=False)
    category = db.Column(db.String(30), nullable=False)
    fund_type = db.Column(db.String(20), nullable=False)
    source = db.Column(db.String(200), nullable=False)
    donor_name = db.Column(db.String(150))
    donor_contact = db.Column(db.String(100))
    payment_mode = db.Column(db.String(20), nullable=False)
    payment_reference = db.Column(db.String(100))
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text)
    verification_status = db.Column(db.String(20), default=VerificationStatus.PENDING)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime)
    verification_remarks = db.Column(db.Text)
    entered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey('incomes.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    entered_by = db.relationship('User', foreign_keys=[entered_by_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])
    transaction = db.relationship('Transaction', backref='income')
    reversal_of = db.relationship('Income', remote_side=[id], backref='reversed_by')
    
    @staticmethod
    def generate_receipt_number():
        today = datetime.utcnow()
        prefix = f"RCP{today.strftime('%Y%m%d')}"
        last_income = Income.query.filter(
            Income.receipt_number.like(f"{prefix}%")
        ).order_by(Income.receipt_number.desc()).first()
        
        if last_income:
            last_num = int(last_income.receipt_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"


class ExpenseCategory:
    SALARY = 'salary'
    UTILITIES = 'utilities'
    MAINTENANCE = 'maintenance'
    VENDOR = 'vendor'
    CHARITY = 'charity'
    ASSET = 'asset'
    OTHER = 'other'
    
    ALL_CATEGORIES = [SALARY, UTILITIES, MAINTENANCE, VENDOR, CHARITY, ASSET, OTHER]
    
    CATEGORY_NAMES = {
        SALARY: 'Salaries & Wages',
        UTILITIES: 'Utilities',
        MAINTENANCE: 'Maintenance',
        VENDOR: 'Vendor Payments',
        CHARITY: 'Charity Disbursement',
        ASSET: 'Asset Purchases',
        OTHER: 'Other Expenses'
    }


class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    voucher_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False)
    fund_type = db.Column(db.String(20), nullable=False, default=FundType.GENERAL)
    payee = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False)
    payment_reference = db.Column(db.String(100))
    supporting_document = db.Column(db.String(255))
    verification_status = db.Column(db.String(20), default=VerificationStatus.PENDING)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime)
    verification_remarks = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default=ApprovalStatus.PENDING)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime)
    approval_remarks = db.Column(db.Text)
    entered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    entered_by = db.relationship('User', foreign_keys=[entered_by_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    transaction = db.relationship('Transaction', backref='expense')
    reversal_of = db.relationship('Expense', remote_side=[id], backref='reversed_by')
    
    @staticmethod
    def generate_voucher_number():
        today = datetime.utcnow()
        prefix = f"VCH{today.strftime('%Y%m%d')}"
        last_expense = Expense.query.filter(
            Expense.voucher_number.like(f"{prefix}%")
        ).order_by(Expense.voucher_number.desc()).first()
        
        if last_expense:
            last_num = int(last_expense.voucher_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    remarks = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class PeriodLock(db.Model):
    __tablename__ = 'period_locks'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    locked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    remarks = db.Column(db.Text)
    
    locked_by = db.relationship('User')
    
    __table_args__ = (
        db.UniqueConstraint('year', 'month', name='unique_period_lock'),
    )
    
    @staticmethod
    def is_period_locked(date):
        return PeriodLock.query.filter_by(
            year=date.year,
            month=date.month
        ).first() is not None
