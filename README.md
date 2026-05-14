# Personal Expense Tracker

A Frappe Framework v16 app for personal expense tracking, monthly budgets, categories, and multi-currency conversion.

## Features

- Expense categories with active/inactive status and monthly budget reference
- Expense entries in SYP, USD, and EUR
- Currency exchange rates with effective dates
- Monthly budgets per user, month, year, and category
- Expense User and Expense Manager roles
- Permission filters so normal users only see their own expenses and budgets
- Client-side exchange-rate fetching and base-currency calculation
- Script reports for monthly, category, and currency exposure summaries
- Personal Expenses workspace and dashboard widgets
- Dummy categories, exchange rates, budgets, and sample expenses

## Installation

```bash
cd /home/frappe/frappe-bench
bench get-app https://github.com/hayyandaood1990/Personal-Expense-Tracker.git
bench --site your-site-name install-app personal_expense_tracker
bench --site your-site-name migrate
```

For a local checkout already inside the bench:

```bash
cd /home/frappe/frappe-bench
bench --site your-site-name install-app personal_expense_tracker
bench --site your-site-name migrate
```

## Dummy Data

The installer creates default roles, categories, placeholder exchange rates, sample budgets, and sample expenses.

To reload dummy data for a user:

```bash
bench --site your-site-name execute personal_expense_tracker.install.create_dummy_data --kwargs "{'user': 'user@example.com'}"
```

## Reports

- Monthly Expense Summary
- Category Expense Summary
- Currency Exposure Report

## License

MIT
