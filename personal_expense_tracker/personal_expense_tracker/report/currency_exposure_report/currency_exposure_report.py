from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from personal_expense_tracker.api import get_expense_rows


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"fieldname": "currency", "fieldtype": "Data", "label": _("Currency"), "width": 100},
		{
			"fieldname": "total_original_amount",
			"fieldtype": "Currency",
			"label": _("Total Original Amount"),
			"options": "currency",
			"width": 180,
		},
		{
			"fieldname": "total_base_amount",
			"fieldtype": "Currency",
			"label": _("Total Base Amount"),
			"width": 180,
		},
		{"fieldname": "average_exchange_rate", "fieldtype": "Float", "label": _("Average Exchange Rate"), "width": 180},
	]


def get_data(filters):
	rows = get_expense_rows(
		user=filters.get("user"),
		from_date=filters.get("from_date"),
		to_date=filters.get("to_date"),
	)
	grouped = defaultdict(lambda: {"original": 0, "base": 0, "rate_total": 0, "count": 0})

	for row in rows:
		grouped[row.currency]["original"] += flt(row.amount)
		grouped[row.currency]["base"] += flt(row.amount_in_base_currency)
		grouped[row.currency]["rate_total"] += flt(row.exchange_rate_to_base)
		grouped[row.currency]["count"] += 1

	data = []
	for currency, values in sorted(grouped.items()):
		data.append(
			{
				"currency": currency,
				"total_original_amount": values["original"],
				"total_base_amount": values["base"],
				"average_exchange_rate": values["rate_total"] / values["count"] if values["count"] else 0,
			}
		)
	return data


def get_chart(data):
	return {
		"data": {
			"labels": [row["currency"] for row in data],
			"datasets": [{"name": _("Base Amount"), "values": [flt(row["total_base_amount"]) for row in data]}],
		},
		"type": "bar",
		"fieldtype": "Currency",
	}
