import frappe
from frappe.utils import getdate

from personal_expense_tracker.budget_period import (
	OPENING_PERIOD_FROM_DATE,
	get_budget_period_for_date,
)
from personal_expense_tracker.utils import MONTHS


def execute():
	ensure_opening_period()
	assign_existing_budgets()
	clear_category_budget_cycle_dates()
	frappe.db.commit()


def ensure_opening_period():
	period = get_budget_period_for_date(OPENING_PERIOD_FROM_DATE, create_if_missing=True)
	frappe.db.set_value(
		"Budget Period",
		period.name,
		{
			"is_opening_period": 1,
			"status": "Open",
			"notes": "Opening budget period for the first app cycle.",
		},
		update_modified=False,
	)


def assign_existing_budgets():
	rows = frappe.get_all(
		"Monthly Budget",
		fields=["name", "user", "month", "year", "category", "budget_period"],
	)
	for row in rows:
		if row.budget_period:
			sync_budget_period_fields(row.name, row.budget_period)
			continue

		period = get_budget_period_for_budget(row)
		if not period:
			continue

		existing = frappe.db.exists(
			"Monthly Budget",
			{
				"user": row.user,
				"budget_period": period.name,
				"category": row.category,
				"name": ["!=", row.name],
			},
		)
		if existing:
			frappe.delete_doc("Monthly Budget", row.name, ignore_permissions=True, force=True)
			continue

		sync_budget_period_fields(row.name, period.name)


def get_budget_period_for_budget(budget):
	if budget.month not in MONTHS or not budget.year:
		return None

	month_number = MONTHS.index(budget.month) + 1
	if int(budget.year) == 2026 and month_number in (5, 6):
		period_date = OPENING_PERIOD_FROM_DATE
	else:
		period_date = getdate(f"{int(budget.year):04d}-{month_number:02d}-01")

	return get_budget_period_for_date(period_date, create_if_missing=True)


def sync_budget_period_fields(budget_name, budget_period):
	period = frappe.db.get_value(
		"Budget Period",
		budget_period,
		["from_date", "to_date", "month", "year"],
		as_dict=True,
	)
	if not period:
		return

	frappe.db.set_value(
		"Monthly Budget",
		budget_name,
		{
			"budget_period": budget_period,
			"from_date": period.from_date,
			"to_date": period.to_date,
			"month": period.month,
			"year": period.year,
		},
		update_modified=False,
	)


def clear_category_budget_cycle_dates():
	if not frappe.db.has_column("Expense Category", "budget_from_date"):
		return

	frappe.db.sql(
		"""
		update `tabExpense Category`
		set budget_from_date = null, budget_to_date = null
		where budget_from_date is not null or budget_to_date is not null
		"""
	)
