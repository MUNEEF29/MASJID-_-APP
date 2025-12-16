import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User

login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.income import income_bp
    from routes.expenses import expenses_bp
    from routes.accounts import accounts_bp
    from routes.reports import reports_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))
    
    with app.app_context():
        db.create_all()
        init_default_data()
    
    return app

def init_default_data():
    from models import User, Account, AccountType, FundType, Role
    
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@masjid.org',
            full_name='System Administrator',
            role=Role.ADMIN,
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    
    default_accounts = [
        ('1000', 'Cash in Hand', AccountType.ASSET, FundType.GENERAL, 'Physical cash held'),
        ('1010', 'Bank Account - General', AccountType.ASSET, FundType.GENERAL, 'Main bank account'),
        ('1020', 'Bank Account - Zakat', AccountType.ASSET, FundType.ZAKAT, 'Dedicated Zakat bank account'),
        ('1030', 'Bank Account - Amanah', AccountType.ASSET, FundType.AMANAH, 'Trust fund bank account'),
        
        ('2000', 'Accounts Payable', AccountType.LIABILITY, FundType.GENERAL, 'Outstanding payables'),
        ('2010', 'Accrued Expenses', AccountType.LIABILITY, FundType.GENERAL, 'Accrued but unpaid expenses'),
        
        ('3000', 'General Fund Balance', AccountType.EQUITY, FundType.GENERAL, 'Accumulated general fund'),
        ('3010', 'Zakat Fund Balance', AccountType.EQUITY, FundType.ZAKAT, 'Accumulated Zakat fund'),
        ('3020', 'Amanah Fund Balance', AccountType.EQUITY, FundType.AMANAH, 'Trust fund balance'),
        
        ('4000', 'Donation Income', AccountType.INCOME, FundType.GENERAL, 'General donations'),
        ('4010', 'Zakat Income', AccountType.INCOME, FundType.ZAKAT, 'Zakat collections'),
        ('4020', 'Sadaqah Income', AccountType.INCOME, FundType.GENERAL, 'Sadaqah contributions'),
        ('4030', 'Fitrah Income', AccountType.INCOME, FundType.ZAKAT, 'Fitrah collections'),
        ('4040', 'Special Collections', AccountType.INCOME, FundType.AMANAH, 'Special purpose collections'),
        ('4050', 'Rental Income', AccountType.INCOME, FundType.GENERAL, 'Property rental income'),
        ('4060', 'Other Income', AccountType.INCOME, FundType.GENERAL, 'Miscellaneous income'),
        
        ('5000', 'Salary Expense', AccountType.EXPENSE, FundType.GENERAL, 'Staff salaries'),
        ('5010', 'Utilities Expense', AccountType.EXPENSE, FundType.GENERAL, 'Electricity, water, etc.'),
        ('5020', 'Maintenance Expense', AccountType.EXPENSE, FundType.GENERAL, 'Building maintenance'),
        ('5030', 'Vendor Payments', AccountType.EXPENSE, FundType.GENERAL, 'Supplier payments'),
        ('5040', 'Charity Disbursement - General', AccountType.EXPENSE, FundType.GENERAL, 'General charity'),
        ('5041', 'Charity Disbursement - Zakat', AccountType.EXPENSE, FundType.ZAKAT, 'Zakat distribution'),
        ('5050', 'Asset Purchases', AccountType.EXPENSE, FundType.GENERAL, 'Capital expenditure'),
        ('5060', 'Other Expenses', AccountType.EXPENSE, FundType.GENERAL, 'Miscellaneous expenses'),
    ]
    
    for code, name, acc_type, fund_type, description in default_accounts:
        if not Account.query.filter_by(code=code).first():
            account = Account(
                code=code,
                name=name,
                account_type=acc_type,
                fund_type=fund_type,
                description=description,
                is_active=True
            )
            db.session.add(account)
    
    db.session.commit()

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
