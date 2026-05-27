# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from personal_expense_tracker.utils import SUPPORTED_CURRENCIES, is_expense_manager


class IncomeEntry(Document):
	def before_validate(self):
		if not self.user and frappe.session.user != "Guest":
			self.user = frappe.session.user

		if self.currency and self.base_currency and self.currency == self.base_currency:
			self.exchange_rate_to_base = 1

		self.calculate_income_in_base_currency()

	def validate(self):
		self.validate_amount()
		self.validate_currencies()
		self.validate_exchange_rate()
		self.validate_posting_date()
		self.validate_user_access()
		self.calculate_income_in_base_currency()

	def validate_amount(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Income Amount must be greater than zero."))

	def validate_currencies(self):
		for fieldname, label in (("currency", _("Currency")), ("base_currency", _("Base Currency"))):
			value = self.get(fieldname)
			if value not in SUPPORTED_CURRENCIES:
				frappe.throw(
					_("{0} must be one of: {1}").format(label, ", ".join(SUPPORTED_CURRENCIES))
				)

	def validate_exchange_rate(self):
		if self.currency == self.base_currency:
			self.exchange_rate_to_base = 1
		elif flt(self.exchange_rate_to_base) <= 0:
			frappe.throw(_("Exchange Rate to Base must be greater than zero."))

	def validate_posting_date(self):
		if getdate(self.posting_date) > getdate(today()) and not is_expense_manager():
			frappe.throw(_("Only users with the Expense Manager role can enter future dated income."))

	def validate_user_access(self):
		if is_expense_manager() or frappe.session.user == "Administrator":
			return

		if self.user != frappe.session.user:
			frappe.throw(_("You can only create or update Income Entries for your own user."))

	def calculate_income_in_base_currency(self):
		self.income_in_base_currency = flt(self.amount) * flt(self.exchange_rate_to_base)
