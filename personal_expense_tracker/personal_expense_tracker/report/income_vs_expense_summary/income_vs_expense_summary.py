import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from personal_expense_tracker.api import (
	get_expense_rows,
	get_income_rows,
	get_total_in_currency,
	get_total_income_in_currency,
)
from personal_expense_tracker.utils import (
	BASE_CURRENCY,
	convert_amount,
	is_expense_manager,
	validate_supported_currency,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	set_default_dates(filters)
	filters.currency = filters.get("currency") or BASE_CURRENCY
	validate_supported_currency(filters.currency)

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def set_default_dates(filters):
	current = getdate(today())
	if not filters.get("from_date"):
		filters.from_date = current.replace(day=1)
	if not filters.get("to_date"):
		filters.to_date = current


def get_columns():
	return [
		{"fieldname": "row_type", "fieldtype": "Data", "label": _("Type"), "width": 150},
		{
			"fieldname": "income_entry",
			"fieldtype": "Link",
			"label": _("Income Entry"),
			"options": "Income Entry",
			"width": 180,
		},
		{"fieldname": "posting_date", "fieldtype": "Date", "label": _("Posting Date"), "width": 120},
		{"fieldname": "user", "fieldtype": "Link", "label": _("User"), "options": "User", "width": 180},
		{"fieldname": "source_or_category", "fieldtype": "Data", "label": _("Source / Category"), "width": 170},
		{"fieldname": "description", "fieldtype": "Small Text", "label": _("Description"), "width": 230},
		{
			"fieldname": "income_amount",
			"fieldtype": "Currency",
			"label": _("Income Amount"),
			"options": "report_currency",
			"width": 150,
		},
		{
			"fieldname": "expense_amount",
			"fieldtype": "Currency",
			"label": _("Expense Amount"),
			"options": "report_currency",
			"width": 150,
		},
		{
			"fieldname": "remaining_amount",
			"fieldtype": "Currency",
			"label": _("Remaining / Savings"),
			"options": "report_currency",
			"width": 170,
		},
		{"fieldname": "usage_percent", "fieldtype": "Percent", "label": _("Income Used %"), "width": 130},
		{"fieldname": "report_currency", "fieldtype": "Data", "label": _("Currency"), "width": 110},
		{"fieldname": "reference_no", "fieldtype": "Data", "label": _("Reference No"), "width": 130},
	]


def get_data(filters):
	user = filters.get("user") if is_expense_manager() else frappe.session.user
	income_rows = get_income_rows(
		user=user,
		from_date=filters.from_date,
		to_date=filters.to_date,
		income_source=filters.get("income_source"),
	)
	expense_rows = get_expense_rows(
		user=user,
		from_date=filters.from_date,
		to_date=filters.to_date,
	)

	report_currency = filters.currency
	total_income = get_total_income_in_currency(income_rows, report_currency)
	total_expenses = get_total_in_currency(expense_rows, report_currency)
	remaining = flt(total_income - total_expenses, 2)
	usage_percent = (total_expenses / total_income * 100) if total_income else 0

	data = []
	for row in income_rows:
		converted_income = convert_amount(
			row.income_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			report_currency,
			row.posting_date,
		)
		data.append(
			{
				"row_type": _("Income"),
				"income_entry": row.name,
				"posting_date": row.posting_date,
				"user": row.user,
				"source_or_category": row.income_source,
				"description": row.description,
				"income_amount": flt(converted_income, 2),
				"expense_amount": 0,
				"remaining_amount": 0,
				"usage_percent": 0,
				"report_currency": report_currency,
				"reference_no": row.get("reference_no"),
			}
		)

	data.append(
		{
			"row_type": _("Total Expenses"),
			"source_or_category": _("All Expense Categories"),
			"description": _("Total expenses in the selected period."),
			"income_amount": 0,
			"expense_amount": total_expenses,
			"remaining_amount": 0,
			"usage_percent": usage_percent,
			"report_currency": report_currency,
		}
	)
	data.append(
		{
			"row_type": _("Unspent Income to Savings"),
			"source_or_category": _("Savings"),
			"description": _("Amount left from income after expenses. Treat this as month-end savings."),
			"income_amount": total_income,
			"expense_amount": total_expenses,
			"remaining_amount": remaining,
			"usage_percent": usage_percent,
			"report_currency": report_currency,
		}
	)
	return data


def get_totals(data):
	if not data:
		return frappe._dict({"total_income": 0, "total_expenses": 0, "remaining": 0, "usage_percent": 0})

	savings_row = data[-1]
	return frappe._dict(
		{
			"total_income": flt(savings_row.get("income_amount")),
			"total_expenses": flt(savings_row.get("expense_amount")),
			"remaining": flt(savings_row.get("remaining_amount")),
			"usage_percent": flt(savings_row.get("usage_percent")),
			"currency": savings_row.get("report_currency") or BASE_CURRENCY,
		}
	)


def get_chart(data):
	totals = get_totals(data)
	return {
		"data": {
			"labels": [_("Total Expenses"), _("Unspent Income to Savings")],
			"datasets": [
				{
					"name": _("Income Allocation"),
					"values": [totals.total_expenses, max(totals.remaining, 0)],
				}
			],
		},
		"type": "donut",
	}


def get_report_summary(data):
	totals = get_totals(data)
	return [
		{
			"value": totals.total_income,
			"label": _("Total Income"),
			"datatype": "Currency",
			"currency": totals.currency,
		},
		{
			"value": totals.total_expenses,
			"label": _("Total Expenses"),
			"datatype": "Currency",
			"currency": totals.currency,
		},
		{
			"value": totals.remaining,
			"label": _("Unspent Income to Savings"),
			"datatype": "Currency",
			"currency": totals.currency,
		},
		{
			"value": totals.usage_percent,
			"label": _("Income Used %"),
			"datatype": "Percent",
		},
	]
