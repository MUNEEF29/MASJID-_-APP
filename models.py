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
    ZAKAT = 'zakat'
    SADAQAH = 'sadaqah'
    AMANAH = 'amanah'
    LILLAH = 'lillah'
    
    ALL_FUNDS = [GENERAL, ZAKAT, SADAQAH, AMANAH, LILLAH]
    
    FUND_NAMES = {
        GENERAL: 'General Fund',
        ZAKAT: 'Zakat Fund (Ring-fenced)',
        SADAQAH: 'Sadaqah Fund',
        AMANAH: 'Amanah/Trust Fund',
        LILLAH: 'Lillah Fund'
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
    ZAKAT = 'zakat'
    SADAQAH = 'sadaqah'
    FITRAH = 'fitrah'
    LILLAH = 'lillah'
    DONATION = 'donation'
    FIDYAH = 'fidyah'
    KAFFARAH = 'kaffarah'
    AQEEQAH = 'aqeeqah'
    QURBANI = 'qurbani'
    RENTAL = 'rental'
    SPECIAL = 'special'
    AMANAH = 'amanah'
    OTHER = 'other'
    
    ALL_CATEGORIES = [ZAKAT, SADAQAH, FITRAH, LILLAH, DONATION, FIDYAH, KAFFARAH, AQEEQAH, QURBANI, RENTAL, SPECIAL, AMANAH, OTHER]
    
    CATEGORY_NAMES = {
        ZAKAT: 'Zakat (زکوٰۃ)',
        SADAQAH: 'Sadaqah (صدقہ)',
        FITRAH: 'Fitrah/Zakat-ul-Fitr (فطرہ)',
        LILLAH: 'Lillah (للّٰہ)',
        DONATION: 'General Donation (عطیہ)',
        FIDYAH: 'Fidyah (فدیہ)',
        KAFFARAH: 'Kaffarah (کفارہ)',
        AQEEQAH: 'Aqeeqah (عقیقہ)',
        QURBANI: 'Qurbani/Udhiyah (قربانی)',
        RENTAL: 'Rental Income (کرایہ)',
        SPECIAL: 'Special Collection (خصوصی چندہ)',
        AMANAH: 'Amanah/Trust (امانت)',
        OTHER: 'Other Income (دیگر آمدنی)'
    }
    
    FUND_MAPPING = {
        ZAKAT: FundType.ZAKAT,
        SADAQAH: FundType.SADAQAH,
        FITRAH: FundType.ZAKAT,
        LILLAH: FundType.LILLAH,
        DONATION: FundType.GENERAL,
        FIDYAH: FundType.SADAQAH,
        KAFFARAH: FundType.SADAQAH,
        AQEEQAH: FundType.SADAQAH,
        QURBANI: FundType.SADAQAH,
        RENTAL: FundType.GENERAL,
        SPECIAL: FundType.GENERAL,
        AMANAH: FundType.AMANAH,
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
    SALARIES = 'salaries'
    UTILITIES = 'utilities'
    MAINTENANCE = 'maintenance'
    CONSTRUCTION = 'construction'
    ZAKAT_DISBURSEMENT = 'zakat_disbursement'
    SADAQAH_DISBURSEMENT = 'sadaqah_disbursement'
    POOR_NEEDY = 'poor_needy'
    EDUCATION = 'education'
    FUNERAL = 'funeral'
    EVENTS = 'events'
    SUPPLIES = 'supplies'
    FOOD = 'food'
    OTHER = 'other'
    
    ALL_CATEGORIES = [SALARIES, UTILITIES, MAINTENANCE, CONSTRUCTION, ZAKAT_DISBURSEMENT, SADAQAH_DISBURSEMENT, POOR_NEEDY, EDUCATION, FUNERAL, EVENTS, SUPPLIES, FOOD, OTHER]
    
    CATEGORY_NAMES = {
        SALARIES: 'Salaries & Wages (تنخواہ)',
        UTILITIES: 'Utilities & Bills (بجلی پانی)',
        MAINTENANCE: 'Maintenance & Repairs (مرمت)',
        CONSTRUCTION: 'Construction & Renovation (تعمیر)',
        ZAKAT_DISBURSEMENT: 'Zakat Disbursement (زکوٰۃ کی تقسیم)',
        SADAQAH_DISBURSEMENT: 'Sadaqah Disbursement (صدقہ کی تقسیم)',
        POOR_NEEDY: 'Poor & Needy Aid (غریب امداد)',
        EDUCATION: 'Education & Madrasah (تعلیم)',
        FUNERAL: 'Funeral Services (جنازہ)',
        EVENTS: 'Islamic Events (اسلامی تقریبات)',
        SUPPLIES: 'Masjid Supplies (سامان)',
        FOOD: 'Food & Langar (کھانا)',
        OTHER: 'Other Expenses (دیگر اخراجات)'
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


class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_setting(key, default=None):
        setting = AppSettings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set_setting(key, value):
        setting = AppSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = AppSettings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    @staticmethod
    def get_all_settings():
        settings = AppSettings.query.all()
        return {s.key: s.value for s in settings}


class AIChatHistory(db.Model):
    __tablename__ = 'ai_chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='ai_chats')


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
    """Create default chart of accounts for a masjid"""
    default_accounts = [
        ('1000', 'Cash in Hand (نقدی)', AccountType.ASSET, FundType.GENERAL, 'Physical cash in masjid'),
        ('1010', 'Bank Account - General', AccountType.ASSET, FundType.GENERAL, 'Main bank account'),
        ('1020', 'Bank Account - Zakat', AccountType.ASSET, FundType.ZAKAT, 'Zakat fund bank account'),
        ('1030', 'Bank Account - Sadaqah', AccountType.ASSET, FundType.SADAQAH, 'Sadaqah fund account'),
        ('1040', 'Bank Account - Amanah', AccountType.ASSET, FundType.AMANAH, 'Trust/Amanah fund account'),
        ('1050', 'Bank Account - Lillah', AccountType.ASSET, FundType.LILLAH, 'Lillah fund account'),
        
        ('2000', 'Payables', AccountType.LIABILITY, FundType.GENERAL, 'Amounts owed'),
        ('2010', 'Amanah Liability', AccountType.LIABILITY, FundType.AMANAH, 'Trust amounts to be returned'),
        
        ('3000', 'General Fund Balance', AccountType.EQUITY, FundType.GENERAL, 'Net worth - General'),
        ('3010', 'Zakat Fund Balance', AccountType.EQUITY, FundType.ZAKAT, 'Net worth - Zakat (Ring-fenced)'),
        ('3020', 'Sadaqah Fund Balance', AccountType.EQUITY, FundType.SADAQAH, 'Net worth - Sadaqah'),
        ('3030', 'Amanah Fund Balance', AccountType.EQUITY, FundType.AMANAH, 'Net worth - Amanah/Trust'),
        ('3040', 'Lillah Fund Balance', AccountType.EQUITY, FundType.LILLAH, 'Net worth - Lillah'),
        
        ('4000', 'Zakat Income (زکوٰۃ)', AccountType.INCOME, FundType.ZAKAT, 'Zakat received'),
        ('4010', 'Sadaqah Income (صدقہ)', AccountType.INCOME, FundType.SADAQAH, 'Sadaqah/Charity received'),
        ('4020', 'Fitrah Income (فطرہ)', AccountType.INCOME, FundType.ZAKAT, 'Zakat-ul-Fitr received'),
        ('4030', 'Lillah Income (للّٰہ)', AccountType.INCOME, FundType.LILLAH, 'Lillah donations'),
        ('4040', 'General Donations (عطیہ)', AccountType.INCOME, FundType.GENERAL, 'General donations'),
        ('4050', 'Rental Income (کرایہ)', AccountType.INCOME, FundType.GENERAL, 'Property rental income'),
        ('4060', 'Special Collections (خصوصی)', AccountType.INCOME, FundType.GENERAL, 'Special event collections'),
        ('4070', 'Amanah Received (امانت)', AccountType.INCOME, FundType.AMANAH, 'Trust amounts received'),
        ('4080', 'Other Income (دیگر)', AccountType.INCOME, FundType.GENERAL, 'Miscellaneous income'),
        
        ('5000', 'Zakat Disbursement (زکوٰۃ تقسیم)', AccountType.EXPENSE, FundType.ZAKAT, 'Zakat given to eligible recipients'),
        ('5010', 'Sadaqah Disbursement (صدقہ تقسیم)', AccountType.EXPENSE, FundType.SADAQAH, 'Sadaqah given out'),
        ('5020', 'Salaries & Wages (تنخواہ)', AccountType.EXPENSE, FundType.GENERAL, 'Imam, staff salaries'),
        ('5030', 'Utilities (بجلی پانی)', AccountType.EXPENSE, FundType.GENERAL, 'Electricity, water, gas'),
        ('5040', 'Maintenance (مرمت)', AccountType.EXPENSE, FundType.GENERAL, 'Repairs and maintenance'),
        ('5050', 'Construction (تعمیر)', AccountType.EXPENSE, FundType.GENERAL, 'Building and renovation'),
        ('5060', 'Education (تعلیم)', AccountType.EXPENSE, FundType.GENERAL, 'Madrasah and education'),
        ('5070', 'Events (تقریبات)', AccountType.EXPENSE, FundType.GENERAL, 'Islamic events and programs'),
        ('5080', 'Food & Langar (کھانا)', AccountType.EXPENSE, FundType.GENERAL, 'Food for events'),
        ('5090', 'Supplies (سامان)', AccountType.EXPENSE, FundType.GENERAL, 'Masjid supplies'),
        ('5100', 'Other Expenses (دیگر)', AccountType.EXPENSE, FundType.GENERAL, 'Miscellaneous expenses'),
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
