from __future__ import annotations

import calendar
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, getdate, nowdate, today

from personal_expense_tracker.utils import (
	BASE_CURRENCY,
	MONTHS,
	convert_amount,
	get_latest_rate_record,
	get_month_date_range,
	is_expense_manager,
	validate_supported_currency,
)


@frappe.whitelist()
def get_latest_exchange_rate(from_currency, to_currency, posting_date=None):
	return get_latest_rate_record(from_currency, to_currency, posting_date)


def resolve_user_filter(user=None):
	if is_expense_manager():
		return user

	return frappe.session.user


def get_expense_rows(user=None, from_date=None, to_date=None, category=None, currency=None):
	filters = []
	resolved_user = resolve_user_filter(user)
	if resolved_user:
		filters.append(["user", "=", resolved_user])
	if from_date:
		filters.append(["posting_date", ">=", getdate(from_date)])
	if to_date:
		filters.append(["posting_date", "<=", getdate(to_date)])
	if category:
		filters.append(["category", "=", category])
	if currency:
		filters.append(["currency", "=", currency])

	return frappe.get_all(
		"Expense Entry",
		filters=filters,
		fields=[
			"name",
			"posting_date",
			"user",
			"category",
			"amount",
			"currency",
			"exchange_rate_to_base",
			"base_currency",
			"amount_in_base_currency",
		],
		order_by="posting_date asc, creation asc",
	)


def get_total_in_currency(rows, target_currency=BASE_CURRENCY):
	validate_supported_currency(target_currency)
	total = 0
	for row in rows:
		total += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			target_currency,
			row.posting_date,
		)
	return flt(total)


@frappe.whitelist()
def get_expense_summary(user=None, from_date=None, to_date=None, currency=BASE_CURRENCY):
	validate_supported_currency(currency)
	rows = get_expense_rows(user=user, from_date=from_date, to_date=to_date)
	total = get_total_in_currency(rows, currency)

	by_category = defaultdict(float)
	by_currency = defaultdict(float)
	for row in rows:
		converted_amount = convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			currency,
			row.posting_date,
		)
		by_category[row.category] += converted_amount
		by_currency[row.currency] += flt(row.amount)

	return {
		"currency": currency,
		"total_expenses": total,
		"number_of_entries": len(rows),
		"by_category": dict(by_category),
		"by_currency": dict(by_currency),
	}


@frappe.whitelist()
def get_monthly_expense_chart(year=None, user=None):
	year = cint(year) or getdate(today()).year
	start_date = f"{year}-01-01"
	end_date = f"{year}-12-31"
	rows = get_expense_rows(user=user, from_date=start_date, to_date=end_date)

	values = [0.0] * 12
	for row in rows:
		month_index = getdate(row.posting_date).month - 1
		values[month_index] += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			BASE_CURRENCY,
			row.posting_date,
		)

	return {
		"data": {"labels": list(MONTHS), "datasets": [{"name": _("Expenses"), "values": values}]},
		"type": "line",
		"fieldtype": "Currency",
	}


@frappe.whitelist()
def get_category_expense_chart(from_date=None, to_date=None, user=None):
	rows = get_expense_rows(user=user, from_date=from_date, to_date=to_date)
	totals = defaultdict(float)
	for row in rows:
		totals[row.category] += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			BASE_CURRENCY,
			row.posting_date,
		)

	ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
	return {
		"data": {
			"labels": [row[0] for row in ordered],
			"datasets": [{"name": _("Expenses"), "values": [row[1] for row in ordered]}],
		},
		"type": "donut",
		"fieldtype": "Currency",
	}


@frappe.whitelist()
def get_monthly_budget_status(user=None, month=None, year=None, category=None, budget_name=None):
	user = resolve_user_filter(user)
	month = month or calendar.month_name[getdate(nowdate()).month]
	year = cint(year) or getdate(nowdate()).year

	if not category:
		return None

	if budget_name and frappe.db.exists("Monthly Budget", budget_name):
		budget = frappe.get_doc("Monthly Budget", budget_name)
		if not is_expense_manager() and budget.user != frappe.session.user:
			frappe.throw(_("You are not permitted to view this budget."))
	else:
		budget_name = frappe.db.get_value(
			"Monthly Budget",
			{"user": user, "month": month, "year": year, "category": category},
			"name",
		)
		if not budget_name:
			return None
		budget = frappe.get_doc("Monthly Budget", budget_name)

	from_date, to_date = get_month_date_range(budget.month, budget.year)
	rows = get_expense_rows(
		user=budget.user,
		from_date=from_date,
		to_date=to_date,
		category=budget.category,
	)
	spent = get_total_in_currency(rows, BASE_CURRENCY)
	budget_amount = flt(budget.budget_in_base_currency)
	remaining = budget_amount - spent
	usage_percent = (spent / budget_amount * 100) if budget_amount else 0

	return {
		"budget": budget_amount,
		"spent": spent,
		"remaining": remaining,
		"usage_percent": usage_percent,
		"currency": BASE_CURRENCY,
	}


@frappe.whitelist()
def get_this_month_expenses_card(filters=None):
	current = getdate(today())
	start = current.replace(day=1)
	end = current.replace(day=calendar.monthrange(current.year, current.month)[1])
	summary = get_expense_summary(from_date=start, to_date=end, currency=BASE_CURRENCY)
	return {"value": summary["total_expenses"], "fieldtype": "Currency", "options": BASE_CURRENCY}


@frappe.whitelist()
def get_today_expenses_card(filters=None):
	summary = get_expense_summary(from_date=today(), to_date=today(), currency=BASE_CURRENCY)
	return {"value": summary["total_expenses"], "fieldtype": "Currency", "options": BASE_CURRENCY}


@frappe.whitelist()
def get_top_category_card(filters=None):
	current = getdate(today())
	start = current.replace(day=1)
	end = current.replace(day=calendar.monthrange(current.year, current.month)[1])
	chart = get_category_expense_chart(from_date=start, to_date=end)
	labels = chart["data"]["labels"]
	values = chart["data"]["datasets"][0]["values"]
	if not labels:
		return _("No expenses")

	return "{0}: {1}".format(labels[0], fmt_money(values[0], currency=BASE_CURRENCY))


@frappe.whitelist()
def get_budget_usage_card(filters=None):
	current = getdate(today())
	month = calendar.month_name[current.month]
	budgets = frappe.get_all(
		"Monthly Budget",
		filters={"user": frappe.session.user, "month": month, "year": current.year},
		fields=["name", "budget_in_base_currency", "category"],
	)
	if not budgets:
		return {"value": 0, "fieldtype": "Percent"}

	total_budget = sum(flt(row.budget_in_base_currency) for row in budgets)
	from_date, to_date = get_month_date_range(month, current.year)
	rows = get_expense_rows(user=frappe.session.user, from_date=from_date, to_date=to_date)
	spent = get_total_in_currency(rows, BASE_CURRENCY)
	usage = (spent / total_budget * 100) if total_budget else 0
	return {"value": usage, "fieldtype": "Percent"}
