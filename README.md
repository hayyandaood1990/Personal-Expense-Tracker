### Personal Expense Tracker

A Frappe v16 app for tracking personal expenses, budgets, categories, and exchange-rate based currency conversion.

### Installation

```bash
cd /home/frappe/frappe-bench
bench get-app /path/to/personal_expense_tracker
bench --site your-site-name install-app personal_expense_tracker
bench --site your-site-name migrate
```

For the local app already created in this bench:

```bash
cd /home/frappe/frappe-bench
bench --site your-site-name install-app personal_expense_tracker
bench --site your-site-name migrate
```

### Dummy Data

The installer creates default roles, categories, placeholder exchange rates, sample budgets, and sample expenses.
To load or refresh dummy records for a specific user:

```bash
bench --site your-site-name execute personal_expense_tracker.install.create_dummy_data --kwargs "{'user': 'user@example.com'}"
```

### License

mit


Implemented personal_expense_tracker as a full Frappe v16 app and installed it on developer-test.

What’s Included


App created at /home/frappe/frappe-bench/apps/personal_expense_tracker

DocTypes:

Expense Category

Expense Entry

Currency Exchange Rate

Monthly Budget




Roles:

Expense User

Expense Manager




Permission query conditions so normal users only see their own Expense Entry and Monthly Budget

Client scripts for exchange-rate fetching and base amount calculation

Whitelisted APIs in api.py

Script Reports:

Monthly Expense Summary

Category Expense Summary

Currency Exposure Report




Workspace: Personal Expenses

Dashboard: Personal Expenses

Number Cards and Dashboard Charts as fixtures

Dummy categories, exchange rates, budgets, and expenses via installer


Key Files


hooks.py

install.py

permissions.py

utils.py

DocTypes under personal_expense_tracker/personal_expense_tracker/doctype/

Reports under personal_expense_tracker/personal_expense_tracker/report/

Fixtures under personal_expense_tracker/fixtures/


Commands

bash



cd /home/frappe/frappe-bench
bench new-app --no-git personal_expense_tracker
bench --site developer-test install-app personal_expense_tracker
bench --site developer-test migrate



Load or refresh dummy data:

bash



bench --site developer-test execute personal_expense_tracker.install.create_dummy_data --kwargs "{'user':'Administrator'}"



Verified


App installed on developer-test

bench --site developer-test migrate succeeds

10 categories seeded

6 sample expenses seeded

Workspace and Dashboard exist

4 number cards and 3 dashboard charts synced

Reports and APIs run successfully

Monthly Budget Expense User permissions are create/read/write, delete disabled as requested.