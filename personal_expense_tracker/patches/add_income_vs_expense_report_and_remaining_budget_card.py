import json

import frappe


WORKSPACE = "Personal Expenses"
REPORT_LABEL = "Income vs Expense Summary"
CARD_LABEL = "Remaining Budget"


def execute():
	upsert_remaining_budget_number_card()
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	add_report_workspace_link()
	add_remaining_budget_number_card()
	add_remaining_budget_content_card()


def upsert_remaining_budget_number_card():
	values = {
		"doctype": "Number Card",
		"name": CARD_LABEL,
		"label": CARD_LABEL,
		"type": "Custom",
		"method": "personal_expense_tracker.api.get_remaining_budget_card",
		"document_type": "Income Entry",
		"is_public": 1,
		"is_standard": 0,
		"module": "Personal Expense Tracker",
		"show_full_number": 1,
		"show_percentage_stats": 0,
		"color": "#00a88e",
	}
	if frappe.db.exists("Number Card", CARD_LABEL):
		doc = frappe.get_doc("Number Card", CARD_LABEL)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return

	frappe.get_doc(values).insert(ignore_permissions=True)


def add_report_workspace_link():
	if frappe.db.exists("Workspace Link", {"parent": WORKSPACE, "label": REPORT_LABEL}):
		return

	reports_card = frappe.db.get_value(
		"Workspace Link",
		{"parent": WORKSPACE, "type": "Card Break", "label": "Reports"},
		["name", "link_count"],
		as_dict=True,
	)
	if reports_card:
		frappe.db.set_value(
			"Workspace Link",
			reports_card.name,
			"link_count",
			(reports_card.link_count or 0) + 1,
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
			"label": REPORT_LABEL,
			"link_type": "Report",
			"link_to": REPORT_LABEL,
			"hidden": 0,
			"is_query_report": 1,
			"onboard": 0,
		}
	).insert(ignore_permissions=True)


def add_remaining_budget_number_card():
	if frappe.db.exists("Workspace Number Card", {"parent": WORKSPACE, "number_card_name": CARD_LABEL}):
		return

	idx = frappe.db.count("Workspace Number Card", {"parent": WORKSPACE}) + 1
	frappe.get_doc(
		{
			"doctype": "Workspace Number Card",
			"parent": WORKSPACE,
			"parenttype": "Workspace",
			"parentfield": "number_cards",
			"idx": idx,
			"number_card_name": CARD_LABEL,
			"label": CARD_LABEL,
		}
	).insert(ignore_permissions=True)


def add_remaining_budget_content_card():
	content = frappe.db.get_value("Workspace", WORKSPACE, "content") or "[]"
	content = json.loads(content)
	if any(row.get("id") == "pet-card-remaining-budget" for row in content):
		return

	remaining_card = {
		"id": "pet-card-remaining-budget",
		"type": "number_card",
		"data": {"number_card_name": CARD_LABEL, "col": 3},
	}
	insert_index = next(
		(index + 1 for index, row in enumerate(content) if row.get("id") == "pet-card-budget"),
		len(content),
	)
	content.insert(insert_index, remaining_card)
	frappe.db.set_value(
		"Workspace",
		WORKSPACE,
		"content",
		json.dumps(content, separators=(",", ":")),
		update_modified=True,
	)
