from datetime import datetime, timedelta
import calendar

def get_insights(db, user_id, current_month=None):
    """
    Computes complete smart financial insights, anomaly detection,
    personalized savings suggestions, and health score for a given user.
    """
    if not current_month:
        current_month = datetime.now().strftime("%Y-%m")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Fetch all transactions for this user
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, type, amount, category, payment_method, date, description
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC
    """, (user_id,))
    all_tx = [dict(row) for row in cursor.fetchall()]

    # If no transactions yet, return sensible defaults
    if not all_tx:
        return {
            "health_score": 50,
            "health_grade": "Getting Started",
            "health_color": "#6366F1",
            "health_factors": {
                "savings_rate": 0,
                "budget_adherence": 100,
                "expense_ratio": 0,
                "goals_progress": 0
            },
            "anomalies": [],
            "suggestions": [
                {
                    "title": "Welcome to SmartSpend!",
                    "type": "tip",
                    "icon": "fa-sparkles",
                    "message": "Start by recording your first income and daily expenses to unlock smart AI-driven financial insights!"
                }
            ],
            "rule_50_30_20": {
                "needs": {"amount": 0, "percent": 0, "recommended": 50},
                "wants": {"amount": 0, "percent": 0, "recommended": 30},
                "savings": {"amount": 0, "percent": 0, "recommended": 20}
            },
            "summaries": {
                "today_spending": 0,
                "this_week_spending": 0,
                "last_week_spending": 0,
                "this_month_spending": 0,
                "last_month_spending": 0,
                "this_month_income": 0,
                "savings_rate": 0
            },
            "top_category": None
        }

    # Helper date boundaries
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)
    
    # Filter by timeframe
    this_month_tx = [tx for tx in all_tx if tx["date"].startswith(current_month)]
    
    # Previous month string
    first_of_month = datetime.strptime(f"{current_month}-01", "%Y-%m-%d").date()
    last_month_end = first_of_month - timedelta(days=1)
    last_month_str = last_month_end.strftime("%Y-%m")
    last_month_tx = [tx for tx in all_tx if tx["date"].startswith(last_month_str)]

    # Spending metrics
    today_spending = sum(tx["amount"] for tx in all_tx if tx["type"] == "expense" and tx["date"] == today_str)
    
    this_week_spending = sum(
        tx["amount"] for tx in all_tx 
        if tx["type"] == "expense" and start_of_week.strftime("%Y-%m-%d") <= tx["date"] <= today_str
    )
    
    last_week_spending = sum(
        tx["amount"] for tx in all_tx 
        if tx["type"] == "expense" and start_of_last_week.strftime("%Y-%m-%d") <= tx["date"] <= end_of_last_week.strftime("%Y-%m-%d")
    )

    this_month_income = sum(tx["amount"] for tx in this_month_tx if tx["type"] == "income")
    this_month_expense = sum(tx["amount"] for tx in this_month_tx if tx["type"] == "expense")
    last_month_expense = sum(tx["amount"] for tx in last_month_tx if tx["type"] == "expense")
    
    # Net savings for current month
    this_month_savings = max(0, this_month_income - this_month_expense)
    savings_rate = round((this_month_savings / this_month_income * 100), 1) if this_month_income > 0 else 0

    # 2. Category Breakdown for current month
    category_totals = {}
    for tx in this_month_tx:
        if tx["type"] == "expense":
            cat = tx["category"]
            category_totals[cat] = category_totals.get(cat, 0) + tx["amount"]

    top_category = None
    if category_totals:
        top_cat_name = max(category_totals, key=category_totals.get)
        top_cat_amount = category_totals[top_cat_name]
        top_cat_pct = round((top_cat_amount / this_month_expense * 100), 1) if this_month_expense > 0 else 0
        top_category = {
            "category": top_cat_name,
            "amount": top_cat_amount,
            "percentage": top_cat_pct,
            "potential_saving_10pct": round(top_cat_amount * 0.10, 2)
        }

    # 3. 50/30/20 Rule Breakdown
    # Needs: Food, Bills, Health, Education
    # Wants: Shopping, Entertainment, Travel, Other
    needs_categories = {"Food", "Bills", "Health", "Education"}
    wants_categories = {"Shopping", "Entertainment", "Travel", "Other"}

    needs_total = sum(amt for cat, amt in category_totals.items() if cat in needs_categories)
    wants_total = sum(amt for cat, amt in category_totals.items() if cat in wants_categories)
    
    effective_income = this_month_income if this_month_income > 0 else this_month_expense
    needs_pct = round((needs_total / effective_income * 100), 1) if effective_income > 0 else 0
    wants_pct = round((wants_total / effective_income * 100), 1) if effective_income > 0 else 0
    savings_pct = round((max(0, this_month_income - this_month_expense) / effective_income * 100), 1) if effective_income > 0 else 0

    # 4. Fetch Budgets & Check limits
    cursor.execute("""
        SELECT id, category, monthly_limit
        FROM budgets
        WHERE user_id = ? AND month = ?
    """, (user_id, current_month))
    budgets = [dict(row) for row in cursor.fetchall()]

    budget_warnings = []
    budget_adherence_score = 35 # Max points
    overbudget_count = 0

    for b in budgets:
        cat = b["category"]
        limit = b["monthly_limit"]
        spent = category_totals.get(cat, 0)
        pct = round((spent / limit * 100), 1) if limit > 0 else 0
        
        if pct >= 100:
            overbudget_count += 1
            budget_warnings.append({
                "type": "danger",
                "category": cat,
                "spent": spent,
                "limit": limit,
                "percent": pct,
                "message": f"Over budget in {cat}! You spent {pct}% of your limit."
            })
        elif pct >= 80:
            budget_warnings.append({
                "type": "warning",
                "category": cat,
                "spent": spent,
                "limit": limit,
                "percent": pct,
                "message": f"Warning: {cat} spending has reached {pct}% of limit."
            })

    # Adherence score penalty
    if budgets:
        budget_adherence_score = max(0, 35 - (overbudget_count * 12))

    # 5. Fetch Savings Goals
    cursor.execute("""
        SELECT id, name, target_amount, current_amount, deadline
        FROM savings_goals
        WHERE user_id = ?
    """, (user_id,))
    goals = [dict(row) for row in cursor.fetchall()]
    goals_progress_score = 0
    if goals:
        total_target = sum(g["target_amount"] for g in goals)
        total_saved = sum(g["current_amount"] for g in goals)
        goals_progress_score = min(10, round((total_saved / total_target * 10), 1)) if total_target > 0 else 5

    # 6. Calculate Financial Health Score (0 - 100)
    # Savings Rate: up to 35 points (target 20% savings gives 35)
    savings_score = min(35, max(0, round(savings_rate * 1.75, 1)))
    
    # Expense Ratio: up to 20 points (target <= 70% of income spent gives 20)
    if this_month_income > 0:
        ratio = (this_month_expense / this_month_income) * 100
        if ratio <= 60:
            expense_ratio_score = 20
        elif ratio <= 80:
            expense_ratio_score = 15
        elif ratio <= 100:
            expense_ratio_score = 8
        else:
            expense_ratio_score = 0
    else:
        expense_ratio_score = 10

    total_score = int(round(savings_score + budget_adherence_score + expense_ratio_score + goals_progress_score))
    total_score = max(5, min(100, total_score))

    if total_score >= 85:
        health_grade = "Financial Master"
        health_color = "#10B981"
    elif total_score >= 70:
        health_grade = "Healthy & Growing"
        health_color = "#3B82F6"
    elif total_score >= 50:
        health_grade = "Moderate Balance"
        health_color = "#F59E0B"
    else:
        health_grade = "Needs Attention"
        health_color = "#EF4444"

    # 7. Anomaly Detection
    # Calculate category averages over all time
    category_all_expenses = {}
    for tx in all_tx:
        if tx["type"] == "expense":
            cat = tx["category"]
            if cat not in category_all_expenses:
                category_all_expenses[cat] = []
            category_all_expenses[cat].append(tx["amount"])

    anomalies = []
    # Check current month transactions for spikes > 2x average
    for tx in this_month_tx:
        if tx["type"] == "expense":
            cat = tx["category"]
            amounts = category_all_expenses.get(cat, [])
            if len(amounts) >= 3:
                avg_cat = sum(amounts) / len(amounts)
                if tx["amount"] >= (2.0 * avg_cat) and tx["amount"] > 500:
                    anomalies.append({
                        "id": tx["id"],
                        "description": tx["description"],
                        "category": cat,
                        "amount": tx["amount"],
                        "date": tx["date"],
                        "average": round(avg_cat, 2),
                        "multiplier": round(tx["amount"] / avg_cat, 1),
                        "reason": f"Spike of {round(tx['amount'] / avg_cat, 1)}x above your normal {cat} expense average."
                    })

    # Limit to latest 3 anomalies
    anomalies = anomalies[:3]

    # 8. Generate Personalized Actionable Recommendations
    suggestions = []

    # Savings suggestion
    if savings_rate >= 20:
        suggestions.append({
            "title": "Strong Savings Discipline",
            "type": "success",
            "icon": "fa-award",
            "message": f"Great job! Your current savings rate is {savings_rate}%, beating the recommended 20% benchmark. Consider allocating surplus to long-term goals."
        })
    elif savings_rate > 0:
        suggestions.append({
            "title": "Boost Your Savings Buffer",
            "type": "tip",
            "icon": "fa-piggy-bank",
            "message": f"Your savings rate is {savings_rate}%. Try bumping it up to 20% by cutting small discretionary costs."
        })
    elif this_month_expense > this_month_income and this_month_income > 0:
        suggestions.append({
            "title": "Deficit Alert",
            "type": "danger",
            "icon": "fa-triangle-exclamation",
            "message": f"Expenses exceed income by {round(this_month_expense - this_month_income, 2)} this month. Review non-essential spending immediately."
        })

    # 50/30/20 suggestion
    if wants_pct > 35:
        suggestions.append({
            "title": "Discretionary Spending High",
            "type": "warning",
            "icon": "fa-bag-shopping",
            "message": f"Wants (Shopping, Entertainment, Travel) take up {wants_pct}% of your funds (recommended is under 30%). Delaying impulsive purchases can save you significant cash."
        })

    # Top category suggestion
    if top_category and top_category["percentage"] >= 30:
        suggestions.append({
            "title": f"Optimize {top_category['category']} Spend",
            "type": "info",
            "icon": "fa-chart-pie",
            "message": f"{top_category['category']} accounts for {top_category['percentage']}% of your expenses. Trimming just 10% can save you ~{top_category['potential_saving_10pct']} this month."
        })

    # Budget warning suggestions
    for bw in budget_warnings:
        suggestions.append({
            "title": f"Budget Alert: {bw['category']}",
            "type": bw["type"],
            "icon": "fa-bell",
            "message": bw["message"]
        })

    # Payment method habit check
    upi_card_tx = [tx for tx in this_month_tx if tx["type"] == "expense" and tx.get("payment_method") in ["UPI", "Card"]]
    if len(this_month_tx) >= 5 and (len(upi_card_tx) / len(this_month_tx)) >= 0.7:
        suggestions.append({
            "title": "Mindful Digital Payments",
            "type": "tip",
            "icon": "fa-mobile-screen-button",
            "message": "Over 70% of your expenses are digital (UPI/Card). Studies show digital tap-and-pay leads to 12% more impulse buys. Track small frequent spends!"
        })

    return {
        "health_score": total_score,
        "health_grade": health_grade,
        "health_color": health_color,
        "health_factors": {
            "savings_rate": savings_score,
            "budget_adherence": budget_adherence_score,
            "expense_ratio": expense_ratio_score,
            "goals_progress": goals_progress_score
        },
        "anomalies": anomalies,
        "suggestions": suggestions,
        "rule_50_30_20": {
            "needs": {"amount": round(needs_total, 2), "percent": needs_pct, "recommended": 50},
            "wants": {"amount": round(wants_total, 2), "percent": wants_pct, "recommended": 30},
            "savings": {"amount": round(this_month_savings, 2), "percent": savings_pct, "recommended": 20}
        },
        "summaries": {
            "today_spending": round(today_spending, 2),
            "this_week_spending": round(this_week_spending, 2),
            "last_week_spending": round(last_week_spending, 2),
            "this_month_spending": round(this_month_expense, 2),
            "last_month_spending": round(last_month_expense, 2),
            "this_month_income": round(this_month_income, 2),
            "savings_rate": savings_rate
        },
        "top_category": top_category,
        "budget_warnings": budget_warnings
    }
