# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from personal_expense_tracker.utils import (
	BASE_CURRENCY,
	MONTHS,
	SUPPORTED_CURRENCIES,
	is_expense_manager,
)
from personal_expense_tracker.budget_period import (
	get_budget_period_date_range,
	get_budget_period_for_date,
)


class MonthlyBudget(Document):
	def before_validate(self):
		if not self.user and frappe.session.user != "Guest":
			self.user = frappe.session.user

		if self.currency == BASE_CURRENCY:
			self.exchange_rate_to_base = 1

		self.set_default_budget_period()
		self.sync_budget_period_fields()
		self.calculate_budget_in_base_currency()

	def validate(self):
		self.validate_user_access()
		self.validate_period()
		self.validate_budget_amount()
		self.validate_currency()
		self.validate_unique_budget()
		self.calculate_budget_in_base_currency()
		self.validate_budget_total_against_income()

	def set_default_budget_period(self):
		if self.budget_period:
			return

		period = get_budget_period_for_date(create_if_missing=True)
		if period:
			self.budget_period = period.name

	def sync_budget_period_fields(self):
		if not self.budget_period:
			return

		period = frappe.db.get_value(
			"Budget Period",
			self.budget_period,
			["from_date", "to_date", "month", "year"],
			as_dict=True,
		)
		if not period:
			frappe.throw(_("Budget Period {0} does not exist.").format(self.budget_period))

		self.from_date = period.from_date
		self.to_date = period.to_date
		self.month = period.month
		self.year = period.year

	def validate_user_access(self):
		if is_expense_manager() or frappe.session.user == "Administrator":
			return

		if self.user != frappe.session.user:
			frappe.throw(_("You can only create or update Monthly Budgets for your own user."))

	def validate_period(self):
		if not self.budget_period:
			frappe.throw(_("Budget Period is required."))

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
			"budget_period": self.budget_period,
			"category": self.category,
			"name": ["!=", self.name],
		}
		if frappe.db.exists("Monthly Budget", filters):
			frappe.throw(
				_("A Monthly Budget already exists for {0}, period {1}, and category {2}.").format(
					self.user, self.budget_period, self.category
				)
			)

	def validate_budget_total_against_income(self):
		if not self.user or not self.budget_period:
			return

		if not frappe.db.exists("DocType", "Income Entry"):
			return

		from_date, to_date = get_budget_period_date_range(self.budget_period)
		income_rows = frappe.get_all(
			"Income Entry",
			filters={
				"user": self.user,
				"posting_date": ["between", [from_date, to_date]],
			},
			fields=["income_in_base_currency"],
		)
		total_income = sum(flt(row.income_in_base_currency) for row in income_rows)

		budget_rows = frappe.get_all(
			"Monthly Budget",
			filters={
				"user": self.user,
				"budget_period": self.budget_period,
				"name": ["!=", self.name],
			},
			fields=["budget_in_base_currency"],
		)
		other_budgets = sum(flt(row.budget_in_base_currency) for row in budget_rows)
		total_budget = flt(other_budgets + flt(self.budget_in_base_currency), 2)

		if total_budget > total_income:
			frappe.throw(
				_(
					"Total budgets ({0}) cannot be greater than total income ({1}) for budget period {2}."
				).format(
					frappe.bold(f"{BASE_CURRENCY} {total_budget:,.2f}"),
					frappe.bold(f"{BASE_CURRENCY} {total_income:,.2f}"),
					self.budget_period,
				)
			)

	def calculate_budget_in_base_currency(self):
		self.budget_in_base_currency = flt(self.budget_amount) * flt(self.exchange_rate_to_base)
