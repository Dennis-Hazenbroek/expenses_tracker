import csv
import io
import json
import tempfile
import threading
import unittest
from decimal import Decimal
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import expenses


class TransactionTotalsTests(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            {
                "title": "Salary",
                "amount": 2500.00,
                "category": "Work",
                "date": "2026-11-01",
                "type": "income",
            },
            {
                "title": "Groceries",
                "amount": 21.0,
                "category": "Food Shopping",
                "date": "2026-11",
            },
            {
                "title": "Rent",
                "amount": "900.00",
                "category": "Housing",
                "date": "2026-10-31",
                "type": "expense",
            },
        ]

    def test_legacy_expenses_are_counted_and_balance_is_calculated(self):
        income, total_expenses = expenses.transaction_totals(self.transactions)

        self.assertEqual(income, Decimal("2500.00"))
        self.assertEqual(total_expenses, Decimal("921.00"))
        self.assertEqual(income - total_expenses, Decimal("1579.00"))

    def test_monthly_totals_include_income_expenses_and_count(self):
        income, total_expenses, count = expenses.monthly_totals(
            "2026-11", self.transactions
        )

        self.assertEqual(income, Decimal("2500.00"))
        self.assertEqual(total_expenses, Decimal("21.00"))
        self.assertEqual(count, 2)


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.original_transactions = expenses.transactions
        self.temp_directory = tempfile.TemporaryDirectory()
        self.file_patch = patch.object(
            expenses,
            "FILE_NAME",
            Path(self.temp_directory.name) / "transactions.json",
        )
        self.file_patch.start()
        expenses.transactions = [
            {
                "title": "Groceries",
                "amount": 21.0,
                "category": "Food",
                "date": "2026-11-20",
            }
        ]

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), expenses.BudgetHandler
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.server_thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        expenses.transactions = self.original_transactions
        self.file_patch.stop()
        self.temp_directory.cleanup()

    def request_json(self, path, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with urlopen(request) as response:
            return response.status, json.load(response)

    def test_income_and_expense_responses_refresh_balance(self):
        status, after_income = self.request_json(
            "/api/transactions",
            "POST",
            {
                "type": "income",
                "title": "Pay",
                "amount": "1200.00",
                "category": "Work",
                "date": "2026-11-20",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(after_income["balance"], "1179.00")

        _, after_expense = self.request_json(
            "/api/transactions",
            "POST",
            {
                "type": "expense",
                "title": "Fuel",
                "amount": "4.32",
                "category": "Transport",
                "date": "2026-11-20",
            },
        )
        self.assertEqual(after_expense["balance"], "1174.68")

        _, persisted = self.request_json("/api/transactions")
        self.assertEqual(persisted["balance"], "1174.68")
        self.assertEqual(len(persisted["transactions"]), 3)

    def test_invalid_transaction_is_rejected_without_changing_balance(self):
        request = Request(
            f"{self.base_url}/api/transactions",
            data=json.dumps(
                {
                    "type": "expense",
                    "title": "Invalid",
                    "amount": "-5",
                    "category": "Other",
                    "date": "2026-11-20",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 400)

        _, dashboard = self.request_json("/api/transactions")
        self.assertEqual(dashboard["balance"], "-21.00")

    def test_homepage_and_csv_download_are_served(self):
        with urlopen(self.base_url) as response:
            page = response.read().decode("utf-8")
        self.assertIn("Add transaction", page)
        self.assertIn(">£</span>", page)
        self.assertIn('currency: "GBP"', page)
        self.assertIn('form.addEventListener("submit"', page)

        with urlopen(f"{self.base_url}/api/export.csv") as response:
            rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))
        self.assertEqual(rows[0]["current_balance"], "-21.00")


if __name__ == "__main__":
    unittest.main()
