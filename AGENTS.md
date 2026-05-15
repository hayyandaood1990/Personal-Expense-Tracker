# AGENTS.md

## Project Context

- Bench path: `/home/frappe/frappe-bench`
- App path: `/home/frappe/frappe-bench/apps/personal_expense_tracker`
- Site used during development: `developer-test`
- Framework: Frappe Framework v16
- Internal app/package name: `personal_expense_tracker`
- User-facing app name: `Personal Expense Tracker`
- GitHub repo: `https://github.com/hayyandaood1990/Personal-Expense-Tracker`

This is a Frappe app for personal expense tracking. It lets users record expenses, group them by category, manage monthly budgets, store exchange rates, convert expenses into a base currency, and view dashboards/reports.

## Core Features

- Expense entry tracking with category, amount, currency, payment method, notes, and attachment.
- Supported currencies: `SYP`, `USD`, `EUR`.
- Default base currency: `SYP`.
- Category management with parent categories, active/inactive state, and monthly budget reference.
- Monthly budgets per user, month, year, and category.
- Currency exchange rates with effective dates and source notes.
- Live exchange-rate sync from SP Today public pages:
  - `https://sp-today.com/en/currency/us-dollar`
  - `https://sp-today.com/en/currency/euro`
- Generic JSON exchange-rate API sync is also available for future API providers.
- Personal Expenses workspace with number cards, charts, and shortcuts.
- Website dashboard route at `/expense-tracker`.
- Script reports for monthly summary, category summary, and currency exposure.
- Dummy data for categories, exchange rates, budgets, and sample expenses.

## Important Doctypes

### Expense Category

Path: `personal_expense_tracker/personal_expense_tracker/doctype/expense_category`

Fields include:
- `category_name`
- `parent_category`
- `is_active`
- `monthly_budget`
- `description`

Important validation:
- Prevent duplicate active category names.
- Prevent selecting itself as parent category.

### Expense Entry

Path: `personal_expense_tracker/personal_expense_tracker/doctype/expense_entry`

Fields include:
- `posting_date`
- `user`
- `category`
- `description`
- `amount`
- `currency`
- `exchange_rate_to_base`
- `base_currency`
- `amount_in_base_currency`
- `payment_method`
- `reference_no`
- `attachment`
- `notes`

Important validation:
- Amount must be greater than zero.
- Currency and base currency must be in `SYP`, `USD`, `EUR`.
- Exchange rate must be greater than zero unless currency equals base currency.
- `amount_in_base_currency = amount * exchange_rate_to_base`.
- Normal users cannot enter future-dated expenses.
- Expense Managers can enter future-dated expenses.

Client behavior:
- File: `personal_expense_tracker/personal_expense_tracker/doctype/expense_entry/expense_entry.js`
- Fetches exchange rates when amount, currency, base currency, or posting date changes.
- Adds `Exchange Rate > Sync SP Today Rates` for Expense Managers/System Managers.

### Currency Exchange Rate

Path: `personal_expense_tracker/personal_expense_tracker/doctype/currency_exchange_rate`

Fields include:
- `from_currency`
- `to_currency`
- `exchange_rate`
- `effective_date`
- `is_active`
- `source`
- `notes`

Important validation:
- From and to currency cannot be the same.
- Exchange rate must be greater than zero.
- Only one active rate is allowed per from/to/effective date.

Client behavior:
- File: `personal_expense_tracker/personal_expense_tracker/doctype/currency_exchange_rate/currency_exchange_rate.js`
- Adds `Sync SP Today Rates` button for Expense Managers/System Managers.

### Monthly Budget

Path: `personal_expense_tracker/personal_expense_tracker/doctype/monthly_budget`

Fields include:
- `user`
- `month`
- `year`
- `category`
- `budget_amount`
- `currency`
- `exchange_rate_to_base`
- `budget_in_base_currency`

Important validation:
- Budget amount must be greater than zero.
- Unique budget per user, month, year, and category.
- Budget amount is converted into base currency.

## Roles And Permissions

Roles:
- `Expense User`
- `Expense Manager`

Expected behavior:
- Expense Users manage their own expense entries and monthly budgets.
- Expense Users can read categories and exchange rates.
- Expense Managers have full access and can view/manage all users' records.
- Permission query conditions are implemented in `personal_expense_tracker/permissions.py`.

## Server API

Main API file: `personal_expense_tracker/api.py`

Important whitelisted methods:
- `get_latest_exchange_rate(from_currency, to_currency, posting_date=None)`
- `sync_exchange_rates_from_sp_today(effective_date=None, rate_type=None)`
- `sync_exchange_rates_from_api(base_currency="USD", effective_date=None, provider_url=None)`
- `get_expense_summary(user=None, from_date=None, to_date=None, currency="SYP")`
- `get_monthly_expense_chart(year=None, user=None)`
- `get_category_expense_chart(from_date=None, to_date=None, user=None)`
- `get_monthly_budget_status(user=None, month=None, year=None, category=None, budget_name=None)`
- `get_this_month_expenses_card(filters=None)`
- `get_today_expenses_card(filters=None)`
- `get_top_category_card(filters=None)`
- `get_budget_usage_card(filters=None)`

SP Today sync notes:
- Defaults to `sell` rate.
- Can use `buy`, `sell`, or `mid`.
- Optional site config:

```bash
bench --site developer-test set-config personal_expense_tracker_sp_today_rate_type "sell"
bench --site developer-test clear-cache
```

Manual sync command:

```bash
cd /home/frappe/frappe-bench
bench --site developer-test execute personal_expense_tracker.api.sync_exchange_rates_from_sp_today
```

## Reports

Report paths:
- `personal_expense_tracker/personal_expense_tracker/report/monthly_expense_summary`
- `personal_expense_tracker/personal_expense_tracker/report/category_expense_summary`
- `personal_expense_tracker/personal_expense_tracker/report/currency_exposure_report`

Reports:
- Monthly Expense Summary
- Category Expense Summary
- Currency Exposure Report

## Workspace And Dashboard

Workspace file:
- `personal_expense_tracker/personal_expense_tracker/workspace/personal_expenses/personal_expenses.json`

Fixtures:
- `personal_expense_tracker/fixtures/number_card.json`
- `personal_expense_tracker/fixtures/dashboard_chart.json`
- `personal_expense_tracker/fixtures/dashboard.json`
- `personal_expense_tracker/fixtures/workspace_shortcut.json`

Workspace cards:
- This Month Expenses
- Today Expenses
- Top Category
- Budget Usage

Charts:
- Monthly Expenses
- Expenses by Category
- Expenses by Currency

Known fix:
- `get_budget_usage_card` should calculate all visible budgets/expenses for Expense Managers, but only the current user's data for normal users.

## Website Dashboard

Route:
- `/expense-tracker`

Files:
- `personal_expense_tracker/www/expense-tracker.html`
- `personal_expense_tracker/www/expense_tracker.py`
- `personal_expense_tracker/public/css/expense_tracker_web.css`
- `personal_expense_tracker/public/js/expense_tracker_web.js`

Behavior:
- Requires login and redirects guests to `/login?redirect-to=/expense-tracker`.
- Reads live Expense Entry, Monthly Budget, category, currency, and recent expense data.
- Shows a full website dashboard with animated canvas background, metric cards, monthly chart, category donut, currency exposure bars, budget pulse, and recent expense links.

## Dummy Data

Installer/dummy data file:
- `personal_expense_tracker/install.py`

Dummy categories:
- Food
- Transport
- Rent
- Utilities
- Health
- Education
- Entertainment
- Shopping
- Family
- Other

Reload dummy data:

```bash
cd /home/frappe/frappe-bench
bench --site developer-test execute personal_expense_tracker.install.create_dummy_data --kwargs "{'user': 'Administrator'}"
```

## Common Commands

Install app on site:

```bash
cd /home/frappe/frappe-bench
bench --site developer-test install-app personal_expense_tracker
bench --site developer-test migrate
```

Clear cache:

```bash
bench --site developer-test clear-cache
```

Run a method:

```bash
bench --site developer-test execute personal_expense_tracker.api.get_budget_usage_card
```

Compile-check Python:

```bash
cd /home/frappe/frappe-bench/apps/personal_expense_tracker
python -m compileall personal_expense_tracker
```

Reload Gunicorn without sudo, if Desk is using stale Python code:

```bash
ps -ef | grep gunicorn | grep -v grep
kill -HUP <gunicorn-master-pid>
```

Use this when Desk says a method does not exist but `bench execute` can run it.

## Git Notes

Repo path:

```bash
cd /home/frappe/frappe-bench/apps/personal_expense_tracker
```

Remote:

```bash
origin https://github.com/hayyandaood1990/Personal-Expense-Tracker.git
```

If local and remote diverge because a commit was amended after pushing:

```bash
git push --force-with-lease origin main
```

Prefer `--force-with-lease` over plain force push.

## Coding Guidance For Future Agents

- Follow existing Frappe patterns in the app.
- Keep the internal Python app name as `personal_expense_tracker`.
- Keep the user-facing name as `Personal Expense Tracker`.
- Use controllers for validation.
- Use `frappe.throw` with translatable strings via `_()`.
- Use helpers from `personal_expense_tracker/utils.py` for currency validation, conversion, month ranges, and manager checks.
- Do not hardcode a site name in app code.
- Keep currencies centralized through `SUPPORTED_CURRENCIES`.
- After changing Python methods used by Desk, run `clear-cache` and reload Gunicorn if needed.
- After changing fixtures/workspace/report metadata, run `bench --site developer-test migrate`.
- Avoid adding debug `print()` calls in whitelisted methods; they show up in `bench execute` output and logs.
