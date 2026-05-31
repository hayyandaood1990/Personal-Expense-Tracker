# AGENTS.md

## Project Context

- Bench path: `/home/frappe/frappe-bench`
- App path: `/home/frappe/frappe-bench/apps/personal_expense_tracker`
- Site used during development: `developer-test`
- Framework: Frappe Framework v16
- Internal app/package name: `personal_expense_tracker`
- User-facing app name: `Personal Expense Tracker`
- GitHub repo: `https://github.com/hayyandaood1990/Personal-Expense-Tracker`

This is a Frappe app for personal expense tracking. It lets users record income and expenses, group expenses by a professional translated category structure, manage budget periods and monthly budgets, store exchange rates, convert amounts into a base currency, and view dashboards/reports.

## Core Features

- Expense entry tracking with category, amount, currency, payment method, notes, and attachment.
- Income entry tracking for paychecks and other income sources.
- Supported currencies: `SYP`, `USD`, `EUR`.
- Default base currency: `SYP`.
- Professional category management with parent categories, active/inactive state, and monthly budget reference.
- Expense Category is a translated DocType: stored names are English, Arabic UI displays Arabic translations.
- Budget Period management for non-calendar opening periods and normal monthly periods.
- Opening budget period: `2026-05-23` to `2026-06-30`.
- From `2026-07-01` onward, budget periods are normal calendar months.
- Monthly budgets per user, budget period, and category.
- Monthly budgets cannot exceed that user's total income for the same budget period.
- Expenses reduce period income; dashboards expose income left after expenses.
- Currency exchange rates with effective dates and source notes.
- Live exchange-rate sync from SP Today public pages:
  - `https://sp-today.com/en/currency/us-dollar`
  - `https://sp-today.com/en/currency/euro`
- Generic JSON exchange-rate API sync is also available for future API providers.
- Personal Expenses workspace with number cards, charts, and shortcuts.
- Website dashboard route at `/expense-tracker`.
- Script reports for monthly summary, category summary, expense entry summary, currency exposure, and income-vs-expense comparison.
- Remaining period income is reported as a Savings planning value; do not auto-create a Savings expense unless the user explicitly asks, because that would change expense totals.
- Dummy data for categories, budget periods, exchange rates, income, budgets, and sample expenses.

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
- Category document names are stored in English and translated with `translated_doctype`.
- Do not add budget cycle dates here; budget windows belong to Budget Period.

### Budget Period

Path: `personal_expense_tracker/personal_expense_tracker/doctype/budget_period`

Fields include:
- `period_name`
- `status`
- `from_date`
- `to_date`
- `month`
- `year`
- `is_opening_period`
- `auto_created`
- `notes`

Important behavior:
- Budget Period is the source of truth for budget windows.
- Periods cannot overlap.
- Opening period is `23-05-2026 to 30-06-2026`.
- Normal periods are auto-created by date, for example `July 2026` from `2026-07-01` to `2026-07-31`.
- Helper file: `personal_expense_tracker/budget_period.py`.
- Important helpers:
  - `get_budget_period_for_date(period_date=None, create_if_missing=True)`
  - `get_budget_period_date_range(budget_period)`

### Income Entry

Path: `personal_expense_tracker/personal_expense_tracker/doctype/income_entry`

Fields include:
- `posting_date`
- `user`
- `income_source`
- `description`
- `amount`
- `currency`
- `exchange_rate_to_base`
- `base_currency`
- `income_in_base_currency`
- `reference_no`
- `attachment`
- `notes`

Important validation:
- Income amount must be greater than zero.
- Currency and base currency must be in `SYP`, `USD`, `EUR`.
- Exchange rate must be greater than zero unless currency equals base currency.
- `income_in_base_currency = amount * exchange_rate_to_base`.
- Normal users cannot enter future-dated income.
- Normal users can only manage their own income entries.

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
- `budget_period`
- `from_date`
- `to_date`
- `month`
- `year`
- `category`
- `budget_amount`
- `currency`
- `exchange_rate_to_base`
- `budget_in_base_currency`

Important validation:
- Budget amount must be greater than zero.
- Unique budget per user, budget period, and category.
- Budget amount is converted into base currency.
- Total budgets for a user cannot exceed that user's total Income Entry amount for the same budget period.
- `budget_period` defaults to the current active period.
- `from_date`, `to_date`, `month`, and `year` sync from the selected Budget Period.
- `month` and `year` remain for display/backward compatibility, but Budget Period is the real period key.

## Roles And Permissions

Roles:
- `Expense User`
- `Expense Manager`

Expected behavior:
- Expense Users manage their own expense entries and monthly budgets.
- Expense Users manage their own income entries.
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
- `get_income_summary(user=None, from_date=None, to_date=None, currency="SYP")`
- `get_monthly_expense_chart(year=None, user=None)`
- `get_category_expense_chart(from_date=None, to_date=None, user=None)`
- `get_current_budget_period(posting_date=None)`
- `get_monthly_budget_status(user=None, month=None, year=None, category=None, budget_name=None, budget_period=None)`
- `get_this_month_expenses_card(filters=None)`
- `get_today_expenses_card(filters=None)`
- `get_top_category_card(filters=None)`
- `get_budget_usage_card(filters=None)`
- `get_remaining_budget_card(filters=None)`

Budget card behavior:
- Workspace cards use the current active Budget Period.
- `get_budget_usage_card` returns the percent of current-period income spent, not percent of category budgets used.
- `get_remaining_budget_card` returns current-period income minus current-period expenses as a `SYP` currency value.

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
- `personal_expense_tracker/personal_expense_tracker/report/expense_entry_summary`
- `personal_expense_tracker/personal_expense_tracker/report/income_vs_expense_summary`

Reports:
- Monthly Expense Summary
- Category Expense Summary
- Currency Exposure Report
- Expense Entry Summary
- Income vs Expense Summary

Income vs Expense Summary behavior:
- Filters by from date, to date, user, income source, and currency.
- Lists income entries for the selected period.
- Adds summary rows for Total Expenses and Unspent Income to Savings.
- Report summary shows Total Income, Total Expenses, Unspent Income to Savings, and Income Used %.
- The chart compares total expenses with the unspent amount that can be treated as month-end savings.

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
- Remaining Budget

Card math:
- Budget Usage = current Budget Period expenses / current Budget Period income * 100.
- Remaining Budget = current Budget Period income - current Budget Period expenses.
- For Expense Managers the cards use all visible users; for normal users they use only the session user's records.

Charts:
- Monthly Expenses
- Expenses by Category
- Expenses by Currency

Visibility behavior:
- Expense Managers see all visible users in workspace card totals.
- Normal users see only their own records in workspace card totals.

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
- Uses the current active Budget Period for the dashboard window.
- Reads live Income Entry totals and subtracts expenses from current-period income.
- Shows a full website dashboard with animated canvas background, metric cards, monthly chart, category donut, currency exposure bars, income-aware budget pulse, and recent expense links.

## Dummy Data

Installer/dummy data file:
- `personal_expense_tracker/install.py`

Default professional categories are stored as English `Expense Category` document names and translated into Arabic through `personal_expense_tracker/translations/ar.csv`:
- Housing Rent
- Groceries & Meals
- Clothing & Personal Items
- Vehicle & Fuel
- Public Transport
- Household Support
- Gifts & Social Obligations
- Charity & Religious Giving
- Visits & Hospitality
- Tobacco & Shisha
- Utilities
- Health
- Education
- Entertainment
- Savings
- Miscellaneous

Default opening Budget Period:
- `23-05-2026 to 30-06-2026`

Monthly Budget records link to this opening period until the app reaches the first normal monthly period beginning `2026-07-01`.

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
- Use helpers from `personal_expense_tracker/budget_period.py` for budget period selection, creation, and date ranges.
- Do not hardcode a site name in app code.
- Keep currencies centralized through `SUPPORTED_CURRENCIES`.
- After changing Python methods used by Desk, run `clear-cache` and reload Gunicorn if needed.
- After changing fixtures/workspace/report metadata, run `bench --site developer-test migrate`.
- Avoid adding debug `print()` calls in whitelisted methods; they show up in `bench execute` output and logs.
