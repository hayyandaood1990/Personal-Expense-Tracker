from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from personal_expense_tracker.api import get_expense_rows
from personal_expense_tracker.utils import BASE_CURRENCY, convert_amount, validate_supported_currency


def execute(filters=None):
	filters = frappe._dict(filters or {})
	currency = filters.get("currency") or BASE_CURRENCY
	validate_supported_currency(currency)

	columns = get_columns()
	data = get_data(filters, currency)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{
			"fieldname": "category",
			"fieldtype": "Link",
			"label": _("Category"),
			"options": "Expense Category",
			"width": 180,
		},
		{
			"fieldname": "total_expenses",
			"fieldtype": "Currency",
			"label": _("Total Expenses"),
			"options": "currency",
			"width": 160,
		},
		{"fieldname": "percentage_of_total", "fieldtype": "Percent", "label": _("Percentage of Total"), "width": 160},
		{"fieldname": "number_of_entries", "fieldtype": "Int", "label": _("Number of Entries"), "width": 150},
	]


def get_data(filters, currency):
	rows = get_expense_rows(
		user=filters.get("user"),
		from_date=filters.get("from_date"),
		to_date=filters.get("to_date"),
	)
	grouped = defaultdict(lambda: {"total": 0, "count": 0})

	for row in rows:
		grouped[row.category]["total"] += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			currency,
			row.posting_date,
		)
		grouped[row.category]["count"] += 1

	grand_total = sum(row["total"] for row in grouped.values())
	data = []
	for category, values in sorted(grouped.items(), key=lambda item: item[1]["total"], reverse=True):
		data.append(
			{
				"category": category,
				"total_expenses": values["total"],
				"currency": currency,
				"percentage_of_total": (values["total"] / grand_total * 100) if grand_total else 0,
				"number_of_entries": values["count"],
			}
		)
	return data


def get_chart(data):
	return {
		"data": {
			"labels": [row["category"] for row in data],
			"datasets": [{"name": _("Expenses"), "values": [flt(row["total_expenses"]) for row in data]}],
		},
		"type": "donut",
	}
