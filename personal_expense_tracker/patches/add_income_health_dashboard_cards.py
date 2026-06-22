from __future__ import annotations

import json

import frappe


WORKSPACE = "Personal Expenses"
CARDS = [
	{
		"name": "Income Used",
		"label": "Income Used",
		"method": "personal_expense_tracker.api.get_income_used_card",
		"document_type": "Expense Entry",
		"color": "#2d9cdb",
		"content_id": "pet-card-income-used",
	},
	{
		"name": "Income Left",
		"label": "Income Left",
		"method": "personal_expense_tracker.api.get_income_left_card",
		"document_type": "Income Entry",
		"color": "#27ae60",
		"content_id": "pet-card-income-left",
	},
]


def execute():
	for card in CARDS:
		upsert_number_card(card)

	if frappe.db.exists("Workspace", WORKSPACE):
		workspace = frappe.get_doc("Workspace", WORKSPACE)
		changed = add_workspace_cards(workspace)
		if changed:
			workspace.save(ignore_permissions=True)
			frappe.db.commit()


def upsert_number_card(card):
	values = {
		"doctype": "Number Card",
		"name": card["name"],
		"label": card["label"],
		"type": "Custom",
		"method": card["method"],
		"document_type": card["document_type"],
		"is_public": 1,
		"is_standard": 0,
		"module": "Personal Expense Tracker",
		"show_full_number": 1,
		"show_percentage_stats": 0,
		"color": card["color"],
	}

	if frappe.db.exists("Number Card", card["name"]):
		doc = frappe.get_doc("Number Card", card["name"])
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc(values).insert(ignore_permissions=True)


def add_workspace_cards(workspace):
	changed = False
	existing_cards = {row.number_card_name for row in workspace.number_cards}
	for card in CARDS:
		if card["name"] not in existing_cards:
			workspace.append(
				"number_cards",
				{"number_card_name": card["name"], "label": card["label"]},
			)
			changed = True

	try:
		content = json.loads(workspace.content or "[]")
	except ValueError:
		return changed

	existing_content_ids = {item.get("id") for item in content}
	insert_at = 0
	for index, item in enumerate(content):
		if item.get("id") == "pet-card-remaining-budget":
			insert_at = index + 1
			break

	for card in CARDS:
		if card["content_id"] in existing_content_ids:
			continue
		content.insert(
			insert_at,
			{
				"id": card["content_id"],
				"type": "number_card",
				"data": {"number_card_name": card["name"], "col": 3},
			},
		)
		insert_at += 1
		changed = True

	if changed:
		workspace.content = json.dumps(content, separators=(",", ":"))
	return changed
