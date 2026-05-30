from __future__ import annotations

import calendar

import frappe
from frappe.utils import add_days, flt, getdate, today

from personal_expense_tracker.utils import BASE_CURRENCY, get_latest_rate_record

DEFAULT_CATEGORIES = [
	"إيجار السكن",
	"المواد الغذائية والوجبات",
	"الملابس والأغراض الشخصية",
	"السيارة والوقود",
	"المواصلات العامة",
	"دعم المنزل",
	"الهدايا والالتزامات الاجتماعية",
	"الزكاة والتبرعات",
	"الزيارات والضيافة",
	"التبغ والأركيلة",
	"الخدمات",
	"الصحة",
	"التعليم",
	"الترفيه",
	"المدخرات",
	"المتفرقات",
]

DUMMY_EXCHANGE_RATES = [
	("USD", "SYP", 15000.0),
	("EUR", "SYP", 16200.0),
	("EUR", "USD", 1.08),
	("USD", "EUR", 0.93),
]


def after_install():
	create_roles()
	create_dummy_data()


def create_roles():
	for role_name in ("Expense User", "Expense Manager"):
		if frappe.db.exists("Role", role_name):
			continue

		role = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
				"is_custom": 0,
			}
		)
		role.insert(ignore_permissions=True)


@frappe.whitelist()
def create_dummy_data(user: str | None = None):
	user = user or frappe.session.user
	if not user or user == "Guest":
		user = "Administrator"

	create_default_categories()
	create_dummy_exchange_rates()
	create_sample_income(user)
	create_sample_budgets(user)
	create_sample_expenses(user)
	frappe.db.commit()


def create_default_categories():
	for category_name in DEFAULT_CATEGORIES:
		if frappe.db.exists("Expense Category", category_name):
			continue

		category = frappe.get_doc(
			{
				"doctype": "Expense Category",
				"category_name": category_name,
				"is_active": 1,
				"description": "Dummy category for Personal Expense Tracker setup.",
			}
		)
		category.insert(ignore_permissions=True)


def create_dummy_exchange_rates():
	# Use an older effective date so every seeded historical expense can resolve
	# a clearly dummy conversion rate during validation.
	effective_date = getdate(add_days(today(), -90))
	for from_currency, to_currency, exchange_rate in DUMMY_EXCHANGE_RATES:
		existing = frappe.db.exists(
			"Currency Exchange Rate",
			{
				"from_currency": from_currency,
				"to_currency": to_currency,
				"effective_date": effective_date,
				"is_active": 1,
			},
		)
		if existing:
			continue

		rate = frappe.get_doc(
			{
				"doctype": "Currency Exchange Rate",
				"from_currency": from_currency,
				"to_currency": to_currency,
				"exchange_rate": exchange_rate,
				"effective_date": effective_date,
				"is_active": 1,
				"source": "Dummy Data - Placeholder",
				"notes": "Placeholder exchange rate for demo data. Replace with a trusted source.",
			}
		)
		rate.insert(ignore_permissions=True)


def create_sample_budgets(user):
	current = getdate(today())
	month = calendar.month_name[current.month]
	budgets = {
		"المواد الغذائية والوجبات": 1500000,
		"المواصلات العامة": 600000,
		"الخدمات": 900000,
		"الترفيه": 450000,
	}

	for category, amount in budgets.items():
		if frappe.db.exists(
			"Monthly Budget",
			{"user": user, "month": month, "year": current.year, "category": category},
		):
			continue

		budget = frappe.get_doc(
			{
				"doctype": "Monthly Budget",
				"user": user,
				"month": month,
				"year": current.year,
				"category": category,
				"budget_amount": amount,
				"currency": BASE_CURRENCY,
				"exchange_rate_to_base": 1,
			}
		)
		budget.insert(ignore_permissions=True)


def create_sample_income(user):
	current = getdate(today())
	reference_no = "DUMMY-PET-INCOME-001"
	values = {
		"posting_date": current.replace(day=1),
		"user": user,
		"income_source": "Paycheck",
		"description": "Monthly paycheck",
		"amount": 5000000,
		"currency": BASE_CURRENCY,
		"exchange_rate_to_base": 1,
		"base_currency": BASE_CURRENCY,
		"reference_no": reference_no,
		"notes": "Dummy income entry for Personal Expense Tracker demo data.",
	}
	existing = frappe.db.exists("Income Entry", {"reference_no": reference_no, "user": user})
	if existing:
		income = frappe.get_doc("Income Entry", existing)
		income.update(values)
		income.save(ignore_permissions=True)
	else:
		income = frappe.get_doc({"doctype": "Income Entry", **values})
		income.insert(ignore_permissions=True)


def create_sample_expenses(user):
	rows = [
		(-1, "المواد الغذائية والوجبات", "Lunch and groceries", 85000, "SYP", "Cash", "DUMMY-PET-001"),
		(-3, "المواصلات العامة", "Taxi and bus rides", 22, "USD", "Wallet", "DUMMY-PET-002"),
		(-7, "الخدمات", "Internet bill", 18, "EUR", "Bank Transfer", "DUMMY-PET-003"),
		(-16, "الترفيه", "Movie night", 125000, "SYP", "Card", "DUMMY-PET-004"),
		(-35, "الصحة", "Pharmacy purchase", 12, "USD", "Cash", "DUMMY-PET-005"),
		(-50, "التعليم", "Online course", 30, "EUR", "Card", "DUMMY-PET-006"),
	]

	for days, category, description, amount, currency, payment_method, reference_no in rows:
		posting_date = add_days(today(), days)
		exchange_rate = 1
		if currency != BASE_CURRENCY:
			rate = get_latest_rate_record(currency, BASE_CURRENCY, posting_date)
			exchange_rate = flt(rate.exchange_rate) if rate else 1

		values = {
			"posting_date": posting_date,
			"user": user,
			"category": category,
			"description": description,
			"amount": amount,
			"currency": currency,
			"exchange_rate_to_base": exchange_rate,
			"base_currency": BASE_CURRENCY,
			"payment_method": payment_method,
			"reference_no": reference_no,
			"notes": "Dummy expense entry for Personal Expense Tracker demo data.",
		}
		existing = frappe.db.exists("Expense Entry", {"reference_no": reference_no, "user": user})
		if existing:
			expense = frappe.get_doc("Expense Entry", existing)
			expense.update(values)
			expense.save(ignore_permissions=True)
		else:
			expense = frappe.get_doc({"doctype": "Expense Entry", **values})
			expense.insert(ignore_permissions=True)
