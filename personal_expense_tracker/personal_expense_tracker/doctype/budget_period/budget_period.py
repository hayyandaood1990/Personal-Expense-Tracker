# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

from personal_expense_tracker.budget_period import get_budget_period_name
from personal_expense_tracker.utils import MONTHS


class BudgetPeriod(Document):
	def before_validate(self):
		if self.from_date and self.to_date and not self.period_name:
			self.period_name = get_budget_period_name(self.from_date, self.to_date)

		if self.to_date:
			to_date = getdate(self.to_date)
			self.month = self.month or MONTHS[to_date.month - 1]
			self.year = self.year or to_date.year

	def validate(self):
		self.validate_dates()
		self.validate_month_year()
		self.validate_overlap()

	def validate_dates(self):
		if not self.from_date or not self.to_date:
			return

		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date."))

	def validate_month_year(self):
		if self.month not in MONTHS:
			frappe.throw(_("Month must be a valid month name."))

		if cint(self.year) <= 0:
			frappe.throw(_("Year must be a valid positive number."))

	def validate_overlap(self):
		if not self.from_date or not self.to_date:
			return

		overlaps = frappe.get_all(
			"Budget Period",
			filters=[
				["name", "!=", self.name],
				["from_date", "<=", getdate(self.to_date)],
				["to_date", ">=", getdate(self.from_date)],
			],
			pluck="name",
			limit=1,
		)
		if overlaps:
			frappe.throw(
				_("Budget Period {0} overlaps with {1}.").format(
					frappe.bold(self.period_name), frappe.bold(overlaps[0])
				)
			)
