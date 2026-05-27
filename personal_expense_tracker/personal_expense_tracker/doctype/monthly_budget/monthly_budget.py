# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from personal_expense_tracker.utils import (
	BASE_CURRENCY,
	MONTHS,
	SUPPORTED_CURRENCIES,
	get_month_date_range,
	is_expense_manager,
)


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
		self.validate_category_budget_period()
		self.validate_budget_total_against_income()

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

	def validate_category_budget_period(self):
		if not self.category or not self.month or not self.year:
			return

		category = frappe.db.get_value(
			"Expense Category",
			self.category,
			["budget_from_date", "budget_to_date"],
			as_dict=True,
		)
		if not category:
			return

		month_start, month_end = get_month_date_range(self.month, self.year)
		if category.budget_from_date and month_end < getdate(category.budget_from_date):
			frappe.throw(
				_("Category {0} budget can only start from {1}.").format(
					self.category, category.budget_from_date
				)
			)
		if category.budget_to_date and month_start > getdate(category.budget_to_date):
			frappe.throw(
				_("Category {0} budget can only be used until {1}.").format(
					self.category, category.budget_to_date
				)
			)

	def validate_budget_total_against_income(self):
		if not self.user or not self.month or not self.year:
			return

		if not frappe.db.exists("DocType", "Income Entry"):
			return

		month_start, month_end = get_month_date_range(self.month, self.year)
		income_rows = frappe.get_all(
			"Income Entry",
			filters={
				"user": self.user,
				"posting_date": ["between", [month_start, month_end]],
			},
			fields=["income_in_base_currency"],
		)
		total_income = sum(flt(row.income_in_base_currency) for row in income_rows)

		budget_rows = frappe.get_all(
			"Monthly Budget",
			filters={
				"user": self.user,
				"month": self.month,
				"year": self.year,
				"name": ["!=", self.name],
			},
			fields=["budget_in_base_currency"],
		)
		other_budgets = sum(flt(row.budget_in_base_currency) for row in budget_rows)
		total_budget = flt(other_budgets + flt(self.budget_in_base_currency), 2)

		if total_budget > total_income:
			frappe.throw(
				_(
					"Total monthly budgets ({0}) cannot be greater than total monthly income ({1}) for {2} {3}."
				).format(
					frappe.bold(f"{BASE_CURRENCY} {total_budget:,.2f}"),
					frappe.bold(f"{BASE_CURRENCY} {total_income:,.2f}"),
					self.month,
					self.year,
				)
			)

	def calculate_budget_in_base_currency(self):
		self.budget_in_base_currency = flt(self.budget_amount) * flt(self.exchange_rate_to_base)
