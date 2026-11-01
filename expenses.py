#! /usr/bin/env python3
import json
import os
from datetime import date
import csv

expenses = []
FILE_NAME = "expenses.json"

def load_expenses():
  global expenses

  if os.path.exists(FILE_NAME):
      with open(FILE_NAME, "r", encoding="utf-8") as file:
          expenses = json.load(file)
          print("Expenses loaded successfully!")

def save_expenses():
    with open(FILE_NAME, "w", encoding="utf-8") as file:
        json.dump(expenses, file, indent=4)

def add_expense():
    title = input("Enter expense title: ")
    amount = float(input("Enter expense amount: "))

    if amount <= 0:
        print("Amount must be greater than zero. Expense not added.")
    
    category = input("Enter expense category: ")
   # date = input("Enter expense date (YYYY-MM-DD) or leave blank for today: ")
    
    expense = {
        "title": title,
        "amount": amount,
        "category": category,
        "date": date.today().strftime("%Y-%m")
    }
    
    expenses.append(expense)
    save_expenses_to_file()
    
    print("Expense added successfully!")

def view_expenses():
    if not expenses:
        print("No expenses recorded.")
        return

    for expense in expenses:
        print(f"Title: {expense['title']}, Amount: {expense['amount']}, Category: {expense['category']}")

def total_expenses():
    total = 0

    for expense in expenses:
        total = total + expense['amount']

    print(f"Total expenses: {total}")

def category_total():
    category = input("Enter category to calculate total: ")
    total = 0

    for expense in expenses:
        if expense['category'].lower() == category.lower():
            total = total + expense['amount']

    print(f"Total expenses for category '{category}': {total}")

def save_expenses_to_file():
    with open(FILE_NAME, "w", encoding="utf-8") as file:
        json.dump(expenses, file, indent=4)

load_expenses()

def expense_report():
    if not expenses:
        print("No Expenses Recorded.")
        return

    amounts = [expense['amount'] for expense in expenses]

    print("Total: ", sum(amounts))
    print("Average: ", round(sum(amounts) / len(amounts), 2))
    print("Highest: ", max(amounts))
    print("Lowest: ", min(amounts))

def category_report():
    if not expenses:
        print("No Expenses Recorded.")
        return

    today = date.today()
    totals = {}

    for expense in expenses:
        category = expense['category']
        amount = expense['amount']

        if category in totals:
            totals[category] += amount
        else:
            totals[category] = amount

    print("\n--- Category Report ----")
    print("Date: ", today.strftime("%Y-%m"))
    for category, total in totals.items():
        print(category, ":", total, "USD")

def monthly_report():
    month = input("Enter Month (YYYY-MM): ").strip()

    total = 0
    count = 0

    for expense in expenses:
        if expense.get("date", "").startswith(month):
            total += expense["amount"]
            count += 1

    print("Month: ", month)
    print("Number of expenses: ", count)
    print("Total Spending: ", total)

def export_csv():
    if not expenses:
        print("No Expenses to Export!")
        return

    with open("expenses.csv", "w", newline="", encoding="utf-8") as file:
        fieldnames = ["title", 'amount', "category", "date"]

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for expense in expenses:
            writer.writerow({
                "title": expense.get("title", ""),
                "amount": expense.get("amount", ""),
                "category": expense.get("category", ""),
                "date": expense.get("date", ""),
            })

    print("Expenses exported to expenses.csv file successfuly!")

def main():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as file:
            global expenses
            expenses = json.load(file)

    while True:
        print("\nExpense Tracker Menu:")
        print("1. Add Expense")
        print("2. View Expenses")
        print("3. Total Expenses")
        print("4. Category Total")
        print("5. Expense Report")
        print("6. Expense By Category Report")
        print("7. Monthly Report")
        print("8. Export CSV")
        print("9. Exit")

        choice = input("Enter your choice (1-9): ")

        if choice == "1":
            add_expense()
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            total_expenses()
        elif choice == "4":
            category_total()
        elif choice == "5":
            expense_report()
        elif choice == "6":
            category_report()
        elif choice == "7":
            monthly_report()
        elif choice == "8":
            export_csv()
        elif choice == "9":
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please try again.")

main()
