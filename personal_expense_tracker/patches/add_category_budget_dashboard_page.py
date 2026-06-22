from __future__ import annotations

import json

import frappe


WORKSPACE = "Personal Expenses"
SHORTCUT_LABEL = "Category Budget Dashboard"
SHORTCUT_URL = "/desk/category-budget-dashboard"
CONTENT_ID = "pet-card-category-budget-dashboard"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE)
	changed = add_workspace_shortcut(workspace)
	changed = add_workspace_content_card(workspace) or changed

	if changed:
		workspace.save(ignore_permissions=True)
		frappe.db.commit()


def add_workspace_shortcut(workspace):
	for row in workspace.shortcuts:
		if row.label == SHORTCUT_LABEL:
			row.type = "URL"
			row.url = SHORTCUT_URL
			row.color = row.color or "Blue"
			return True

	workspace.append(
		"shortcuts",
		{
			"type": "URL",
			"url": SHORTCUT_URL,
			"label": SHORTCUT_LABEL,
			"color": "Blue",
		},
	)
	return True


def add_workspace_content_card(workspace):
	try:
		content = json.loads(workspace.content or "[]")
	except ValueError:
		return False

	for item in content:
		if item.get("id") == CONTENT_ID:
			return False

	shortcut = {
		"id": CONTENT_ID,
		"type": "shortcut",
		"data": {"shortcut_name": SHORTCUT_LABEL, "col": 3},
	}
	insert_at = len(content)
	for index, item in enumerate(content):
		if item.get("id") == "pet-header-links":
			insert_at = index + 1
			break

	content.insert(insert_at, shortcut)
	workspace.content = json.dumps(content, separators=(",", ":"))
	return True
