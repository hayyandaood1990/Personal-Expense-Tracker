from __future__ import annotations

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

SUPPORTED_CURRENCIES = ("SYP", "USD", "EUR")
BASE_CURRENCY = "SYP"
MONTHS = (
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
)


def is_expense_manager(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	return bool({"Expense Manager", "System Manager"} & roles)


def validate_supported_currency(currency: str, label: str | None = None) -> None:
	if currency not in SUPPORTED_CURRENCIES:
		frappe.throw(
			_("{0} must be one of: {1}").format(label or _("Currency"), ", ".join(SUPPORTED_CURRENCIES))
		)


def get_latest_rate_record(from_currency: str, to_currency: str, posting_date: str | date | None = None):
	validate_supported_currency(from_currency, _("From Currency"))
	validate_supported_currency(to_currency, _("To Currency"))

	if from_currency == to_currency:
		return frappe._dict(
			{
				"exchange_rate": 1,
				"from_currency": from_currency,
				"to_currency": to_currency,
				"effective_date": getdate(posting_date or nowdate()),
				"name": None,
			}
		)

	posting_date = getdate(posting_date or nowdate())
	rate = frappe.db.get_all(
		"Currency Exchange Rate",
		filters={
			"from_currency": from_currency,
			"to_currency": to_currency,
			"is_active": 1,
			"effective_date": ["<=", posting_date],
		},
		fields=["name", "from_currency", "to_currency", "exchange_rate", "effective_date"],
		order_by="effective_date desc, modified desc",
		limit=1,
	)

	return frappe._dict(rate[0]) if rate else None


def get_conversion_rate(from_currency: str, to_currency: str, posting_date: str | date | None = None) -> float:
	if from_currency == to_currency:
		return 1.0

	rate = get_latest_rate_record(from_currency, to_currency, posting_date)
	if rate:
		return flt(rate.exchange_rate)

	inverse_rate = get_latest_rate_record(to_currency, from_currency, posting_date)
	if inverse_rate and flt(inverse_rate.exchange_rate):
		return 1 / flt(inverse_rate.exchange_rate)

	frappe.throw(
		_("No active exchange rate found for {0} to {1} on or before {2}.").format(
			from_currency, to_currency, getdate(posting_date or nowdate())
		)
	)


def convert_amount(
	amount: float,
	from_currency: str,
	to_currency: str = BASE_CURRENCY,
	posting_date: str | date | None = None,
) -> float:
	return flt(amount) * get_conversion_rate(from_currency, to_currency, posting_date)


def get_month_date_range(month: str, year: int) -> tuple[date, date]:
	if month not in MONTHS:
		frappe.throw(_("Month must be a valid month name."))

	month_number = MONTHS.index(month) + 1
	year = int(year)
	last_day = calendar.monthrange(year, month_number)[1]
	return date(year, month_number, 1), date(year, month_number, last_day)
