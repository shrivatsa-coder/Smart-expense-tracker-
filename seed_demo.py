from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def seed_demo_user(db):
    cursor = db.cursor()
    
    # Check if demo user already exists
    cursor.execute("SELECT id FROM users WHERE email = 'demo@smartspend.io'")
    existing = cursor.fetchone()
    
    if existing:
        demo_id = existing["id"]
        # Clear previous data for clean refresh
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (demo_id,))
        cursor.execute("DELETE FROM budgets WHERE user_id = ?", (demo_id,))
        cursor.execute("DELETE FROM savings_goals WHERE user_id = ?", (demo_id,))
    else:
        password_hash = generate_password_hash("demo123")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, currency, monthly_income_goal)
            VALUES (?, ?, ?, ?, ?)
        """, ("Alex Morgan", "demo@smartspend.io", password_hash, "INR", 75000))
        demo_id = cursor.lastrowid

    now = datetime.now()
    current_month_str = now.strftime("%Y-%m")
    
    # Compute last month
    first_of_this_month = now.replace(day=1)
    last_month_date = first_of_this_month - timedelta(days=5)
    last_month_str = last_month_date.strftime("%Y-%m")

    # Sample transactions
    sample_data = [
        # --- Current Month Income ---
        ("income", 65000, "Salary", "Bank Transfer", f"{current_month_str}-01", "Monthly Tech Lead Salary"),
        ("income", 12500, "Freelancing", "UPI", f"{current_month_str}-04", "UI/UX Design Contract for Client"),
        ("income", 5000, "Business", "Bank Transfer", f"{current_month_str}-10", "Quarterly SaaS Affiliate Revenue"),
        ("income", 3000, "Gift", "UPI", f"{current_month_str}-15", "Birthday gift from Family"),

        # --- Current Month Expenses ---
        ("expense", 18500, "Bills", "Bank Transfer", f"{current_month_str}-02", "Apartment Rent & Maintenance"),
        ("expense", 2400, "Bills", "Card", f"{current_month_str}-03", "Electricity & High-speed Fiber Bill"),
        ("expense", 680, "Food", "UPI", f"{current_month_str}-03", "Organic Groceries from Supermarket"),
        ("expense", 350, "Travel", "UPI", f"{current_month_str}-04", "Metro Card Recharge & Uber ride"),
        ("expense", 1250, "Food", "Card", f"{current_month_str}-05", "Dinner at Italian Bistro with colleagues"),
        ("expense", 499, "Entertainment", "Card", f"{current_month_str}-05", "Netflix & Spotify Monthly Subscriptions"),
        ("expense", 3200, "Shopping", "Card", f"{current_month_str}-06", "Ergonomic Office Chair Cushion & Desk Lamp"),
        ("expense", 850, "Health", "UPI", f"{current_month_str}-07", "Monthly Multivitamins & Health Supplements"),
        ("expense", 450, "Food", "Cash", f"{current_month_str}-08", "Weekly Fresh Vegetables & Fruits"),
        ("expense", 1500, "Education", "Card", f"{current_month_str}-09", "Cloud Architecture Certification Course"),
        ("expense", 920, "Travel", "UPI", f"{current_month_str}-10", "Weekend Fuel Refill for Car"),
        ("expense", 890, "Food", "UPI", f"{current_month_str}-11", "Artisan Coffee & Snacks"),
        ("expense", 4500, "Shopping", "Card", f"{current_month_str}-12", "Wireless Noise-cancelling Headphones"),
        ("expense", 1800, "Entertainment", "UPI", f"{current_month_str}-13", "IMAX Movie Tickets & Popcorn Combo"),
        ("expense", 620, "Health", "UPI", f"{current_month_str}-14", "Dental Routine Cleaning & Checkup"),
        ("expense", 1100, "Food", "UPI", f"{current_month_str}-15", "Family Weekend Brunch"),

        # --- Last Month Data (for comparison & trends) ---
        ("income", 65000, "Salary", "Bank Transfer", f"{last_month_str}-01", "Monthly Salary"),
        ("income", 10000, "Freelancing", "UPI", f"{last_month_str}-12", "Website Frontend Optimization"),
        ("expense", 18500, "Bills", "Bank Transfer", f"{last_month_str}-02", "Apartment Rent"),
        ("expense", 2200, "Bills", "Card", f"{last_month_str}-04", "Utilities & Water Bill"),
        ("expense", 7800, "Food", "UPI", f"{last_month_str}-15", "Monthly Groceries & Dining"),
        ("expense", 3400, "Travel", "UPI", f"{last_month_str}-20", "Fuel and Cab Commute"),
        ("expense", 5600, "Shopping", "Card", f"{last_month_str}-22", "Autumn Wardrobe & Shoes"),
        ("expense", 2000, "Entertainment", "Card", f"{last_month_str}-25", "Concert tickets"),
        ("expense", 1200, "Health", "Cash", f"{last_month_str}-27", "Physiotherapy Session"),
    ]

    for tx in sample_data:
        cursor.execute("""
            INSERT INTO transactions (user_id, type, amount, category, payment_method, date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (demo_id, tx[0], tx[1], tx[2], tx[3], tx[4], tx[5]))

    # Seed Budgets for current month
    budgets = [
        ("Food", 10000),
        ("Bills", 22000),
        ("Shopping", 8000),
        ("Travel", 4000),
        ("Entertainment", 3000),
        ("Health", 2500)
    ]
    for cat, limit in budgets:
        cursor.execute("""
            INSERT INTO budgets (user_id, category, monthly_limit, month)
            VALUES (?, ?, ?, ?)
        """, (demo_id, cat, limit, current_month_str))

    # Seed Savings Goals
    goals = [
        ("Emergency Fund (6 Months)", 120000, 85000, f"{now.year + 1}-06-30", "#10B981", "fa-shield-halved"),
        ("MacBook Pro M-Series", 95000, 68000, f"{now.year}-12-31", "#6366F1", "fa-laptop"),
        ("Japan Cherry Blossom Trip", 150000, 42000, f"{now.year + 1}-04-15", "#EC4899", "fa-plane-departure"),
    ]
    for name, target, current, deadline, color, icon in goals:
        cursor.execute("""
            INSERT INTO savings_goals (user_id, name, target_amount, current_amount, deadline, color, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (demo_id, name, target, current, deadline, color, icon))

    db.commit()
    return demo_id
