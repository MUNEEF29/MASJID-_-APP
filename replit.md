# Masjid Accounting System

## Overview
A production-ready, audit-grade web-based accounting application designed for Masjid (mosque) financial management. Built with Flask and PostgreSQL, featuring double-entry bookkeeping, role-based access control, and Islamic compliance features.

## Tech Stack
- **Backend**: Python 3.11 + Flask
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Authentication**: Flask-Login with role-based access control
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap 5
- **PDF Generation**: ReportLab

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

### Reports
- Daily, Monthly, Yearly reports
- Donor-wise contribution reports
- Fund summary with distribution charts
- Export to PDF and CSV

## Project Structure
```
/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
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
├── static/             # CSS, JavaScript, images
└── uploads/            # Supporting document storage
```

## Default Admin Login
- **Username**: admin
- **Password**: admin123

## Running the Application
The application runs on port 5000 and is configured to work with the PostgreSQL database provided by Replit.

## User Preferences
- Mobile-first responsive design
- Clean, professional UI
- No mock data - all transactions are real
- Audit-grade data integrity
