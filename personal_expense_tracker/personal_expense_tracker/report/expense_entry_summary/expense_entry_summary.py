from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate

from personal_expense_tracker.utils import BASE_CURRENCY, is_expense_manager


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "expense_entry",
			"fieldtype": "Link",
			"label": _("Expense Entry"),
			"options": "Expense Entry",
			"width": 180,
		},
		{"fieldname": "posting_date", "fieldtype": "Date", "label": _("Posting Date"), "width": 120},
		{
			"fieldname": "category",
			"fieldtype": "Link",
			"label": _("Category"),
			"options": "Expense Category",
			"width": 160,
		},
		{"fieldname": "description", "fieldtype": "Small Text", "label": _("Description"), "width": 220},
		{"fieldname": "notes", "fieldtype": "Long Text", "label": _("Notes"), "width": 260},
		{
			"fieldname": "amount",
			"fieldtype": "Currency",
			"label": _("Amount"),
			"options": "currency",
			"width": 130,
		},
		{"fieldname": "currency", "fieldtype": "Data", "label": _("Currency"), "width": 90},
		{"fieldname": "exchange_rate_to_base", "fieldtype": "Float", "label": _("Exchange Rate to Base"), "width": 150},
		{"fieldname": "base_currency", "fieldtype": "Data", "label": _("Base Currency"), "width": 120},
		{
			"fieldname": "amount_in_base_currency",
			"fieldtype": "Currency",
			"label": _("Amount in Base Currency"),
			"options": "base_currency",
			"width": 180,
		},
		{"fieldname": "payment_method", "fieldtype": "Data", "label": _("Payment Method"), "width": 130},
		{"fieldname": "reference_no", "fieldtype": "Data", "label": _("Reference No"), "width": 130},
		{"fieldname": "user", "fieldtype": "Link", "label": _("User"), "options": "User", "width": 180},
	]


def get_data(filters):
	query_filters = build_query_filters(filters)
	rows = frappe.get_all(
		"Expense Entry",
		filters=query_filters,
		fields=[
			"name",
			"posting_date",
			"user",
			"category",
			"description",
			"notes",
			"amount",
			"currency",
			"exchange_rate_to_base",
			"base_currency",
			"amount_in_base_currency",
			"payment_method",
			"reference_no",
		],
		order_by="category asc, posting_date desc, creation desc",
	)

	for row in rows:
		row.expense_entry = row.name
		row.base_currency = row.base_currency or BASE_CURRENCY

	return rows


def build_query_filters(filters):
	query_filters = []

	if not is_expense_manager():
		query_filters.append(["user", "=", frappe.session.user])
	elif filters.get("user"):
		query_filters.append(["user", "=", filters.get("user")])

	if filters.get("from_date"):
		query_filters.append(["posting_date", ">=", getdate(filters.get("from_date"))])
	if filters.get("to_date"):
		query_filters.append(["posting_date", "<=", getdate(filters.get("to_date"))])
	if filters.get("category"):
		query_filters.append(["category", "=", filters.get("category")])
	if filters.get("currency"):
		query_filters.append(["currency", "=", filters.get("currency")])
	if filters.get("description"):
		query_filters.append(["description", "like", f"%{filters.get('description')}%"])
	if filters.get("notes"):
		query_filters.append(["notes", "like", f"%{filters.get('notes')}%"])

	return query_filters


def get_chart(data):
	grouped = defaultdict(float)
	for row in data:
		grouped[row.category] += flt(row.amount_in_base_currency)

	return {
		"data": {
			"labels": [_(category or "") for category in grouped],
			"datasets": [{"name": _("Base Amount"), "values": [flt(value) for value in grouped.values()]}],
		},
		"type": "bar",
	}


def get_report_summary(data):
	total_base = sum(flt(row.amount_in_base_currency) for row in data)
	categories = {row.category for row in data if row.category}
	return [
		{
			"value": len(data),
			"label": _("Entries"),
			"datatype": "Int",
		},
		{
			"value": len(categories),
			"label": _("Categories"),
			"datatype": "Int",
		},
		{
			"value": total_base,
			"label": _("Total Base Amount"),
			"datatype": "Currency",
			"currency": BASE_CURRENCY,
		},
	]
