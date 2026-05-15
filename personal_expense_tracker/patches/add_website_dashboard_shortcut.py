import json

import frappe


WORKSPACE = "Personal Expenses"
SHORTCUT_LABEL = "Website Dashboard"
SHORTCUT_URL = "/expense-tracker"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	add_shortcut_row()
	add_content_card()


def add_shortcut_row():
	if frappe.db.exists("Workspace Shortcut", {"parent": WORKSPACE, "label": SHORTCUT_LABEL}):
		return

	idx = frappe.db.count("Workspace Shortcut", {"parent": WORKSPACE}) + 1
	frappe.get_doc(
		{
			"doctype": "Workspace Shortcut",
			"parent": WORKSPACE,
			"parenttype": "Workspace",
			"parentfield": "shortcuts",
			"idx": idx,
			"type": "URL",
			"url": SHORTCUT_URL,
			"label": SHORTCUT_LABEL,
			"color": "Cyan",
		}
	).insert(ignore_permissions=True)


def add_content_card():
	content = frappe.db.get_value("Workspace", WORKSPACE, "content") or "[]"
	content = json.loads(content)
	if any(row.get("id") == "pet-card-website" for row in content):
		return

	website_card = {
		"id": "pet-card-website",
		"type": "shortcut",
		"data": {"shortcut_name": SHORTCUT_LABEL, "col": 3},
	}
	insert_index = next(
		(index + 1 for index, row in enumerate(content) if row.get("id") == "pet-header-links"),
		len(content),
	)
	content.insert(insert_index, website_card)
	frappe.db.set_value(
		"Workspace",
		WORKSPACE,
		"content",
		json.dumps(content, separators=(",", ":")),
		update_modified=True,
	)
