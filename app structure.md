# Personal Expense Tracker App Structure Export

Generated from local app source on 2026-06-22.

Use this document as context for future ChatGPT/Codex work when asking for new features, reports, dashboards, or refactors.

## Important Context

- Python package/app name: `personal_expense_tracker`
- Visible app/workspace title: `Personal Expense Tracker`
- Main module name: `Personal Expense Tracker`
- Framework target: Frappe Framework v16
- Purpose: personal income, expense, budget, savings, and currency tracking
- Base currency: `SYP`
- Supported currencies: `SYP`, `USD`, `EUR`
- Roles: `Expense User`, `Expense Manager`
- User-owned records: Expense Entry, Income Entry, Monthly Budget
- Expense Managers can manage master data, exchange rates, all user entries, and future-dated records
- Exchange rates support manual entry and date-aware SP Today sync
- Arabic translation file exists at `personal_expense_tracker/translations/ar.csv`
- Website dashboard exists at `/expense-tracker`
- Do not commit generated files such as `__pycache__` or `.pyc`

## App Metadata

- `app_name = "personal_expense_tracker"`
- `app_title = "Personal Expense Tracker"`
- `app_publisher = "Frappe"`
- `app_description = "Personal expense tracking for Frappe"`
- `app_license = "mit"`
- Python package requires: `>=3.14`
- Bench-managed dependency: Frappe v16

## App Layout

```text
personal_expense_tracker/
├── README.md
├── AGENTS.md
├── app structure.md
├── pyproject.toml
├── license.txt
└── personal_expense_tracker/
    ├── api.py
    ├── hooks.py
    ├── install.py
    ├── permissions.py
    ├── utils.py
    ├── budget_period.py
    ├── patches/
    ├── fixtures/
    ├── translations/
    ├── public/
    ├── www/
    └── personal_expense_tracker/
        ├── doctype/
        ├── report/
        └── workspace/
```

## Core Architecture

| Layer | Files / Folders | Purpose |
| --- | --- | --- |
| App hooks | `hooks.py` | Install hook, fixtures, permission query conditions, custom permissions |
| Setup data | `install.py` | Roles, categories, sample income, budgets, expenses, exchange rates |
| API layer | `api.py` | Exchange rates, dashboard cards, summaries, charts, report helpers |
| Permission layer | `permissions.py` | Restricts user-owned financial data |
| Shared utilities | `utils.py` | Currency constants, conversion helpers, role checks |
| Budget logic | `budget_period.py` | Budget period lookup, creation, date-window logic |
| Migrations | `patches/` and `patches.txt` | Safe updates for installed sites |
| Desk models | `doctype/` | Frappe DocTypes and controllers |
| Reports | `report/` | Script Reports |
| Website | `www/`, `public/css`, `public/js` | `/expense-tracker` web dashboard |
| Translations | `translations/ar.csv` | Arabic app translation |

## DocType Inventory

| DocType | Type | Fields | Main Purpose | Roles |
| --- | --- | ---: | --- | --- |
| Budget Period | Desk DocType | 10 | Defines budget date windows | Expense User, Expense Manager |
| Expense Category | Desk DocType | 5 | Customizable expense master data | Expense User, Expense Manager |
| Currency Exchange Rate | Desk DocType | 7 | Effective-dated currency rates | Expense User, Expense Manager |
| Expense Entry | Desk DocType | 16 | Personal expense transactions | Expense User, Expense Manager |
| Income Entry | Desk DocType | 15 | Personal income transactions | Expense User, Expense Manager |
| Monthly Budget | Desk DocType | 13 | User/category budgets by period | Expense User, Expense Manager |

## Budget Period

- Module: `Personal Expense Tracker`
- Autoname: `field:period_name`
- Title field: `period_name`
- Search fields: `period_name,from_date,to_date,status`

Key fields:

| Field | Type | Notes |
| --- | --- | --- |
| `period_name` | Data | Required, unique |
| `status` | Select | Open / Closed |
| `from_date` | Date | Required |
| `to_date` | Date | Required |
| `month` | Select | January to December |
| `year` | Int | Required |
| `is_opening_period` | Check | Marks first custom opening period |
| `auto_created` | Check | Marks generated periods |
| `notes` | Small Text | Optional |

Business role: this is the source of truth for budget windows. Dashboard cards, Monthly Budget, and reporting use Budget Period dates.

## Expense Category

- Module: `Personal Expense Tracker`
- Autoname: `field:category_name`
- Title field: `category_name`
- Search fields: `category_name,parent_category`

Fields:

| Field | Type | Notes |
| --- | --- | --- |
| `category_name` | Data | Required, unique |
| `parent_category` | Link | Links to Expense Category |
| `is_active` | Check | Default 1 |
| `monthly_budget` | Currency | Optional legacy/simple budget value |
| `description` | Small Text | Optional |

Controller rules:

- Prevent duplicate active category names
- Prevent category being its own parent
- Categories are translated to Arabic through translation/data patches

Professional categories include housing, groceries, clothing, transport, family support, charity, hospitality, utilities, health, education, entertainment, savings, and miscellaneous.

## Currency Exchange Rate

- Module: `Personal Expense Tracker`
- Autoname: `PET-RATE-{from_currency}-{to_currency}-{effective_date}-{###}`
- Search fields: `from_currency,to_currency,effective_date,source`

Fields:

| Field | Type | Notes |
| --- | --- | --- |
| `from_currency` | Select | SYP / USD / EUR |
| `to_currency` | Select | SYP / USD / EUR |
| `exchange_rate` | Float | Required |
| `effective_date` | Date | Required |
| `is_active` | Check | Default 1 |
| `source` | Data | Manual/API/SP Today |
| `notes` | Small Text | Sync details |

Controller rules:

- `from_currency` and `to_currency` cannot match
- `exchange_rate` must be greater than zero
- Only one active rate per pair and effective date

SP Today behavior:

- Today: fetches live public SP Today pages
- Past dates: fetches SP Today historical endpoint
- Future dates: blocked
- Currency Exchange Rate form sync fills the selected pair only
- Expense/Income sync can save all supported pairs for the selected date

## Expense Entry

- Autoname: `PET-EXP-{YYYY}-{#####}`
- Title field: `category`
- Search fields: `category,description,user,posting_date`

Core fields:

| Field | Type | Notes |
| --- | --- | --- |
| `posting_date` | Date | Required, default Today |
| `user` | Link User | Required, default current user |
| `category` | Link Expense Category | Required |
| `description` | Small Text | List view |
| `amount` | Currency | Required |
| `currency` | Select | SYP / USD / EUR |
| `exchange_rate_to_base` | Float | Required |
| `base_currency` | Select | Default SYP |
| `amount_in_base_currency` | Currency | Read only |
| `payment_method` | Select | Cash, Bank Transfer, Card, Wallet, Other |
| `reference_no` | Data | Optional |
| `attachment` | Attach | Optional |
| `notes` | Long Text | Optional |

Controller rules:

- Amount must be greater than zero
- Currency must be supported
- Exchange rate must be positive unless same currency
- Same currency sets exchange rate to 1
- Base amount auto-calculates
- Normal users cannot enter future expenses
- Normal users can only create/update their own records

Client behavior:

- Auto-fetch exact exchange rate by posting date
- Hide `Fetch Exchange Rate` if no exact rate exists
- Show `Sync SP Today Rates` for Expense Managers when rate is missing
- Recalculate base amount on amount/rate/currency changes

## Income Entry

- Autoname: `PET-INC-{YYYY}-{#####}`
- Title field: `income_source`
- Search fields: `income_source,description,user,posting_date`

Core fields:

| Field | Type | Notes |
| --- | --- | --- |
| `posting_date` | Date | Required, default Today |
| `user` | Link User | Required, default current user |
| `income_source` | Select | Paycheck, Freelance, Gift, Investment, Other |
| `description` | Small Text | Optional |
| `amount` | Currency | Required |
| `currency` | Select | SYP / USD / EUR |
| `exchange_rate_to_base` | Float | Required |
| `base_currency` | Select | Default SYP |
| `income_in_base_currency` | Currency | Read only |
| `reference_no` | Data | Optional |
| `attachment` | Attach | Optional |
| `notes` | Long Text | Optional |

Controller rules mirror Expense Entry:

- Income amount must be greater than zero
- Currency must be supported
- Future income requires Expense Manager
- Normal users only manage their own income
- Base income auto-calculates

Data-analysis role: Income Entry is the income side of the app. Budget usage, remaining budget, savings analysis, and income-vs-expense reporting depend on this DocType.

## Monthly Budget

- Autoname: `PET-BUD-{year}-{month}-{#####}`
- Title field: `category`
- Search fields: `user,budget_period,month,year,category`

Fields:

| Field | Type | Notes |
| --- | --- | --- |
| `user` | Link User | Required |
| `budget_period` | Link Budget Period | Required |
| `from_date` | Date | Read only from Budget Period |
| `to_date` | Date | Read only from Budget Period |
| `month` | Select | Copied from Budget Period |
| `year` | Int | Copied from Budget Period |
| `category` | Link Expense Category | Required |
| `budget_amount` | Currency | Required |
| `currency` | Select | SYP / USD / EUR |
| `exchange_rate_to_base` | Float | Required |
| `budget_in_base_currency` | Currency | Read only |

Controller rules:

- User ownership enforced
- Budget Period required
- Budget amount must be greater than zero
- Currency must be supported
- Unique budget per user, budget period, and category
- Total budgets cannot exceed total income for that budget period

Data-analysis role: Monthly Budget is used to compare planned spending against actual expenses and available income.

## Reports

| Report | Type | Ref DocType | Purpose |
| --- | --- | --- | --- |
| Monthly Expense Summary | Script Report | Expense Entry | Expenses grouped by month |
| Category Expense Summary | Script Report | Expense Entry | Expenses grouped by category and percentage |
| Expense Entry Summary | Script Report | Expense Entry | Entry-level expense detail with filters |
| Currency Exposure Report | Script Report | Expense Entry | Original currency exposure and average rates |
| Income vs Expense Summary | Script Report | Income Entry | Compares income, expenses, remaining money, and savings |

## Workspace and Dashboard

Workspace:

```text
personal_expense_tracker/workspace/personal_expenses/personal_expenses.json
```

Workspace title:

```text
Personal Expenses
```

Main shortcuts:

- Expense Entry
- Income Entry
- Expense Category
- Monthly Budget
- Currency Exchange Rate
- Reports
- Website dashboard shortcut

Number cards:

- This Month Expenses
- Today Expenses
- Top Category
- Budget Usage
- Remaining Budget

Charts:

- Monthly Expenses
- Expenses by Category
- Expenses by Currency

## Website Dashboard

Files:

```text
personal_expense_tracker/www/expense-tracker.html
personal_expense_tracker/www/expense_tracker.py
personal_expense_tracker/public/css/expense_tracker_web.css
personal_expense_tracker/public/js/expense_tracker_web.js
```

Route:

```text
/expense-tracker
```

Purpose:

- User-facing dashboard outside Desk
- Shows income, expenses, remaining budget, charts, and financial snapshot
- Uses the same API/data model as Desk dashboards

## Fixtures

```text
fixtures/
├── role.json
├── number_card.json
├── dashboard_chart.json
└── dashboard.json
```

Fixtures preserve:

- Expense roles
- Number cards
- Dashboard charts
- Dashboard records

## Permission Model

Role behavior:

| Role | Access |
| --- | --- |
| Expense User | Own Expense Entry, own Income Entry, own Monthly Budget, read categories/rates |
| Expense Manager | Full financial access, manage categories, manage rates, sync SP Today, view all users |

Permission query conditions exist for:

```text
Expense Entry
Income Entry
Monthly Budget
```

This protects financial data at list/report level, not only form save level.

## Data Model Summary

```text
User
 ├── Income Entry
 ├── Expense Entry
 └── Monthly Budget

Expense Entry ──> Expense Category
Expense Entry ──> Currency Exchange Rate by date/pair
Income Entry  ──> Currency Exchange Rate by date/pair
Monthly Budget ──> Budget Period
Monthly Budget ──> Expense Category
```

Financial calculations:

```text
expense_base = amount * exchange_rate_to_base
income_base = amount * exchange_rate_to_base
budget_base = budget_amount * exchange_rate_to_base

budget_usage_percent = period_expenses / period_income * 100
remaining_budget = period_income - period_expenses
unspent_income = total_income - total_expenses
```

## Data Analysis Notes

This app is structured around four analytical questions:

1. How much did I earn in a period?
2. How much did I spend in that same period?
3. Which categories consumed the most money?
4. How much income remains for savings?

Strong analytical dimensions:

- User
- Budget Period
- Posting Date
- Expense Category
- Currency
- Base Currency
- Income Source
- Payment Method

Key metrics:

- Total income
- Total expenses
- Remaining income
- Budget usage percent
- Category share of total expenses
- Currency exposure
- Average exchange rate
- Savings amount

## Migration / Patch Files

Important patches:

```text
apply_professional_expense_category_structure.py
translate_expense_categories_to_arabic.py
restore_english_expense_category_names.py
create_budget_periods_and_assign_budgets.py
add_income_entry_workspace_and_savings.py
add_income_vs_expense_report_and_remaining_budget_card.py
add_expense_entry_summary_report_link.py
add_website_dashboard_shortcut.py
```

These patches preserve existing data while adding newer budgeting, income, savings, Arabic category, report, and website-dashboard features.

## Senior Developer Notes

- The app follows Frappe controller-based validation.
- Financial values are normalized into base currency for reporting.
- SP Today sync is date-aware and supports historical data.
- User data isolation is implemented in both controllers and permission query conditions.
- Budget Period is the correct reporting window, not calendar month alone.
- The app is ready for future extension to more currencies if `SUPPORTED_CURRENCIES`, DocType Select options, and sync providers are expanded together.
- Generated Python cache files exist locally but should not be committed.
