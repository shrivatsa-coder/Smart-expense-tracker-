import os
import uuid
import csv
import io
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, render_template, send_from_directory, Response, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import DB_PATH, init_db
from smart_insights import get_insights
from seed_demo import seed_demo_user

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "smartspend-super-secret-key-99214")
CORS(app)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# Initialize database schema on startup
with app.app_context():
    init_db()

# --- Auth Helper Decorator ---
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()
        elif request.headers.get("X-Auth-Token"):
            token = request.headers.get("X-Auth-Token").strip()
        
        if not token:
            return jsonify({"error": "Unauthorized. Please log in."}), 401

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.currency, u.monthly_income_goal
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "Session expired or invalid. Please log in again."}), 401

        g.current_user = dict(user)
        g.token = token
        return f(*args, **kwargs)
    return decorated


# --- Static / UI Route ---
@app.route("/")
def index():
    return render_template("index.html")


# --- Auth Endpoints ---
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    currency = (data.get("currency") or "INR").strip().upper()

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        return jsonify({"error": "An account with this email already exists."}), 409

    pwd_hash = generate_password_hash(password)
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, currency)
        VALUES (?, ?, ?, ?)
    """, (name, email, pwd_hash, currency))
    user_id = cursor.lastrowid

    # Create session token
    token = str(uuid.uuid4())
    cursor.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    db.commit()

    return jsonify({
        "message": "Registration successful!",
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "currency": currency,
            "monthly_income_goal": 0
        }
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    token = str(uuid.uuid4())
    cursor.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user["id"]))
    db.commit()

    return jsonify({
        "message": "Login successful!",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "currency": user["currency"],
            "monthly_income_goal": user["monthly_income_goal"]
        }
    })


@app.route("/api/auth/demo", methods=["POST"])
def login_demo():
    """Allows instantaneous 1-click test access with preloaded rich realistic data."""
    db = get_db()
    demo_user_id = seed_demo_user(db)
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (demo_user_id,))
    user = cursor.fetchone()

    token = str(uuid.uuid4())
    cursor.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user["id"]))
    db.commit()

    return jsonify({
        "message": "Logged into demo account!",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "currency": user["currency"],
            "monthly_income_goal": user["monthly_income_goal"]
        }
    })


@app.route("/api/auth/profile", methods=["GET"])
@auth_required
def get_profile():
    return jsonify({"user": g.current_user})


@app.route("/api/auth/profile", methods=["PUT"])
@auth_required
def update_profile():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    currency = (data.get("currency") or "INR").strip().upper()
    monthly_income_goal = float(data.get("monthly_income_goal") or 0)

    if not name:
        return jsonify({"error": "Name cannot be empty."}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE users
        SET name = ?, currency = ?, monthly_income_goal = ?
        WHERE id = ?
    """, (name, currency, monthly_income_goal, g.current_user["id"]))
    db.commit()

    g.current_user["name"] = name
    g.current_user["currency"] = currency
    g.current_user["monthly_income_goal"] = monthly_income_goal

    return jsonify({"message": "Profile updated successfully!", "user": g.current_user})


@app.route("/api/auth/logout", methods=["POST"])
@auth_required
def logout():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (g.token,))
    db.commit()
    return jsonify({"message": "Logged out successfully."})


# --- Dashboard Stats API ---
@app.route("/api/dashboard/stats", methods=["GET"])
@auth_required
def dashboard_stats():
    user_id = g.current_user["id"]
    db = get_db()
    cursor = db.cursor()

    today_str = datetime.now().strftime("%Y-%m-%d")
    current_month_str = datetime.now().strftime("%Y-%m")
    
    # Calculate previous month string
    first_this_month = datetime.now().replace(day=1)
    last_month_date = first_this_month - timedelta(days=5)
    last_month_str = last_month_date.strftime("%Y-%m")

    # 1. Total All-time Income & Expense
    cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expense
        FROM transactions
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    total_income = row["total_income"]
    total_expense = row["total_expense"]
    total_balance = total_income - total_expense

    # 2. Today's spending
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS today_spend
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date = ?
    """, (user_id, today_str))
    today_spending = cursor.fetchone()["today_spend"]

    # 3. Monthly spending (current vs last month)
    cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'expense' AND date LIKE ? THEN amount ELSE 0 END), 0) AS month_expense,
            COALESCE(SUM(CASE WHEN type = 'income' AND date LIKE ? THEN amount ELSE 0 END), 0) AS month_income
        FROM transactions
        WHERE user_id = ?
    """, (f"{current_month_str}%", f"{current_month_str}%", user_id))
    m_row = cursor.fetchone()
    this_month_expense = m_row["month_expense"]
    this_month_income = m_row["month_income"]

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS last_month_expense
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date LIKE ?
    """, (user_id, f"{last_month_str}%"))
    last_month_expense = cursor.fetchone()["last_month_expense"]

    # Monthly spending percentage change
    month_diff_pct = 0
    if last_month_expense > 0:
        month_diff_pct = round(((this_month_expense - last_month_expense) / last_month_expense) * 100, 1)

    # 4. Available Savings: Net balance across all accounts
    available_savings = max(0, total_balance)

    # 5. Recent transactions (latest 6)
    cursor.execute("""
        SELECT id, type, amount, category, payment_method, date, description
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 6
    """, (user_id,))
    recent_transactions = [dict(r) for r in cursor.fetchall()]

    # 6. Budget Warning Alerts Summary
    cursor.execute("""
        SELECT b.id, b.category, b.monthly_limit,
               COALESCE(SUM(t.amount), 0) as spent
        FROM budgets b
        LEFT JOIN transactions t ON t.user_id = b.user_id 
             AND t.category = b.category 
             AND t.type = 'expense' 
             AND t.date LIKE ?
        WHERE b.user_id = ? AND b.month = ?
        GROUP BY b.id
    """, (f"{current_month_str}%", user_id, current_month_str))
    
    budget_alerts = []
    budget_rows = cursor.fetchall()
    total_budget_limit = 0
    total_budget_spent = 0
    for b in budget_rows:
        limit = b["monthly_limit"]
        spent = b["spent"]
        total_budget_limit += limit
        total_budget_spent += spent
        pct = round((spent / limit * 100), 1) if limit > 0 else 0
        if pct >= 80:
            budget_alerts.append({
                "category": b["category"],
                "limit": limit,
                "spent": spent,
                "percentage": pct,
                "status": "danger" if pct >= 100 else "warning"
            })

    # 7. Goals overview
    cursor.execute("""
        SELECT id, name, target_amount, current_amount, deadline, color, icon
        FROM savings_goals
        WHERE user_id = ?
        ORDER BY (current_amount / target_amount) DESC
        LIMIT 3
    """, (user_id,))
    top_goals = []
    for g_row in cursor.fetchall():
        target = g_row["target_amount"]
        curr = g_row["current_amount"]
        pct = min(100, round((curr / target * 100), 1)) if target > 0 else 0
        top_goals.append({
            "id": g_row["id"],
            "name": g_row["name"],
            "target_amount": target,
            "current_amount": curr,
            "deadline": g_row["deadline"],
            "percentage": pct,
            "color": g_row["color"],
            "icon": g_row["icon"]
        })

    return jsonify({
        "total_balance": round(total_balance, 2),
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "available_savings": round(available_savings, 2),
        "today_spending": round(today_spending, 2),
        "this_month_spending": round(this_month_expense, 2),
        "this_month_income": round(this_month_income, 2),
        "last_month_spending": round(last_month_expense, 2),
        "month_diff_pct": month_diff_pct,
        "recent_transactions": recent_transactions,
        "budget_alerts": budget_alerts,
        "total_budget_limit": round(total_budget_limit, 2),
        "total_budget_spent": round(total_budget_spent, 2),
        "top_goals": top_goals
    })


# --- Transaction Management ---
@app.route("/api/transactions", methods=["GET"])
@auth_required
def list_transactions():
    user_id = g.current_user["id"]
    db = get_db()
    cursor = db.cursor()

    t_type = request.args.get("type", "all").strip().lower()
    category = request.args.get("category", "").strip()
    payment_method = request.args.get("payment_method", "").strip()
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    sort_by = request.args.get("sort_by", "newest").strip().lower()

    query = "SELECT id, type, amount, category, payment_method, date, description, created_at FROM transactions WHERE user_id = ?"
    params = [user_id]

    if t_type in ["income", "expense"]:
        query += " AND type = ?"
        params.append(t_type)

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if payment_method and payment_method != "all":
        query += " AND payment_method = ?"
        params.append(payment_method)

    if search:
        query += " AND (description LIKE ? OR category LIKE ? OR payment_method LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    if sort_by == "oldest":
        query += " ORDER BY date ASC, id ASC"
    elif sort_by == "amount_high":
        query += " ORDER BY amount DESC"
    elif sort_by == "amount_low":
        query += " ORDER BY amount ASC"
    else: # newest
        query += " ORDER BY date DESC, id DESC"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    return jsonify({"transactions": rows, "count": len(rows)})


@app.route("/api/transactions", methods=["POST"])
@auth_required
def add_transaction():
    data = request.get_json() or {}
    t_type = (data.get("type") or "").strip().lower()
    amount = data.get("amount")
    category = (data.get("category") or "").strip()
    payment_method = (data.get("payment_method") or "Cash").strip()
    date_val = (data.get("date") or "").strip()
    description = (data.get("description") or "").strip()

    # Validation
    if t_type not in ["income", "expense"]:
        return jsonify({"error": "Type must be either 'income' or 'expense'."}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be a positive number greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount value."}), 400

    if not category:
        return jsonify({"error": "Category is required."}), 400

    if not date_val:
        return jsonify({"error": "Date is required."}), 400

    try:
        datetime.strptime(date_val, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Date format must be YYYY-MM-DD."}), 400

    if not description:
        description = f"{category} ({t_type.capitalize()})"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO transactions (user_id, type, amount, category, payment_method, date, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (g.current_user["id"], t_type, amount, category, payment_method, date_val, description))
    new_id = cursor.lastrowid
    db.commit()

    return jsonify({
        "message": f"{t_type.capitalize()} of {amount} added successfully!",
        "transaction": {
            "id": new_id,
            "type": t_type,
            "amount": amount,
            "category": category,
            "payment_method": payment_method,
            "date": date_val,
            "description": description
        }
    }), 201


@app.route("/api/transactions/<int:tx_id>", methods=["PUT"])
@auth_required
def update_transaction(tx_id):
    data = request.get_json() or {}
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", (tx_id, g.current_user["id"]))
    existing = cursor.fetchone()
    if not existing:
        return jsonify({"error": "Transaction not found or unauthorized."}), 404

    t_type = (data.get("type") or existing["type"]).strip().lower()
    amount = data.get("amount", existing["amount"])
    category = (data.get("category") or existing["category"]).strip()
    payment_method = (data.get("payment_method") or existing["payment_method"]).strip()
    date_val = (data.get("date") or existing["date"]).strip()
    description = (data.get("description") or existing["description"]).strip()

    if t_type not in ["income", "expense"]:
        return jsonify({"error": "Type must be 'income' or 'expense'."}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount value."}), 400

    try:
        datetime.strptime(date_val, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    cursor.execute("""
        UPDATE transactions
        SET type = ?, amount = ?, category = ?, payment_method = ?, date = ?, description = ?
        WHERE id = ? AND user_id = ?
    """, (t_type, amount, category, payment_method, date_val, description, tx_id, g.current_user["id"]))
    db.commit()

    return jsonify({
        "message": "Transaction updated successfully!",
        "transaction": {
            "id": tx_id,
            "type": t_type,
            "amount": amount,
            "category": category,
            "payment_method": payment_method,
            "date": date_val,
            "description": description
        }
    })


@app.route("/api/transactions/<int:tx_id>", methods=["DELETE"])
@auth_required
def delete_transaction(tx_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, g.current_user["id"]))
    if not cursor.fetchone():
        return jsonify({"error": "Transaction not found or unauthorized."}), 404

    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, g.current_user["id"]))
    db.commit()
    return jsonify({"message": "Transaction deleted successfully."})


# --- Budget Management ---
@app.route("/api/budgets", methods=["GET"])
@auth_required
def get_budgets():
    user_id = g.current_user["id"]
    month = request.args.get("month", datetime.now().strftime("%Y-%m")).strip()
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.id, b.category, b.monthly_limit, b.month,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b
        LEFT JOIN transactions t ON t.user_id = b.user_id 
             AND t.category = b.category 
             AND t.type = 'expense' 
             AND t.date LIKE ?
        WHERE b.user_id = ? AND b.month = ?
        GROUP BY b.id
        ORDER BY b.monthly_limit DESC
    """, (f"{month}%", user_id, month))
    
    budgets = []
    total_limit = 0
    total_spent = 0

    for row in cursor.fetchall():
        limit = row["monthly_limit"]
        spent = row["spent"]
        remaining = max(0, limit - spent)
        pct = round((spent / limit * 100), 1) if limit > 0 else 0
        total_limit += limit
        total_spent += spent

        status = "safe"
        if pct >= 100:
            status = "danger"
        elif pct >= 80:
            status = "warning"

        budgets.append({
            "id": row["id"],
            "category": row["category"],
            "monthly_limit": limit,
            "month": row["month"],
            "spent": round(spent, 2),
            "remaining": round(remaining, 2),
            "percentage": pct,
            "status": status
        })

    overall_pct = round((total_spent / total_limit * 100), 1) if total_limit > 0 else 0

    return jsonify({
        "month": month,
        "budgets": budgets,
        "total_limit": round(total_limit, 2),
        "total_spent": round(total_spent, 2),
        "total_remaining": round(max(0, total_limit - total_spent), 2),
        "overall_percentage": overall_pct
    })


@app.route("/api/budgets", methods=["POST"])
@auth_required
def save_budget():
    data = request.get_json() or {}
    category = (data.get("category") or "").strip()
    limit = data.get("monthly_limit")
    month = (data.get("month") or datetime.now().strftime("%Y-%m")).strip()

    if not category:
        return jsonify({"error": "Category is required."}), 400

    try:
        limit = float(limit)
        if limit <= 0:
            return jsonify({"error": "Budget limit must be greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid monthly limit."}), 400

    db = get_db()
    cursor = db.cursor()

    # Upsert budget
    cursor.execute("""
        INSERT INTO budgets (user_id, category, monthly_limit, month)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, category, month) DO UPDATE SET
            monthly_limit = excluded.monthly_limit
    """, (g.current_user["id"], category, limit, month))
    db.commit()

    return jsonify({"message": f"Budget for {category} set to {limit} for {month}."})


@app.route("/api/budgets/<int:budget_id>", methods=["DELETE"])
@auth_required
def delete_budget(budget_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM budgets WHERE id = ? AND user_id = ?", (budget_id, g.current_user["id"]))
    if not cursor.fetchone():
        return jsonify({"error": "Budget not found or unauthorized."}), 404

    cursor.execute("DELETE FROM budgets WHERE id = ? AND user_id = ?", (budget_id, g.current_user["id"]))
    db.commit()
    return jsonify({"message": "Budget deleted successfully."})


# --- Savings Goals ---
@app.route("/api/goals", methods=["GET"])
@auth_required
def get_goals():
    user_id = g.current_user["id"]
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, name, target_amount, current_amount, deadline, color, icon, created_at
        FROM savings_goals
        WHERE user_id = ?
        ORDER BY (current_amount / target_amount) DESC, id DESC
    """, (user_id,))
    
    goals = []
    today = datetime.now().date()

    for r in cursor.fetchall():
        target = r["target_amount"]
        curr = r["current_amount"]
        pct = min(100, round((curr / target * 100), 1)) if target > 0 else 0
        remaining = max(0, target - curr)
        
        days_left = None
        if r["deadline"]:
            try:
                deadline_date = datetime.strptime(r["deadline"], "%Y-%m-%d").date()
                days_left = (deadline_date - today).days
            except ValueError:
                pass

        goals.append({
            "id": r["id"],
            "name": r["name"],
            "target_amount": target,
            "current_amount": curr,
            "remaining_amount": round(remaining, 2),
            "percentage": pct,
            "deadline": r["deadline"],
            "days_left": days_left,
            "color": r["color"] or "#10B981",
            "icon": r["icon"] or "fa-piggy-bank",
            "is_completed": curr >= target
        })

    return jsonify({"goals": goals})


@app.route("/api/goals", methods=["POST"])
@auth_required
def create_goal():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    target_amount = data.get("target_amount")
    current_amount = data.get("current_amount", 0)
    deadline = (data.get("deadline") or "").strip()
    color = (data.get("color") or "#10B981").strip()
    icon = (data.get("icon") or "fa-piggy-bank").strip()

    if not name:
        return jsonify({"error": "Goal name is required."}), 400

    try:
        target_amount = float(target_amount)
        if target_amount <= 0:
            return jsonify({"error": "Target amount must be greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid target amount."}), 400

    try:
        current_amount = float(current_amount or 0)
        if current_amount < 0:
            return jsonify({"error": "Current amount cannot be negative."}), 400
    except (ValueError, TypeError):
        current_amount = 0

    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Deadline must be YYYY-MM-DD."}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO savings_goals (user_id, name, target_amount, current_amount, deadline, color, icon)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (g.current_user["id"], name, target_amount, current_amount, deadline or None, color, icon))
    goal_id = cursor.lastrowid
    db.commit()

    return jsonify({"message": f"Savings goal '{name}' created successfully!", "id": goal_id}), 201


@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
@auth_required
def update_goal(goal_id):
    data = request.get_json() or {}
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, g.current_user["id"]))
    existing = cursor.fetchone()
    if not existing:
        return jsonify({"error": "Goal not found."}), 404

    name = (data.get("name") or existing["name"]).strip()
    target_amount = float(data.get("target_amount", existing["target_amount"]))
    current_amount = float(data.get("current_amount", existing["current_amount"]))
    deadline = data.get("deadline", existing["deadline"])
    color = data.get("color", existing["color"])
    icon = data.get("icon", existing["icon"])

    cursor.execute("""
        UPDATE savings_goals
        SET name = ?, target_amount = ?, current_amount = ?, deadline = ?, color = ?, icon = ?
        WHERE id = ? AND user_id = ?
    """, (name, target_amount, current_amount, deadline, color, icon, goal_id, g.current_user["id"]))
    db.commit()

    return jsonify({"message": "Goal updated successfully!"})


@app.route("/api/goals/<int:goal_id>/deposit", methods=["POST"])
@auth_required
def deposit_goal(goal_id):
    data = request.get_json() or {}
    action = data.get("action", "deposit") # 'deposit' or 'withdraw'
    amount = data.get("amount")

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount."}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, g.current_user["id"]))
    goal = cursor.fetchone()
    if not goal:
        return jsonify({"error": "Goal not found."}), 404

    curr = goal["current_amount"]
    if action == "deposit":
        new_amt = curr + amount
    elif action == "withdraw":
        if amount > curr:
            return jsonify({"error": "Cannot withdraw more than current saved amount."}), 400
        new_amt = curr - amount
    else:
        return jsonify({"error": "Action must be deposit or withdraw."}), 400

    cursor.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (new_amt, goal_id))
    db.commit()

    target = goal["target_amount"]
    pct = round((new_amt / target * 100), 1) if target > 0 else 0

    return jsonify({
        "message": f"Successfully {action}ed {amount}!",
        "current_amount": round(new_amt, 2),
        "percentage": min(100, pct),
        "is_completed": new_amt >= target
    })


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@auth_required
def delete_goal(goal_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, g.current_user["id"]))
    if not cursor.fetchone():
        return jsonify({"error": "Goal not found."}), 404

    cursor.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, g.current_user["id"]))
    db.commit()
    return jsonify({"message": "Savings goal deleted."})


# --- Analytics & Reports ---
@app.route("/api/analytics", methods=["GET"])
@auth_required
def get_analytics():
    user_id = g.current_user["id"]
    db = get_db()
    cursor = db.cursor()

    month = request.args.get("month", datetime.now().strftime("%Y-%m")).strip()

    # 1. Income vs Expense for last 6 months
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', date) as m_label,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as inc,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as exp
        FROM transactions
        WHERE user_id = ?
        GROUP BY m_label
        ORDER BY m_label DESC
        LIMIT 6
    """, (user_id,))
    rows = cursor.fetchall()
    # Reverse to chronological order
    rows = list(reversed(rows))
    months_labels = [r["m_label"] for r in rows]
    months_income = [round(r["inc"], 2) for r in rows]
    months_expense = [round(r["exp"], 2) for r in rows]
    months_savings = [round(max(0, r["inc"] - r["exp"]), 2) for r in rows]

    # 2. Category breakdown for selected month
    cursor.execute("""
        SELECT category, SUM(amount) as cat_total
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date LIKE ?
        GROUP BY category
        ORDER BY cat_total DESC
    """, (user_id, f"{month}%"))
    cat_rows = cursor.fetchall()
    cat_labels = [r["category"] for r in cat_rows]
    cat_amounts = [round(r["cat_total"], 2) for r in cat_rows]

    # 3. Payment Method breakdown for selected month
    cursor.execute("""
        SELECT COALESCE(payment_method, 'Other') as p_method, SUM(amount) as p_total
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date LIKE ?
        GROUP BY p_method
        ORDER BY p_total DESC
    """, (user_id, f"{month}%"))
    pay_rows = cursor.fetchall()
    pay_labels = [r["p_method"] for r in pay_rows]
    pay_amounts = [round(r["p_total"], 2) for r in pay_rows]

    # 4. Daily spending in current month
    cursor.execute("""
        SELECT date, SUM(amount) as daily_sum
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date LIKE ?
        GROUP BY date
        ORDER BY date ASC
    """, (user_id, f"{month}%"))
    daily_rows = cursor.fetchall()
    daily_labels = [r["date"].split("-")[-1] for r in daily_rows] # just day of month
    daily_amounts = [round(r["daily_sum"], 2) for r in daily_rows]

    # Summary metrics
    total_exp = sum(cat_amounts)
    avg_daily = round(total_exp / max(1, len(daily_rows)), 2) if daily_rows else 0
    highest_day = max(daily_rows, key=lambda x: x["daily_sum"])["date"] if daily_rows else None

    return jsonify({
        "month": month,
        "monthly_trend": {
            "labels": months_labels,
            "income": months_income,
            "expense": months_expense,
            "savings": months_savings
        },
        "category_breakdown": {
            "labels": cat_labels,
            "amounts": cat_amounts
        },
        "payment_methods": {
            "labels": pay_labels,
            "amounts": pay_amounts
        },
        "daily_trend": {
            "labels": daily_labels,
            "amounts": daily_amounts
        },
        "summary": {
            "total_expenses": round(total_exp, 2),
            "average_daily_spend": avg_daily,
            "highest_spending_day": highest_day
        }
    })


# --- Smart Insights API ---
@app.route("/api/smart-insights", methods=["GET"])
@auth_required
def smart_insights_endpoint():
    month = request.args.get("month", datetime.now().strftime("%Y-%m")).strip()
    db = get_db()
    insights = get_insights(db, g.current_user["id"], month)
    return jsonify(insights)


# --- CSV Export API ---
@app.route("/api/export", methods=["GET"])
@auth_required
def export_transactions():
    user_id = g.current_user["id"]
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT date, type, category, description, payment_method, amount
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
    """, (user_id,))
    rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Category", "Description", "Payment Method", f"Amount ({g.current_user['currency']})"])
    
    for r in rows:
        writer.writerow([r["date"], r["type"].upper(), r["category"], r["description"], r["payment_method"], r["amount"]])

    filename = f"SmartSpend_Transactions_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


if __name__ == "__main__":
    print("=" * 60)
    print(" SmartSpend Backend Server Starting on http://127.0.0.1:5000 ")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
