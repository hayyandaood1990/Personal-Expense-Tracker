import frappe


WORKSPACE = "Personal Expenses"
REPORT_LABEL = "Expense Entry Summary"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	if frappe.db.exists("Workspace Link", {"parent": WORKSPACE, "label": REPORT_LABEL}):
		return

	report_card = frappe.db.get_value(
		"Workspace Link",
		{"parent": WORKSPACE, "type": "Card Break", "label": "Reports"},
		["name", "link_count"],
		as_dict=True,
	)
	if report_card:
		frappe.db.set_value(
			"Workspace Link",
			report_card.name,
			"link_count",
			(report_card.link_count or 0) + 1,
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
			"is_query_report": 1,
			"hidden": 0,
			"onboard": 0,
		}
	).insert(ignore_permissions=True)
