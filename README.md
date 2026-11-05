# SmartSpend — Modern Smart Expense Tracker Application

**SmartSpend** is a modern, fully functional, responsive smart financial management application designed for students, employees, business owners, and families for daily personal finance tracking, budget enforcement, and AI-driven spending analytics.

---

## 🌟 Key Features

### 1. User Authentication & Profile
- **Secure Registration & Login** with password hashing (PBKDF2/SHA-256 via Werkzeug).
- **Session Token Management** supporting multi-device persistence and automatic authorization.
- **1-Click Demo Account Access** with preloaded, realistic financial transactions, categories, budgets, and savings goals for instant exploration.
- **User Customization**: Profile name, preferred currency (`₹ INR`, `$ USD`, `€ EUR`, `£ GBP`, `¥ JPY`), and monthly income target.

### 2. Comprehensive Financial Dashboard
- **Total Balance**: Real-time all-time net balance (`Total Income - Total Expenses`).
- **Total Inflow & Outflow**: Distinct emerald green and rose red metrics.
- **Available Savings**: Net reserve balance.
- **Today's Spending**: Live aggregate of today's expenses.
- **Monthly Spending Trend**: Compares current month spending vs. previous month with percentage change indicator.
- **Budget Warning Banners**: Highlights active budgets that have reached 80% (Warning) or 100%+ (Over-budget).
- **Recent Transactions Card**: Quick view of latest income and expense entries with category tags and payment badges.
- **Financial Health Score Widget**: Real-time 0-100 score with grade pill.

### 3. Income Management
- Add income records with positive amount validation.
- Select source: **Salary, Business, Freelancing, Gift, Other**.
- Payment method: **Bank Transfer, UPI, Cash, Card**.
- Custom date and description.
- Edit and delete income records.

### 4. Daily Expense Management
- Record daily expenses with positive amount validation.
- Categories: **Food, Travel, Shopping, Education, Bills, Health, Entertainment, Other**.
- Payment methods: **Cash, UPI, Bank Transfer, Card**.
- Real-time instant updating of dashboard metrics upon adding, editing, or deleting.

### 5. Transaction History & Filtering
- Search transactions by description, category, or payment method.
- Filter by:
  - **Transaction Type**: All, Income (+), Expense (-)
  - **Category / Source**
  - **Payment Method**
  - **Date Range**: Custom date range or quick filters (*All Time, Today, This Month, Last Month*)
  - **Sort By**: Newest first, Oldest first, Highest amount, Lowest amount.
- Color-coded badges: Income in **emerald green**, Expenses in **rose red**.
- **CSV Data Export**: Download full transaction logs with a single click.
- **Print / Summary Receipts**: Built-in print stylesheets for clean paper and PDF reports.

### 6. Interactive Analytics & Visual Reports (Chart.js)
- **Income vs. Expense Trend**: 6-month dual-dataset bar chart.
- **Category-wise Spending Breakdown**: Doughnut chart with hover percentages and legend.
- **Payment Method Distribution**: Pie chart comparing UPI, Card, Bank Transfer, and Cash usage.
- **Daily Spending Curve**: Smooth area line chart tracking daily spend throughout the month.
- **Summary Metrics**: Total expenses, average daily spend, and highest spending day of the month.

### 7. Category Budget Management
- Set monthly limits for any expense category.
- Dynamic color-coded progress bars:
  - **< 80%**: Safe (Emerald Green)
  - **80% - 99%**: Warning (Amber Alert)
  - **&ge; 100%**: Danger / Over Limit (Crimson Red with pulsing alert)
- Shows spent amount, remaining allowance, and percentage used.
- Overall monthly spending limit overview.

### 8. Smart Financial Insights & AI Coach
- **Financial Health Score (0 - 100)**: Evaluates savings rate discipline, budget adherence, expense-to-income ratio, and goals progress.
- **50/30/20 Rule Analysis**: Visual breakdown of Needs (50%), Wants (30%), and Savings (20%) compared against recommended targets.
- **Unusual Spending Anomaly Detection**: Automatically flags expenses that exceed 2.0x category averages.
- **Personalized Money-Saving Suggestions**: Actionable advice derived from actual spending habits (e.g., potential 10% savings in highest expense category, digital payment discipline).
- **Automated Financial Summaries**: Daily, weekly, and monthly spending comparisons.

### 9. Savings Goals Tracker
- Create goals for Emergency Funds, Vacations, Gadgets, Vehicles, or Downpayments.
- Visual progress bars, target amounts, saved amounts, deadlines, and days remaining.
- **Deposit & Withdraw Modal**: Easily add or withdraw funds from goals.
- **Milestone Celebration**: Confetti animation triggers when a goal hits 100%!

### 10. Design & UX
- Modern, clean card UI with glassmorphism touches.
- **Dark Mode & Light Mode** toggle with instant switching and localStorage persistence.
- Fully responsive design: sidebar on desktop, bottom navigation bar on mobile/tablet.
- Non-blocking animated toast notifications.

---

## 🛠️ Technology Stack
- **Backend**: Python 3 (Flask, SQLite3, Werkzeug, Flask-CORS)
- **Frontend**: HTML5, Tailwind CSS, FontAwesome 6, Chart.js, Canvas-Confetti, Vanilla ES6+ JavaScript
- **Database**: SQLite3 (`smartspend.db`) with permanent storage and foreign key constraints

---

## 🚀 How to Run the Application

### Option 1: PowerShell
```powershell
cd C:\Users\Sajan\.gemini\antigravity\scratch\smartspend
& "C:\Users\Sajan\AppData\Local\Python\pythoncore-3.14-64\python.exe" app.py
```

### Option 2: Run Scripts
Double-click `run.bat` or run `.\run.ps1`.

### Option 3: Access in Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
- Click **"Explore Demo Account"** to immediately test with rich pre-loaded data, or **"Create Account"** to start fresh!

---

## 🧪 Running Integration Tests
To execute the automated test suite covering all APIs, validations, and database operations:
```powershell
& "C:\Users\Sajan\AppData\Local\Python\pythoncore-3.14-64\python.exe" test_smartspend.py
```
