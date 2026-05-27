import calendar
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from personal_expense_tracker.api import get_expense_rows, get_total_in_currency
from personal_expense_tracker.utils import BASE_CURRENCY, MONTHS, validate_supported_currency


def execute(filters=None):
	filters = frappe._dict(filters or {})
	currency = filters.get("currency") or BASE_CURRENCY
	validate_supported_currency(currency)

	columns = get_columns(currency)
	data = get_data(filters, currency)
	chart = get_chart(data, currency)
	return columns, data, None, chart


def get_columns(currency):
	return [
		{"fieldname": "month", "fieldtype": "Data", "label": _("Month"), "width": 180},
		{
			"fieldname": "total_expenses",
			"fieldtype": "Currency",
			"label": _("Total Expenses"),
			"options": "currency",
			"width": 160,
		},
		{"fieldname": "currency", "fieldtype": "Data", "label": _("Currency"), "width": 100},
		{"fieldname": "number_of_entries", "fieldtype": "Int", "label": _("Number of Entries"), "width": 150},
	]


def get_data(filters, currency):
	year = cint(filters.get("year")) or getdate(today()).year
	from_date = filters.get("from_date") or f"{year}-01-01"
	to_date = filters.get("to_date") or f"{year}-12-31"
	rows = get_expense_rows(user=filters.get("user"), from_date=from_date, to_date=to_date)

	grouped = defaultdict(list)
	for row in rows:
		key = getdate(row.posting_date).strftime("%Y-%m")
		grouped[key].append(row)

	data = []
	for key in sorted(grouped):
		year_number, month_number = key.split("-")
		label = f"{calendar.month_name[int(month_number)]} {year_number}"
		data.append(
			{
				"month": label,
				"total_expenses": get_total_in_currency(grouped[key], currency),
				"currency": currency,
				"number_of_entries": len(grouped[key]),
			}
		)
	return data


def get_chart(data, currency):
	return {
		"data": {
			"labels": [row["month"] for row in data],
			"datasets": [{"name": _("Expenses"), "values": [flt(row["total_expenses"]) for row in data]}],
		},
		"type": "line",
	}
