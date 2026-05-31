# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ExpenseCategory(Document):
	def validate(self):
		self.validate_duplicate_active_category_name()
		self.validate_parent_category()

	def validate_duplicate_active_category_name(self):
		if not self.is_active or not self.category_name:
			return

		filters = {
			"category_name": self.category_name,
			"is_active": 1,
			"name": ["!=", self.name],
		}
		if frappe.db.exists("Expense Category", filters):
			frappe.throw(
				_("An active Expense Category named {0} already exists.").format(
					frappe.bold(self.category_name)
				)
			)

	def validate_parent_category(self):
		if self.parent_category and self.parent_category in {self.name, self.category_name}:
			frappe.throw(_("An Expense Category cannot be its own parent category."))
