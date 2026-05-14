# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from personal_expense_tracker.utils import BASE_CURRENCY, MONTHS, SUPPORTED_CURRENCIES, is_expense_manager


class MonthlyBudget(Document):
	def before_validate(self):
		if not self.user and frappe.session.user != "Guest":
			self.user = frappe.session.user

		if self.currency == BASE_CURRENCY:
			self.exchange_rate_to_base = 1

		self.calculate_budget_in_base_currency()

	def validate(self):
		self.validate_user_access()
		self.validate_period()
		self.validate_budget_amount()
		self.validate_currency()
		self.validate_unique_budget()
		self.calculate_budget_in_base_currency()

	def validate_user_access(self):
		if is_expense_manager() or frappe.session.user == "Administrator":
			return

		if self.user != frappe.session.user:
			frappe.throw(_("You can only create or update Monthly Budgets for your own user."))

	def validate_period(self):
		if self.month not in MONTHS:
			frappe.throw(_("Month must be a valid month name."))

		if cint(self.year) <= 0:
			frappe.throw(_("Year must be a valid positive number."))

	def validate_budget_amount(self):
		if flt(self.budget_amount) <= 0:
			frappe.throw(_("Budget Amount must be greater than zero."))

	def validate_currency(self):
		if self.currency not in SUPPORTED_CURRENCIES:
			frappe.throw(_("Currency must be one of: {0}").format(", ".join(SUPPORTED_CURRENCIES)))

		if self.currency != BASE_CURRENCY and flt(self.exchange_rate_to_base) <= 0:
			frappe.throw(_("Exchange Rate to Base must be greater than zero."))

	def validate_unique_budget(self):
		filters = {
			"user": self.user,
			"month": self.month,
			"year": self.year,
			"category": self.category,
			"name": ["!=", self.name],
		}
		if frappe.db.exists("Monthly Budget", filters):
			frappe.throw(
				_("A Monthly Budget already exists for {0}, {1} {2}, and category {3}.").format(
					self.user, self.month, self.year, self.category
				)
			)

	def calculate_budget_in_base_currency(self):
		self.budget_in_base_currency = flt(self.budget_amount) * flt(self.exchange_rate_to_base)
