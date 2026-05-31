from __future__ import annotations

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate, today

from personal_expense_tracker.utils import MONTHS

OPENING_PERIOD_FROM_DATE = date(2026, 5, 23)
OPENING_PERIOD_TO_DATE = date(2026, 6, 30)


def get_budget_period_for_date(
	period_date: str | date | None = None,
	create_if_missing: bool = True,
):
	period_date = getdate(period_date or today())
	period = find_budget_period_for_date(period_date)
	if period:
		return period

	if not create_if_missing:
		return None

	return create_budget_period_for_date(period_date)


def find_budget_period_for_date(period_date: str | date):
	period_date = getdate(period_date)
	periods = frappe.get_all(
		"Budget Period",
		filters={
			"from_date": ["<=", period_date],
			"to_date": [">=", period_date],
			"status": "Open",
		},
		fields=["name", "from_date", "to_date", "month", "year", "status"],
		order_by="from_date desc",
		limit=1,
	)
	return frappe._dict(periods[0]) if periods else None


def create_budget_period_for_date(period_date: str | date):
	period_date = getdate(period_date)
	if OPENING_PERIOD_FROM_DATE <= period_date <= OPENING_PERIOD_TO_DATE:
		from_date = OPENING_PERIOD_FROM_DATE
		to_date = OPENING_PERIOD_TO_DATE
		is_opening_period = 1
	else:
		from_date = period_date.replace(day=1)
		to_date = period_date.replace(
			day=calendar.monthrange(period_date.year, period_date.month)[1]
		)
		is_opening_period = 0

	existing = frappe.get_all(
		"Budget Period",
		filters={"from_date": from_date, "to_date": to_date},
		fields=["name", "from_date", "to_date", "month", "year", "status"],
		limit=1,
	)
	if existing:
		return frappe._dict(existing[0])

	doc = frappe.get_doc(
		{
			"doctype": "Budget Period",
			"period_name": get_budget_period_name(from_date, to_date),
			"from_date": from_date,
			"to_date": to_date,
			"month": MONTHS[to_date.month - 1],
			"year": to_date.year,
			"status": "Open",
			"is_opening_period": is_opening_period,
			"auto_created": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return frappe._dict(
		{
			"name": doc.name,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"month": doc.month,
			"year": doc.year,
			"status": doc.status,
		}
	)


def get_budget_period_name(from_date: str | date, to_date: str | date) -> str:
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if from_date.day == 1 and from_date.month == to_date.month and from_date.year == to_date.year:
		last_day = calendar.monthrange(to_date.year, to_date.month)[1]
		if to_date.day == last_day:
			return f"{MONTHS[to_date.month - 1]} {to_date.year}"

	return f"{from_date:%d-%m-%Y} to {to_date:%d-%m-%Y}"


def get_budget_period_date_range(budget_period: str | None):
	if not budget_period:
		return None, None

	period = frappe.db.get_value(
		"Budget Period",
		budget_period,
		["from_date", "to_date"],
		as_dict=True,
	)
	if not period:
		frappe.throw(_("Budget Period {0} does not exist.").format(budget_period))

	return getdate(period.from_date), getdate(period.to_date)
