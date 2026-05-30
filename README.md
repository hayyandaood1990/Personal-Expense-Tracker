# Personal Expense Tracker

A Frappe Framework v16 app for personal income and expense tracking, monthly budgets, savings planning, categories, and multi-currency conversion.

## Features

- Professional expense categories with active/inactive status and monthly budget reference
- Income entries for paychecks, freelance income, gifts, investments, and other income
- Expense entries in SYP, USD, and EUR
- Currency exchange rates with effective dates
- Live exchange-rate sync for SYP, USD, and EUR
- Monthly budgets per user, month, year, and category
- Budget usage is calculated against monthly income so expenses reduce available income
- Remaining income is shown as a Savings value for month-end planning
- Expense User and Expense Manager roles
- Permission filters so normal users only see their own income, expenses, and budgets
- Client-side exchange-rate fetching and base-currency calculation
- Script reports for monthly, category, entry-level, currency exposure, and income-vs-expense summaries
- Personal Expenses workspace with dashboard widgets, including Remaining Budget in currency value
- Website dashboard at `/expense-tracker`
- Dummy categories, exchange rates, income, budgets, and sample expenses

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

The installer creates default roles, professional categories, placeholder exchange rates, sample income, sample budgets, and sample expenses. A `Savings` category is included for tracking money left after monthly expenses.

Default categories are stored in Arabic so they appear in Arabic inside Link fields: إيجار السكن، المواد الغذائية والوجبات، الملابس والأغراض الشخصية، السيارة والوقود، المواصلات العامة، دعم المنزل، الهدايا والالتزامات الاجتماعية، الزكاة والتبرعات، الزيارات والضيافة، التبغ والأركيلة، الخدمات، الصحة، التعليم، الترفيه، المدخرات، والمتفرقات.

To reload dummy data for a user:

```bash
bench --site your-site-name execute personal_expense_tracker.install.create_dummy_data --kwargs "{'user': 'user@example.com'}"
```

## Live Exchange Rates

Expense Managers can sync live exchange rates from SP Today:

- Open an Expense Entry and click Exchange Rate > Sync SP Today Rates
- Or open any Currency Exchange Rate and click Sync SP Today Rates

The SP Today sync reads the public USD and EUR pages and stores the selected sell rate by default:

```text
https://sp-today.com/en/currency/us-dollar
https://sp-today.com/en/currency/euro
```

To use buy or midpoint rates instead of sell rates:

```bash
bench --site your-site-name set-config personal_expense_tracker_sp_today_rate_type "buy"
bench --site your-site-name clear-cache
```

You can also sync SP Today rates from the command line:

```bash
bench --site your-site-name execute personal_expense_tracker.api.sync_exchange_rates_from_sp_today
```

The generic JSON API sync is still available. To use another compatible API endpoint, set this site config value. The URL may include `{base_currency}`:

```bash
bench --site your-site-name set-config personal_expense_tracker_exchange_rate_api_url "https://open.er-api.com/v6/latest/{base_currency}"
bench --site your-site-name clear-cache
```

Then run:

```bash
bench --site your-site-name execute personal_expense_tracker.api.sync_exchange_rates_from_api
```

## Reports

- Monthly Expense Summary
- Category Expense Summary
- Expense Entry Summary
- Currency Exposure Report
- Income vs Expense Summary

The **Income vs Expense Summary** report compares all income in a selected period with total expenses, then calculates the unspent amount that can be treated as month-end savings.

## Workspace Cards

The Personal Expenses workspace includes these number cards:

- This Month Expenses
- Today Expenses
- Top Category
- Budget Usage
- Remaining Budget

`Budget Usage` shows the percentage of income spent. `Remaining Budget` shows the actual money left from monthly income after expenses.

## Website Dashboard

Open the website dashboard here after logging in:

```text
https://your-site/expense-tracker
```

For the local development site:

```text
https://developer-test/expense-tracker
```

## License

MIT
