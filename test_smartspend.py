import unittest
import json
import os
import sys
from datetime import datetime

# Configure test environment
os.environ["SECRET_KEY"] = "test-secret-key"
from app import app
from database import init_db, get_db

class SmartSpendTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with app.app_context():
            init_db()

    def test_full_user_lifecycle(self):
        print("\n--- Running SmartSpend Integration Tests ---")

        # 1. Test Demo Login / Seeding
        res = self.client.post("/api/auth/demo")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("token", data)
        token = data["token"]
        print("[OK] Demo Login & Seeder")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test Dashboard Stats
        res = self.client.get("/api/dashboard/stats", headers=headers)
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()
        self.assertGreater(stats["total_income"], 0)
        self.assertGreater(stats["total_expense"], 0)
        self.assertIn("available_savings", stats)
        self.assertIn("recent_transactions", stats)
        print(f"[OK] Dashboard Stats: Total Balance = {stats['total_balance']}, Income = {stats['total_income']}, Expense = {stats['total_expense']}")

        # 3. Test Add Income
        today_str = datetime.now().strftime("%Y-%m-%d")
        income_payload = {
            "type": "income",
            "amount": 25000,
            "category": "Salary",
            "payment_method": "Bank Transfer",
            "date": today_str,
            "description": "Bonus Payout"
        }
        res = self.client.post("/api/transactions", json=income_payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        income_tx_id = res.get_json()["transaction"]["id"]
        print(f"[OK] Add Income: ID {income_tx_id} created successfully")

        # 4. Test Add Expense
        expense_payload = {
            "type": "expense",
            "amount": 1450,
            "category": "Food",
            "payment_method": "UPI",
            "date": today_str,
            "description": "Dinner at Olive Garden"
        }
        res = self.client.post("/api/transactions", json=expense_payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        expense_tx_id = res.get_json()["transaction"]["id"]
        print(f"[OK] Add Expense: ID {expense_tx_id} created successfully")

        # 5. Test Transactions Search & Filter
        res = self.client.get("/api/transactions?type=expense&category=Food", headers=headers)
        self.assertEqual(res.status_code, 200)
        food_txs = res.get_json()["transactions"]
        self.assertTrue(any(t["id"] == expense_tx_id for t in food_txs))
        print(f"[OK] Transaction Filters: Found {len(food_txs)} Food expenses")

        # 6. Test Edit Transaction
        edit_payload = {
            "type": "expense",
            "amount": 1600,
            "category": "Food",
            "payment_method": "Card",
            "date": today_str,
            "description": "Dinner at Olive Garden (with dessert)"
        }
        res = self.client.put(f"/api/transactions/{expense_tx_id}", json=edit_payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        print("[OK] Edit Transaction")

        # 7. Test Delete Transaction
        res = self.client.delete(f"/api/transactions/{expense_tx_id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        print("[OK] Delete Transaction")

        # 8. Test Budgets
        current_month = datetime.now().strftime("%Y-%m")
        budget_payload = {
            "category": "Food",
            "monthly_limit": 15000,
            "month": current_month
        }
        res = self.client.post("/api/budgets", json=budget_payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        res = self.client.get(f"/api/budgets?month={current_month}", headers=headers)
        self.assertEqual(res.status_code, 200)
        budgets_data = res.get_json()
        self.assertGreater(len(budgets_data["budgets"]), 0)
        print(f"[OK] Budgets: Category limits verified, overall pct = {budgets_data['overall_percentage']}%")

        # 9. Test Savings Goals & Deposit
        goal_payload = {
            "name": "Tesla Model Y Downpayment",
            "target_amount": 500000,
            "current_amount": 150000,
            "deadline": "2027-12-31",
            "color": "#3B82F6",
            "icon": "fa-car"
        }
        res = self.client.post("/api/goals", json=goal_payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        goal_id = res.get_json()["id"]

        # Deposit to goal
        res = self.client.post(f"/api/goals/{goal_id}/deposit", json={"action": "deposit", "amount": 25000}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["current_amount"], 175000)
        print("[OK] Savings Goals & Deposit")

        # 10. Test Analytics
        res = self.client.get(f"/api/analytics?month={current_month}", headers=headers)
        self.assertEqual(res.status_code, 200)
        analytics = res.get_json()
        self.assertIn("monthly_trend", analytics)
        self.assertIn("category_breakdown", analytics)
        print("[OK] Analytics & Reports")

        # 11. Test Smart Insights & AI Advisor
        res = self.client.get(f"/api/smart-insights?month={current_month}", headers=headers)
        self.assertEqual(res.status_code, 200)
        insights = res.get_json()
        self.assertIn("health_score", insights)
        self.assertIn("rule_50_30_20", insights)
        self.assertIn("suggestions", insights)
        print(f"[OK] Smart Financial Insights: Health Score = {insights['health_score']}/100 ({insights['health_grade']})")

        # 12. Test CSV Export
        res = self.client.get("/api/export", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.content_type)
        print("[OK] CSV Export")

        # 13. Test Negative / Invalid Validation
        invalid_tx = {
            "type": "expense",
            "amount": -500,
            "category": "Food",
            "date": today_str
        }
        res = self.client.post("/api/transactions", json=invalid_tx, headers=headers)
        self.assertEqual(res.status_code, 400)
        print("[OK] Validation check (Negative amounts blocked)")

        print("\nAll integration tests passed successfully!\n")

if __name__ == "__main__":
    unittest.main()
