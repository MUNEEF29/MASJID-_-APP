# MSJID E AMEER E MUAVIYYAH - Islamic Accounting System

## Overview
A production-ready, audit-grade web-based accounting application designed for **MSJID E AMEER E MUAVIYYAH (مسجد امیر معاویہ)**. Built with Flask and PostgreSQL, featuring double-entry bookkeeping, role-based access control, and Islamic compliance features. The system uses **Indian Rupee (₹)** as the default currency.

**Key Highlights:**
- Configurable app name through Admin Settings
- Beautiful Islamic-themed UI with Bismillah and Arabic calligraphy
- AI Islamic Assistant for learning about Islamic teachings

## Tech Stack
- **Backend**: Python 3.11 + Flask
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Authentication**: Flask-Login with role-based access control + Google OAuth
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap 5
- **PDF Generation**: ReportLab
- **AI Assistant**: Built-in Islamic knowledge base
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

### Income Management (Islamic Categories)
- **Zakat (زکوٰۃ)** - Ring-fenced obligatory charity
- **Sadaqah (صدقہ)** - Voluntary charity
- **Fitrah/Zakat-ul-Fitr (فطرہ)** - Ramadan charity
- **Lillah (للّٰہ)** - For the sake of Allah
- **General Donation (عطیہ)** - Regular donations
- **Fidyah (فدیہ)** - Compensation for missed fasts
- **Kaffarah (کفارہ)** - Expiation payments
- **Aqeeqah (عقیقہ)** - Birth celebration sacrifice
- **Qurbani/Udhiyah (قربانی)** - Eid sacrifice
- **Rental Income (کرایہ)** - Property rental
- **Special Collection (خصوصی چندہ)** - Event collections
- **Amanah/Trust (امانت)** - Trust funds
- Auto-generated receipt numbers
- Full audit trail with Urdu labels

### Expense Management (Islamic Categories)
- **Zakat Disbursement (زکوٰۃ کی تقسیم)** - Zakat given to eligible recipients
- **Sadaqah Disbursement (صدقہ کی تقسیم)** - Charity given out
- **Salaries & Wages (تنخواہ)** - Imam, staff salaries
- **Utilities & Bills (بجلی پانی)** - Electricity, water, gas
- **Maintenance & Repairs (مرمت)** - Building maintenance
- **Construction & Renovation (تعمیر)** - Building projects
- **Poor & Needy Aid (غریب امداد)** - Helping the poor
- **Education & Madrasah (تعلیم)** - Religious education
- **Funeral Services (جنازہ)** - Funeral arrangements
- **Islamic Events (اسلامی تقریبات)** - Programs and events
- **Masjid Supplies (سامان)** - General supplies
- **Food & Langar (کھانا)** - Community meals
- Voucher system with supporting document upload
- No deletion - only reversals allowed

### Fund Types (Islamic Finance)
- **General Fund** - General masjid operations
- **Zakat Fund (Ring-fenced)** - Strictly for eligible Zakat recipients only
- **Sadaqah Fund** - Flexible charitable use
- **Amanah/Trust Fund** - Funds held in trust
- **Lillah Fund** - For Allah's cause (masjid operations)

### Double-Entry Accounting
- Chart of Accounts with proper Islamic account types
- Automatic journal entries on creation
- Separate fund tracking with strict Zakat separation
- Trial Balance, Income & Expenditure Statement, Balance Sheet

### Islamic Compliance
- Zakat funds strictly separated and ring-fenced
- No interest calculations
- Amanah funds clearly tagged
- Transparent labeling
- Bismillah greeting on login

### AI Islamic Assistant
- Built-in knowledge base for Islamic teachings
- Information about Five Pillars of Islam
- Prayer times guidance
- Zakat and Sadaqah explanations
- Common Islamic greetings and phrases
- Duas for various occasions
- Quran and Hajj information
- Chat history saved per user

### Dynamic App Settings
- Change app name (English and Arabic)
- Customize tagline
- Configure currency symbol and code
- All settings logged in audit trail

### Reports
- Daily, Monthly, Yearly reports
- Donor-wise contribution reports
- Fund summary with distribution charts
- Export to PDF and CSV

## Configuration (config.py)
```python
APP_NAME = "MSJID E AMEER E MUAVIYYAH"
APP_NAME_ARABIC = "مسجد امیر معاویہ"
APP_TAGLINE = "Islamic Accounting & Financial Management System"
CURRENCY_SYMBOL = "₹"
CURRENCY_CODE = "INR"
CURRENCY_NAME = "Indian Rupee"
```

Note: These settings can be overridden via Admin > App Settings in the UI.

## Project Structure
```
/
├── app.py              # Main Flask application
├── main.py             # Entry point (runs on port 5000)
├── config.py           # Configuration settings (app name, currency)
├── models.py           # SQLAlchemy database models (including AppSettings, AIChatHistory)
├── routes/             # Blueprint routes
│   ├── auth.py         # Authentication
│   ├── dashboard.py    # Dashboard
│   ├── income.py       # Income management
│   ├── expenses.py     # Expense management
│   ├── accounts.py     # Chart of accounts & financial reports
│   ├── reports.py      # Report generation
│   ├── admin.py        # User & system administration + App Settings
│   └── ai_assistant.py # Islamic AI Assistant
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template with Islamic theme
│   ├── auth/           # Login, profile pages
│   ├── dashboard/      # Dashboard with Bismillah greeting
│   ├── income/         # Income entry pages
│   ├── expenses/       # Expense entry pages
│   ├── accounts/       # Chart of accounts, ledger, statements
│   ├── reports/        # Report pages
│   ├── admin/          # Admin pages + Settings
│   └── ai/             # AI Islamic Assistant
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
- Indian Rupee (₹) currency
- Mobile-first responsive design
- No mock data - all transactions are real
- Audit-grade data integrity

## Recent Changes
- **December 2025**: Added AI Islamic Assistant with knowledge base for Islamic teachings
- **December 2025**: Added dynamic App Settings to change app name, tagline, and currency
- **December 2025**: Created beautiful Islamic login page with mosque icon and Bismillah
- **December 2025**: Updated app name to "MSJID E AMEER E MUAVIYYAH"
- **December 2025**: Added Arabic name display throughout the app
- **December 2024**: Changed currency to Indian Rupee (₹)
- **December 2024**: Removed verification process - income and expenses now auto-post to accounts on creation
- **December 2024**: Implemented stunning Islamic-themed UI with geometric patterns
- **December 2024**: Added Bismillah greeting on login page
- **December 2024**: Enhanced dashboard with Islamic greeting (Assalamu Alaikum)
- **December 2024**: Updated all templates with Rupee currency formatting
