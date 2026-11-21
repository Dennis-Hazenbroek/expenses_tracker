#! /usr/bin/env python3
import csv
import io
import json
import threading
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

transactions = []
BASE_DIR = Path(__file__).resolve().parent
FILE_NAME = BASE_DIR / "expenses.json"
HTML_FILE = BASE_DIR / "index.html"
CENT = Decimal("0.01")
HOST = "127.0.0.1"
PORT = 8000
MAX_REQUEST_SIZE = 16_384
transactions_lock = threading.RLock()


def load_transactions():
    global transactions

    if FILE_NAME.exists():
        with FILE_NAME.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, list):
            raise ValueError(f"{FILE_NAME} must contain a JSON list.")
        transactions = loaded


def save_transactions(entries=None):
    entries = transactions if entries is None else entries
    with FILE_NAME.open("w", encoding="utf-8") as file:
        json.dump(entries, file, indent=4)


def amount_of(transaction):
    return Decimal(str(transaction["amount"])).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def format_money(amount):
    return f"{amount:.2f}"


def transaction_totals(entries=None):
    entries = transactions if entries is None else entries
    income = sum(
        (amount_of(entry) for entry in entries if entry.get("type") == "income"),
        Decimal("0.00"),
    )
    expenses = sum(
        (
            amount_of(entry)
            for entry in entries
            if entry.get("type", "expense") == "expense"
        ),
        Decimal("0.00"),
    )
    return income, expenses


def monthly_totals(month, entries=None):
    entries = transactions if entries is None else entries
    matching = [
        entry for entry in entries if entry.get("date", "").startswith(month)
    ]
    income, expenses = transaction_totals(matching)
    return income, expenses, len(matching)


def dashboard_data(entries=None):
    entries = transactions if entries is None else entries
    income, expenses = transaction_totals(entries)
    return {
        "income": format_money(income),
        "expenses": format_money(expenses),
        "balance": format_money(income - expenses),
        "transactions": [
            {
                "type": transaction.get("type", "expense"),
                "title": transaction.get("title", ""),
                "amount": format_money(amount_of(transaction)),
                "category": transaction.get("category", ""),
                "date": transaction.get("date", ""),
            }
            for transaction in reversed(entries)
        ],
    }


def create_transaction(payload):
    if not isinstance(payload, dict):
        raise ValueError("Transaction must be a JSON object.")

    transaction_type = payload.get("type")
    if not isinstance(transaction_type, str) or transaction_type not in {
        "income",
        "expense",
    }:
        raise ValueError("Choose income or expense.")

    title = payload.get("title")
    category = payload.get("category")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Title is required.")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Category is required.")

    try:
        amount = Decimal(str(payload.get("amount", "")).strip())
    except InvalidOperation as error:
        raise ValueError("Enter a valid amount.") from error

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    try:
        rounded_amount = amount.quantize(CENT)
    except InvalidOperation as error:
        raise ValueError("Enter a valid amount.") from error
    if amount != rounded_amount:
        raise ValueError("Amount must have no more than two decimal places.")

    transaction_date = payload.get("date") or date.today().isoformat()
    if not isinstance(transaction_date, str):
        raise ValueError("Enter a valid date.")
    try:
        parsed_date = date.fromisoformat(transaction_date)
    except ValueError as error:
        raise ValueError("Enter a valid date in YYYY-MM-DD format.") from error
    if parsed_date.isoformat() != transaction_date:
        raise ValueError("Enter a valid date in YYYY-MM-DD format.")

    return {
        "type": transaction_type,
        "title": title.strip(),
        "amount": format_money(rounded_amount),
        "category": category.strip(),
        "date": transaction_date,
    }


def add_transaction(payload):
    transaction = create_transaction(payload)
    with transactions_lock:
        updated_transactions = [*transactions, transaction]
        save_transactions(updated_transactions)
        transactions[:] = updated_transactions
        return dashboard_data(transactions)


def csv_content():
    with transactions_lock:
        entries = list(transactions)

    income, expenses = transaction_totals(entries)
    current_balance = format_money(income - expenses)
    output = io.StringIO(newline="")
    fieldnames = [
        "type",
        "title",
        "amount",
        "category",
        "date",
        "current_balance",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for transaction in entries:
        writer.writerow(
            {
                "type": transaction.get("type", "expense"),
                "title": transaction.get("title", ""),
                "amount": format_money(amount_of(transaction)),
                "category": transaction.get("category", ""),
                "date": transaction.get("date", ""),
                "current_balance": current_balance,
            }
        )
    return output.getvalue()


class BudgetHandler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_body(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            try:
                body = HTML_FILE.read_bytes()
            except OSError:
                self.send_json(500, {"error": "Unable to load the web page."})
                return
            self.send_body(status=200, body=body, content_type="text/html; charset=utf-8")
        elif path == "/api/transactions":
            with transactions_lock:
                payload = dashboard_data(transactions)
            self.send_json(200, payload)
        elif path == "/api/export.csv":
            body = csv_content().encode("utf-8")
            self.send_body(
                200,
                body,
                "text/csv; charset=utf-8",
                {"Content-Disposition": 'attachment; filename="expenses.csv"'},
            )
        else:
            self.send_json(404, {"error": "Not found."})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/transactions":
            self.send_json(404, {"error": "Not found."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid request size."})
            return
        if content_length <= 0:
            self.send_json(400, {"error": "Request body is required."})
            return
        if content_length > MAX_REQUEST_SIZE:
            self.send_json(413, {"error": "Request body is too large."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Request body must be valid JSON."})
            return

        try:
            result = add_transaction(payload)
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except OSError:
            self.send_json(500, {"error": "Unable to save the transaction."})
            return

        self.send_json(201, result)


def main():
    load_transactions()
    with ThreadingHTTPServer((HOST, PORT), BudgetHandler) as server:
        print(f"Budget tracker is running at http://{HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nBudget tracker stopped.")


if __name__ == "__main__":
    main()
