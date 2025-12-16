# Masjid e Ameer e Muaviyyah - Accounting System

## Overview
A production-ready, audit-grade web-based accounting application designed for **Masjid e Ameer e Muaviyyah (مسجد امیر معاویہ)**. Built with Flask and PostgreSQL, featuring double-entry bookkeeping, role-based access control, and Islamic compliance features. The system uses **Pakistani Rupee (Rs.)** as the default currency.

## Tech Stack
- **Backend**: Python 3.11 + Flask
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Authentication**: Flask-Login with role-based access control
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap 5
- **PDF Generation**: ReportLab
- **Fonts**: Amiri (Arabic/Islamic calligraphy), Poppins (modern UI)

## Design Theme
- **Islamic-inspired design** with emerald green (#0d6b4f) and gold (#d4af37) color palette
- Arabic calligraphy and Bismillah integration
- Crescent moon and stars logo
- Geometric patterns inspired by Islamic art
- Fully responsive mobile-first design

## Key Features

### Authentication & Roles
- 5 user roles: Admin, Accountant, Verifier, Treasurer, Auditor (read-only)
- Every action logged with user and timestamp
- Session-based authentication with Flask-Login

### Income Management
- Support for: Donations, Zakat, Sadaqah, Fitrah, Special Collections, Rental Income
- Auto-generated receipt numbers
- Verification workflow before posting to accounts
- Full audit trail
- Currency: Pakistani Rupee (Rs.)

### Expense Management
- Support for: Salaries, Utilities, Maintenance, Vendor Payments, Charity Disbursement, Asset Purchases
- Voucher system with supporting document upload
- Two-stage approval (Verification + Approval)
- No deletion - only reversals allowed

### Double-Entry Accounting
- Chart of Accounts with proper account types
- Automatic journal entries on verification/approval
- Separate fund tracking: General Fund, Zakat Fund (ring-fenced), Amanah/Trust Fund
- Trial Balance, Income & Expenditure Statement, Balance Sheet

### Islamic Compliance
- Zakat funds strictly separated and ring-fenced
- No interest calculations
- Amanah funds clearly tagged
- Transparent labeling
- Bismillah greeting on login

### Reports
- Daily, Monthly, Yearly reports
- Donor-wise contribution reports
- Fund summary with distribution charts
- Export to PDF and CSV

## Configuration (config.py)
```python
MOSQUE_NAME = "Masjid e Ameer e Muaviyyah"
MOSQUE_NAME_ARABIC = "مسجد امیر معاویہ"
CURRENCY_SYMBOL = "₹"
CURRENCY_CODE = "PKR"
CURRENCY_NAME = "Pakistani Rupee"
```

## Project Structure
```
/
├── app.py              # Main Flask application
├── main.py             # Entry point (runs on port 5000)
├── config.py           # Configuration settings (mosque name, currency)
├── models.py           # SQLAlchemy database models
├── routes/             # Blueprint routes
│   ├── auth.py         # Authentication
│   ├── dashboard.py    # Dashboard
│   ├── income.py       # Income management
│   ├── expenses.py     # Expense management
│   ├── accounts.py     # Chart of accounts & financial reports
│   ├── reports.py      # Report generation
│   └── admin.py        # User & system administration
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template with Islamic theme
│   ├── auth/           # Login, profile pages
│   ├── dashboard/      # Dashboard with greeting
│   ├── income/         # Income entry pages
│   ├── expenses/       # Expense entry pages
│   ├── accounts/       # Chart of accounts, ledger, statements
│   ├── reports/        # Report pages
│   └── admin/          # Admin pages
├── static/
│   ├── css/style.css   # Islamic-themed styling
│   └── js/main.js      # JavaScript utilities
└── uploads/            # Supporting document storage
```

## Default Admin Login
- **Username**: admin
- **Password**: admin123

## Running the Application
The application runs on port 5000 and is configured to work with the PostgreSQL database provided by Replit.

## User Preferences
- Islamic-themed design with emerald green and gold colors
- Arabic calligraphy for mosque name
- Pakistani Rupee (Rs.) currency
- Mobile-first responsive design
- No mock data - all transactions are real
- Audit-grade data integrity

## Recent Changes
- **December 2024**: Updated mosque name to "Masjid e Ameer e Muaviyyah"
- **December 2024**: Changed currency to Pakistani Rupee (Rs.)
- **December 2024**: Implemented stunning Islamic-themed UI with geometric patterns
- **December 2024**: Added Bismillah greeting on login page
- **December 2024**: Enhanced dashboard with Islamic greeting (Assalamu Alaikum)
- **December 2024**: Updated all templates with Rupee currency formatting
