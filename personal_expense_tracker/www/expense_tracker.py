from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, getdate, today

from personal_expense_tracker.api import get_expense_rows, get_income_rows
from personal_expense_tracker.budget_period import get_budget_period_for_date
from personal_expense_tracker.utils import (
	BASE_CURRENCY,
	MONTHS,
	convert_amount,
	is_expense_manager,
)

no_cache = 1
no_sitemap = 1


def get_context(context):
	context = frappe._dict(context or {})
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/expense-tracker"
		raise frappe.Redirect

	current = getdate(today())
	period = get_budget_period_for_date(current, create_if_missing=True)
	month = period.month
	from_date = period.from_date
	to_date = period.to_date
	user = None if is_expense_manager() else frappe.session.user

	current_month_rows = get_expense_rows(user=user, from_date=from_date, to_date=to_date)
	current_month_income_rows = get_income_rows(user=user, from_date=from_date, to_date=to_date)
	year_rows = get_expense_rows(
		user=user,
		from_date=f"{current.year}-01-01",
		to_date=f"{current.year}-12-31",
	)
	today_rows = get_expense_rows(user=user, from_date=today(), to_date=today())

	page_data = build_page_data(
		current=current,
		month=month,
		period=period,
		from_date=from_date,
		to_date=to_date,
		user=user,
		current_month_rows=current_month_rows,
		current_month_income_rows=current_month_income_rows,
		year_rows=year_rows,
		today_rows=today_rows,
	)

	context.update(
		{
			"no_breadcrumbs": True,
			"show_sidebar": False,
			"title": _("Personal Expense Tracker"),
			"page_data": page_data,
			"page_data_json": frappe.as_json(page_data),
			"desk_url": "/desk/personal-expenses",
			"income_entry_url": "/desk/income-entry",
			"expense_entry_url": "/desk/expense-entry",
			"monthly_budget_url": "/desk/monthly-budget",
			"exchange_rate_url": "/desk/currency-exchange-rate",
		}
	)
	return context


def build_page_data(
	current,
	month,
	period,
	from_date,
	to_date,
	user,
	current_month_rows,
	current_month_income_rows,
	year_rows,
	today_rows,
):
	month_total = get_rows_total(current_month_rows)
	month_income = get_income_total(current_month_income_rows)
	today_total = get_rows_total(today_rows)
	category_totals = get_category_totals(current_month_rows)
	currency_totals = get_currency_totals(current_month_rows)
	monthly_totals = get_monthly_totals(year_rows)
	budget_status = get_budget_status(user, period, current_month_rows, current_month_income_rows)
	top_category = get_top_category(category_totals)
	recent_expenses = get_recent_expenses(user)

	return {
		"generated_on": today(),
		"period_label": period.name,
		"base_currency": BASE_CURRENCY,
		"month_total": month_total,
		"month_total_display": fmt_money(month_total, currency=BASE_CURRENCY),
		"month_income": month_income,
		"month_income_display": fmt_money(month_income, currency=BASE_CURRENCY),
		"net_income": flt(month_income - month_total, 2),
		"net_income_display": fmt_money(month_income - month_total, currency=BASE_CURRENCY),
		"today_total": today_total,
		"today_total_display": fmt_money(today_total, currency=BASE_CURRENCY),
		"entry_count": len(current_month_rows),
		"top_category": top_category,
		"budget": budget_status,
		"monthly": {
			"labels": list(MONTHS),
			"values": monthly_totals,
		},
		"categories": category_totals,
		"currencies": currency_totals,
		"recent_expenses": recent_expenses,
		"translations": get_client_translations(),
		"from_date": from_date,
		"to_date": to_date,
	}


def get_rows_total(rows):
	total = 0
	for row in rows:
		total += convert_amount(
			row.get("amount_in_base_currency"),
			row.get("base_currency") or BASE_CURRENCY,
			BASE_CURRENCY,
			row.get("posting_date"),
		)
	return flt(total, 2)


def get_income_total(rows):
	total = 0
	for row in rows:
		total += convert_amount(
			row.get("income_in_base_currency"),
			row.get("base_currency") or BASE_CURRENCY,
			BASE_CURRENCY,
			row.get("posting_date"),
		)
	return flt(total, 2)


def get_category_totals(rows):
	totals = defaultdict(float)
	for row in rows:
		totals[row.get("category")] += convert_amount(
			row.get("amount_in_base_currency"),
			row.get("base_currency") or BASE_CURRENCY,
			BASE_CURRENCY,
			row.get("posting_date"),
		)

	ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
	return [
		{
			"label": _(category or ""),
			"value": flt(value, 2),
			"display": fmt_money(value, currency=BASE_CURRENCY),
		}
		for category, value in ordered
	]


def get_currency_totals(rows):
	totals = defaultdict(lambda: {"original": 0.0, "base": 0.0, "count": 0})
	for row in rows:
		currency = row.get("currency") or BASE_CURRENCY
		totals[currency]["original"] += flt(row.get("amount"))
		totals[currency]["base"] += convert_amount(
			row.get("amount_in_base_currency"),
			row.get("base_currency") or BASE_CURRENCY,
			BASE_CURRENCY,
			row.get("posting_date"),
		)
		totals[currency]["count"] += 1

	return [
		{
			"currency": currency,
			"original": flt(values["original"], 2),
			"base": flt(values["base"], 2),
			"base_display": fmt_money(values["base"], currency=BASE_CURRENCY),
			"count": values["count"],
		}
		for currency, values in sorted(totals.items())
	]


def get_monthly_totals(rows):
	values = [0.0] * 12
	for row in rows:
		month_index = getdate(row.get("posting_date")).month - 1
		values[month_index] += convert_amount(
			row.get("amount_in_base_currency"),
			row.get("base_currency") or BASE_CURRENCY,
			BASE_CURRENCY,
			row.get("posting_date"),
		)
	return [flt(value, 2) for value in values]


def get_budget_status(user, period, rows, income_rows):
	budget_filters = {"budget_period": period.name}
	if user:
		budget_filters["user"] = user

	budgets = frappe.get_all(
		"Monthly Budget",
		filters=budget_filters,
		fields=["name", "user", "category", "budget_in_base_currency"],
	)
	total_budget = sum(flt(row.get("budget_in_base_currency")) for row in budgets)
	spent = get_rows_total(rows)
	total_income = get_income_total(income_rows)
	remaining_budget = total_budget - spent
	income_remaining = total_income - spent
	usage_percent = (spent / total_income * 100) if total_income else 0
	allocation_percent = (total_budget / total_income * 100) if total_income else 0

	return {
		"total": flt(total_budget, 2),
		"total_display": fmt_money(total_budget, currency=BASE_CURRENCY),
		"income": flt(total_income, 2),
		"income_display": fmt_money(total_income, currency=BASE_CURRENCY),
		"spent": spent,
		"spent_display": fmt_money(spent, currency=BASE_CURRENCY),
		"remaining": flt(remaining_budget, 2),
		"remaining_display": fmt_money(remaining_budget, currency=BASE_CURRENCY),
		"income_remaining": flt(income_remaining, 2),
		"income_remaining_display": fmt_money(income_remaining, currency=BASE_CURRENCY),
		"usage_percent": flt(usage_percent, 2),
		"usage_width": min(flt(usage_percent, 2), 100),
		"allocation_percent": flt(allocation_percent, 2),
		"count": len(budgets),
	}


def get_top_category(category_totals):
	if not category_totals:
		return {"label": _("No expenses"), "value": 0, "display": fmt_money(0, currency=BASE_CURRENCY)}

	return category_totals[0]


def get_recent_expenses(user):
	filters = {}
	if user:
		filters["user"] = user

	rows = frappe.get_all(
		"Expense Entry",
		filters=filters,
		fields=[
			"name",
			"posting_date",
			"category",
			"description",
			"amount",
			"currency",
			"amount_in_base_currency",
			"base_currency",
		],
		order_by="posting_date desc, creation desc",
		limit=6,
	)

	return [
		{
			"name": row.get("name"),
			"date": row.get("posting_date"),
			"category": _(row.get("category") or ""),
			"description": row.get("description"),
			"amount": fmt_money(row.get("amount"), currency=row.get("currency")),
			"base_amount": fmt_money(
				row.get("amount_in_base_currency"),
				currency=row.get("base_currency") or BASE_CURRENCY,
			),
			"url": f"/desk/expense-entry/{row.get('name')}",
		}
		for row in rows
	]


def get_client_translations():
	return {
		"no_categories_yet": _("No categories yet."),
		"no_currency_exposure_yet": _("No currency exposure yet."),
		"entries": _("entries"),
	}
