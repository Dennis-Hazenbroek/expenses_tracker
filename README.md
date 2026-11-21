# Budget Tracker

A local web app for tracking income, expenses, and your current balance in
British pounds (GBP). It saves transactions to `expenses.json` and supports CSV
downloads. Existing expense records without a transaction type remain
supported.

Run the app with Python 3:

```sh
python3 expenses.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. The
dashboard updates as soon as an income or expense is added. Stop the server
with Ctrl+C.

Run the tests with:

```sh
python3 -m unittest -v
```
