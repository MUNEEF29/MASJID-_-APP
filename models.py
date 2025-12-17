from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    profile_picture = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    accounts = db.relationship('Account', backref='owner', lazy='dynamic')
    incomes = db.relationship('Income', backref='owner', lazy='dynamic', foreign_keys='Income.user_id')
    expenses = db.relationship('Expense', backref='owner', lazy='dynamic', foreign_keys='Expense.user_id')
    transactions = db.relationship('Transaction', backref='owner', lazy='dynamic', foreign_keys='Transaction.user_id')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        return True
    
    def is_read_only(self):
        return False


class FundType:
    GENERAL = 'general'
    SAVINGS = 'savings'
    EMERGENCY = 'emergency'
    
    ALL_FUNDS = [GENERAL, SAVINGS, EMERGENCY]
    
    FUND_NAMES = {
        GENERAL: 'General Fund',
        SAVINGS: 'Savings Fund',
        EMERGENCY: 'Emergency Fund'
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    fund_type = db.Column(db.String(20), nullable=False, default=FundType.GENERAL)
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    parent = db.relationship('Account', remote_side=[id], backref='children')
    journal_entries = db.relationship('JournalEntry', backref='account', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'code', name='unique_user_account_code'),
    )
    
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reference_number = db.Column(db.String(50), nullable=False, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    fund_type = db.Column(db.String(20), nullable=False, default=FundType.GENERAL)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'reference_number', name='unique_user_reference'),
    )
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    reversal_of = db.relationship('Transaction', remote_side=[id], backref='reversed_by')
    journal_entries = db.relationship('JournalEntry', backref='transaction', lazy='dynamic', cascade='all, delete-orphan')


class IncomeCategory:
    SALARY = 'salary'
    FREELANCE = 'freelance'
    INVESTMENT = 'investment'
    GIFT = 'gift'
    REFUND = 'refund'
    RENTAL = 'rental'
    OTHER = 'other'
    
    ALL_CATEGORIES = [SALARY, FREELANCE, INVESTMENT, GIFT, REFUND, RENTAL, OTHER]
    
    CATEGORY_NAMES = {
        SALARY: 'Salary/Wages',
        FREELANCE: 'Freelance/Business',
        INVESTMENT: 'Investment Returns',
        GIFT: 'Gift/Bonus',
        REFUND: 'Refund',
        RENTAL: 'Rental Income',
        OTHER: 'Other Income'
    }
    
    FUND_MAPPING = {
        SALARY: FundType.GENERAL,
        FREELANCE: FundType.GENERAL,
        INVESTMENT: FundType.SAVINGS,
        GIFT: FundType.GENERAL,
        REFUND: FundType.GENERAL,
        RENTAL: FundType.GENERAL,
        OTHER: FundType.GENERAL
    }


class PaymentMode:
    CASH = 'cash'
    BANK = 'bank'
    UPI = 'upi'
    CARD = 'card'
    CHEQUE = 'cheque'
    
    ALL_MODES = [CASH, BANK, UPI, CARD, CHEQUE]
    
    MODE_NAMES = {
        CASH: 'Cash',
        BANK: 'Bank Transfer',
        UPI: 'UPI/Digital Payment',
        CARD: 'Credit/Debit Card',
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receipt_number = db.Column(db.String(50), nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=False)
    category = db.Column(db.String(30), nullable=False)
    fund_type = db.Column(db.String(20), nullable=False)
    source = db.Column(db.String(200), nullable=False)
    payer_name = db.Column(db.String(150))
    payer_contact = db.Column(db.String(100))
    payment_mode = db.Column(db.String(20), nullable=False)
    payment_reference = db.Column(db.String(100))
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text)
    verification_status = db.Column(db.String(20), default=VerificationStatus.VERIFIED)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime)
    verification_remarks = db.Column(db.Text)
    entered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey('incomes.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'receipt_number', name='unique_user_receipt'),
    )
    
    entered_by = db.relationship('User', foreign_keys=[entered_by_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])
    transaction = db.relationship('Transaction', backref='income')
    reversal_of = db.relationship('Income', remote_side=[id], backref='reversed_by')
    
    @staticmethod
    def generate_receipt_number(user_id):
        today = datetime.utcnow()
        prefix = f"RCP{today.strftime('%Y%m%d')}"
        last_income = Income.query.filter(
            Income.user_id == user_id,
            Income.receipt_number.like(f"{prefix}%")
        ).order_by(Income.receipt_number.desc()).first()
        
        if last_income:
            last_num = int(last_income.receipt_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"


class ExpenseCategory:
    FOOD = 'food'
    TRANSPORT = 'transport'
    UTILITIES = 'utilities'
    RENT = 'rent'
    SHOPPING = 'shopping'
    ENTERTAINMENT = 'entertainment'
    HEALTHCARE = 'healthcare'
    EDUCATION = 'education'
    INVESTMENT = 'investment'
    OTHER = 'other'
    
    ALL_CATEGORIES = [FOOD, TRANSPORT, UTILITIES, RENT, SHOPPING, ENTERTAINMENT, HEALTHCARE, EDUCATION, INVESTMENT, OTHER]
    
    CATEGORY_NAMES = {
        FOOD: 'Food & Dining',
        TRANSPORT: 'Transportation',
        UTILITIES: 'Utilities & Bills',
        RENT: 'Rent/Mortgage',
        SHOPPING: 'Shopping',
        ENTERTAINMENT: 'Entertainment',
        HEALTHCARE: 'Healthcare',
        EDUCATION: 'Education',
        INVESTMENT: 'Investment',
        OTHER: 'Other Expenses'
    }


class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    voucher_number = db.Column(db.String(50), nullable=False, index=True)
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
    verification_status = db.Column(db.String(20), default=VerificationStatus.VERIFIED)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime)
    verification_remarks = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default=ApprovalStatus.APPROVED)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime)
    approval_remarks = db.Column(db.Text)
    entered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'voucher_number', name='unique_user_voucher'),
    )
    
    entered_by = db.relationship('User', foreign_keys=[entered_by_id])
    verified_by = db.relationship('User', foreign_keys=[verified_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    transaction = db.relationship('Transaction', backref='expense')
    reversal_of = db.relationship('Expense', remote_side=[id], backref='reversed_by')
    
    @staticmethod
    def generate_voucher_number(user_id):
        today = datetime.utcnow()
        prefix = f"EXP{today.strftime('%Y%m%d')}"
        last_expense = Expense.query.filter(
            Expense.user_id == user_id,
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    locked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    remarks = db.Column(db.Text)
    
    locked_by = db.relationship('User', foreign_keys=[locked_by_id])
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'year', 'month', name='unique_user_period_lock'),
    )
    
    @staticmethod
    def is_period_locked(user_id, date):
        return PeriodLock.query.filter_by(
            user_id=user_id,
            year=date.year,
            month=date.month
        ).first() is not None


def create_default_accounts_for_user(user_id):
    """Create default chart of accounts for a new user"""
    default_accounts = [
        ('1000', 'Cash in Hand', AccountType.ASSET, FundType.GENERAL, 'Physical cash'),
        ('1010', 'Bank Account - Primary', AccountType.ASSET, FundType.GENERAL, 'Main bank account'),
        ('1020', 'Bank Account - Savings', AccountType.ASSET, FundType.SAVINGS, 'Savings account'),
        ('1030', 'Bank Account - Emergency', AccountType.ASSET, FundType.EMERGENCY, 'Emergency fund account'),
        ('1100', 'Investments', AccountType.ASSET, FundType.SAVINGS, 'Investment portfolio'),
        
        ('2000', 'Credit Card', AccountType.LIABILITY, FundType.GENERAL, 'Credit card balance'),
        ('2010', 'Loans Payable', AccountType.LIABILITY, FundType.GENERAL, 'Loan balances'),
        
        ('3000', 'General Fund Balance', AccountType.EQUITY, FundType.GENERAL, 'Net worth - General'),
        ('3010', 'Savings Fund Balance', AccountType.EQUITY, FundType.SAVINGS, 'Net worth - Savings'),
        ('3020', 'Emergency Fund Balance', AccountType.EQUITY, FundType.EMERGENCY, 'Net worth - Emergency'),
        
        ('4000', 'Salary Income', AccountType.INCOME, FundType.GENERAL, 'Salary and wages'),
        ('4010', 'Freelance Income', AccountType.INCOME, FundType.GENERAL, 'Freelance earnings'),
        ('4020', 'Investment Income', AccountType.INCOME, FundType.SAVINGS, 'Investment returns'),
        ('4030', 'Gift Income', AccountType.INCOME, FundType.GENERAL, 'Gifts and bonuses'),
        ('4040', 'Rental Income', AccountType.INCOME, FundType.GENERAL, 'Property rental income'),
        ('4050', 'Other Income', AccountType.INCOME, FundType.GENERAL, 'Miscellaneous income'),
        
        ('5000', 'Food & Dining', AccountType.EXPENSE, FundType.GENERAL, 'Food expenses'),
        ('5010', 'Transportation', AccountType.EXPENSE, FundType.GENERAL, 'Travel and transport'),
        ('5020', 'Utilities', AccountType.EXPENSE, FundType.GENERAL, 'Bills and utilities'),
        ('5030', 'Rent/Mortgage', AccountType.EXPENSE, FundType.GENERAL, 'Housing costs'),
        ('5040', 'Shopping', AccountType.EXPENSE, FundType.GENERAL, 'Shopping expenses'),
        ('5050', 'Entertainment', AccountType.EXPENSE, FundType.GENERAL, 'Entertainment and leisure'),
        ('5060', 'Healthcare', AccountType.EXPENSE, FundType.GENERAL, 'Medical expenses'),
        ('5070', 'Education', AccountType.EXPENSE, FundType.GENERAL, 'Education expenses'),
        ('5080', 'Investment', AccountType.EXPENSE, FundType.SAVINGS, 'Investment contributions'),
        ('5090', 'Other Expenses', AccountType.EXPENSE, FundType.GENERAL, 'Miscellaneous expenses'),
    ]
    
    for code, name, acc_type, fund_type, description in default_accounts:
        existing = Account.query.filter_by(user_id=user_id, code=code).first()
        if not existing:
            account = Account(
                user_id=user_id,
                code=code,
                name=name,
                account_type=acc_type,
                fund_type=fund_type,
                description=description,
                is_active=True
            )
            db.session.add(account)
    
    db.session.commit()
