import json

import frappe


WORKSPACE = "Personal Expenses"
INCOME_LABEL = "Income Entry"
SAVINGS_CATEGORY = "Savings"


def execute():
	create_savings_category()
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	add_income_workspace_link()
	add_income_shortcut()
	add_income_content_card()


def create_savings_category():
	if frappe.db.exists("Expense Category", SAVINGS_CATEGORY):
		return

	frappe.get_doc(
		{
			"doctype": "Expense Category",
			"category_name": SAVINGS_CATEGORY,
			"is_active": 1,
			"description": "Savings category for money intentionally set aside.",
		}
	).insert(ignore_permissions=True)


def add_income_workspace_link():
	if frappe.db.exists("Workspace Link", {"parent": WORKSPACE, "label": INCOME_LABEL}):
		return

	transaction_card = frappe.db.get_value(
		"Workspace Link",
		{"parent": WORKSPACE, "type": "Card Break", "label": "Transactions"},
		["name", "link_count"],
		as_dict=True,
	)
	if transaction_card:
		frappe.db.set_value(
			"Workspace Link",
			transaction_card.name,
			"link_count",
			(transaction_card.link_count or 0) + 1,
			update_modified=False,
		)

	idx = frappe.db.count("Workspace Link", {"parent": WORKSPACE}) + 1
	frappe.get_doc(
		{
			"doctype": "Workspace Link",
			"parent": WORKSPACE,
			"parenttype": "Workspace",
			"parentfield": "links",
			"idx": idx,
			"type": "Link",
			"label": INCOME_LABEL,
			"link_type": "DocType",
			"link_to": INCOME_LABEL,
			"hidden": 0,
			"is_query_report": 0,
			"onboard": 0,
		}
	).insert(ignore_permissions=True)


def add_income_shortcut():
	if frappe.db.exists("Workspace Shortcut", {"parent": WORKSPACE, "label": INCOME_LABEL}):
		return

	idx = frappe.db.count("Workspace Shortcut", {"parent": WORKSPACE}) + 1
	frappe.get_doc(
		{
			"doctype": "Workspace Shortcut",
			"parent": WORKSPACE,
			"parenttype": "Workspace",
			"parentfield": "shortcuts",
			"idx": idx,
			"type": "DocType",
			"link_to": INCOME_LABEL,
			"label": INCOME_LABEL,
			"doc_view": "List",
			"color": "Cyan",
		}
	).insert(ignore_permissions=True)


def add_income_content_card():
	content = frappe.db.get_value("Workspace", WORKSPACE, "content") or "[]"
	content = json.loads(content)
	if any(row.get("id") == "pet-card-income" for row in content):
		return

	income_card = {
		"id": "pet-card-income",
		"type": "shortcut",
		"data": {"shortcut_name": INCOME_LABEL, "col": 3},
	}
	insert_index = next(
		(index + 1 for index, row in enumerate(content) if row.get("id") == "pet-card-website"),
		len(content),
	)
	content.insert(insert_index, income_card)
	frappe.db.set_value(
		"Workspace",
		WORKSPACE,
		"content",
		json.dumps(content, separators=(",", ":")),
		update_modified=True,
	)
