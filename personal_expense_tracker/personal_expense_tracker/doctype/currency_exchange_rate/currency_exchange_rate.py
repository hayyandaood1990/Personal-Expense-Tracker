# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from personal_expense_tracker.utils import SUPPORTED_CURRENCIES, get_latest_rate_record


class CurrencyExchangeRate(Document):
	def validate(self):
		self.validate_currencies()
		self.validate_exchange_rate()
		self.validate_single_active_rate()

	def validate_currencies(self):
		for fieldname, label in (("from_currency", _("From Currency")), ("to_currency", _("To Currency"))):
			value = self.get(fieldname)
			if value not in SUPPORTED_CURRENCIES:
				frappe.throw(
					_("{0} must be one of: {1}").format(label, ", ".join(SUPPORTED_CURRENCIES))
				)

		if self.from_currency == self.to_currency:
			frappe.throw(_("From Currency and To Currency cannot be the same."))

	def validate_exchange_rate(self):
		if flt(self.exchange_rate) <= 0:
			frappe.throw(_("Exchange Rate must be greater than zero."))

	def validate_single_active_rate(self):
		if not self.is_active:
			return

		filters = {
			"from_currency": self.from_currency,
			"to_currency": self.to_currency,
			"effective_date": self.effective_date,
			"is_active": 1,
			"name": ["!=", self.name],
		}
		if frappe.db.exists("Currency Exchange Rate", filters):
			frappe.throw(
				_(
					"Only one active exchange rate is allowed for {0} to {1} on {2}."
				).format(self.from_currency, self.to_currency, self.effective_date)
			)


def get_latest_exchange_rate(from_currency, to_currency, posting_date=None):
	return get_latest_rate_record(from_currency, to_currency, posting_date)
