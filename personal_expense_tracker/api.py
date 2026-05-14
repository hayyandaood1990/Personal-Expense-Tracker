from __future__ import annotations

import calendar
import re
from collections import defaultdict

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, fmt_money, getdate, nowdate, today

from personal_expense_tracker.utils import (
	BASE_CURRENCY,
	MONTHS,
	SUPPORTED_CURRENCIES,
	convert_amount,
	get_latest_rate_record,
	get_month_date_range,
	is_expense_manager,
	validate_supported_currency,
)

DEFAULT_EXCHANGE_RATE_API_URL = "https://open.er-api.com/v6/latest/{base_currency}"
DEFAULT_EXCHANGE_RATE_API_SOURCE = "open.er-api.com"
SP_TODAY_RATE_SOURCE = "sp-today.com"
SP_TODAY_CURRENCY_PAGES = {
	"USD": "https://sp-today.com/en/currency/us-dollar",
	"EUR": "https://sp-today.com/en/currency/euro",
}
SP_TODAY_RATE_TYPES = ("buy", "sell", "mid")


@frappe.whitelist()
def get_latest_exchange_rate(from_currency, to_currency, posting_date=None):
	return get_latest_rate_record(from_currency, to_currency, posting_date)


def get_exchange_rate_api_url(base_currency):
	configured_url = frappe.conf.get("personal_expense_tracker_exchange_rate_api_url")
	url = configured_url or DEFAULT_EXCHANGE_RATE_API_URL
	return url.format(base_currency=base_currency)


def ensure_can_sync_exchange_rates():
	if not is_expense_manager():
		frappe.throw(_("Only Expense Managers can sync exchange rates."))


def fetch_exchange_rates_from_api(base_currency="USD", provider_url=None):
	validate_supported_currency(base_currency, _("Base Currency"))
	url = (provider_url or get_exchange_rate_api_url(base_currency)).format(
		base_currency=base_currency
	)

	try:
		response = requests.get(url, timeout=15)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.throw(_("Could not fetch exchange rates from API: {0}").format(str(exc)))

	try:
		data = response.json()
	except ValueError:
		frappe.throw(_("Exchange-rate API returned an invalid JSON response."))

	if data.get("result") == "error" or data.get("success") is False:
		error = data.get("error-type") or data.get("error") or _("Unknown API error")
		frappe.throw(_("Exchange-rate API returned an error: {0}").format(error))

	rates = data.get("rates") or data.get("conversion_rates")
	provider_base_currency = data.get("base_code") or data.get("base") or base_currency
	validate_supported_currency(provider_base_currency, _("API Base Currency"))

	if not isinstance(rates, dict):
		frappe.throw(_("Exchange-rate API response does not contain a rates object."))

	rates[provider_base_currency] = rates.get(provider_base_currency) or 1
	missing_currencies = [currency for currency in SUPPORTED_CURRENCIES if currency not in rates]
	if missing_currencies:
		frappe.throw(
			_("Exchange-rate API response is missing rates for: {0}").format(
				", ".join(missing_currencies)
			)
		)

	return frappe._dict(
		{
			"rates": {currency: flt(rates[currency]) for currency in SUPPORTED_CURRENCIES},
			"base_currency": provider_base_currency,
			"source": data.get("provider") or DEFAULT_EXCHANGE_RATE_API_SOURCE,
			"source_url": url,
			"provider_timestamp": data.get("time_last_update_utc") or data.get("date"),
		}
	)


def normalize_sp_today_amount(value):
	return flt(value.replace(",", "").replace("SYP", "").strip())


def get_sp_today_rate_type(rate_type=None):
	rate_type = (
		rate_type or frappe.conf.get("personal_expense_tracker_sp_today_rate_type") or "sell"
	).lower()
	if rate_type not in SP_TODAY_RATE_TYPES:
		frappe.throw(
			_("SP Today rate type must be one of: {0}").format(", ".join(SP_TODAY_RATE_TYPES))
		)

	return rate_type


def extract_sp_today_rates(html, currency):
	text = re.sub(r"<[^>]+>", " ", html)
	text = re.sub(r"\s+", " ", text)
	match = re.search(
		rf"1\s+{currency}\s+([\d,]+)\s+SYP\s+([\d,]+)\s+SYP",
		text,
		flags=re.IGNORECASE,
	)
	if not match:
		frappe.throw(_("Could not read {0}/SYP rates from SP Today page.").format(currency))

	return frappe._dict(
		{
			"buy": normalize_sp_today_amount(match.group(1)),
			"sell": normalize_sp_today_amount(match.group(2)),
		}
	)


def fetch_sp_today_currency_rate(currency):
	url = SP_TODAY_CURRENCY_PAGES.get(currency)
	if not url:
		frappe.throw(_("SP Today page is not configured for {0}.").format(currency))

	try:
		response = requests.get(
			url,
			timeout=15,
			headers={"User-Agent": "PersonalExpenseTracker/0.0.1"},
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.throw(
			_("Could not fetch {0}/SYP rates from SP Today: {1}").format(
				currency, str(exc)
			)
		)

	rates = extract_sp_today_rates(response.text, currency)
	if rates.buy <= 0 or rates.sell <= 0:
		frappe.throw(_("SP Today returned an invalid {0}/SYP rate.").format(currency))

	return rates


def select_sp_today_rate(rates, rate_type):
	if rate_type == "mid":
		return flt((rates.buy + rates.sell) / 2, 9)

	return flt(rates.get(rate_type), 9)


def fetch_exchange_rates_from_sp_today(rate_type=None):
	rate_type = get_sp_today_rate_type(rate_type)
	usd_rates = fetch_sp_today_currency_rate("USD")
	eur_rates = fetch_sp_today_currency_rate("EUR")

	usd_to_syp = select_sp_today_rate(usd_rates, rate_type)
	eur_to_syp = select_sp_today_rate(eur_rates, rate_type)
	if usd_to_syp <= 0 or eur_to_syp <= 0:
		frappe.throw(_("SP Today returned an invalid exchange rate."))

	return frappe._dict(
		{
			"rates": {
				"SYP": 1,
				"USD": 1 / usd_to_syp,
				"EUR": 1 / eur_to_syp,
			},
			"source": SP_TODAY_RATE_SOURCE,
			"source_url": ", ".join(SP_TODAY_CURRENCY_PAGES.values()),
			"provider_timestamp": None,
			"rate_type": rate_type,
			"provider_rates": {
				"USD": {"buy": usd_rates.buy, "sell": usd_rates.sell},
				"EUR": {"buy": eur_rates.buy, "sell": eur_rates.sell},
			},
		}
	)


def get_supported_currency_pairs(api_rates):
	for from_currency in SUPPORTED_CURRENCIES:
		for to_currency in SUPPORTED_CURRENCIES:
			if from_currency == to_currency:
				continue

			from_rate = flt(api_rates[from_currency])
			to_rate = flt(api_rates[to_currency])
			if from_rate <= 0 or to_rate <= 0:
				frappe.throw(
					_("Invalid API rate received for {0} or {1}.").format(
						from_currency, to_currency
					)
				)

			yield frappe._dict(
				{
					"from_currency": from_currency,
					"to_currency": to_currency,
					"exchange_rate": flt(to_rate / from_rate, 9),
				}
			)


def upsert_exchange_rate(pair, effective_date, source, notes):
	filters = {
		"from_currency": pair.from_currency,
		"to_currency": pair.to_currency,
		"effective_date": effective_date,
		"is_active": 1,
	}
	name = frappe.db.exists("Currency Exchange Rate", filters)
	if name:
		doc = frappe.get_doc("Currency Exchange Rate", name)
		doc.exchange_rate = pair.exchange_rate
		doc.source = source[:140] if source else DEFAULT_EXCHANGE_RATE_API_SOURCE
		doc.notes = notes
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Currency Exchange Rate",
				"from_currency": pair.from_currency,
				"to_currency": pair.to_currency,
				"exchange_rate": pair.exchange_rate,
				"effective_date": effective_date,
				"is_active": 1,
				"source": source[:140] if source else DEFAULT_EXCHANGE_RATE_API_SOURCE,
				"notes": notes,
			}
		)
		doc.insert(ignore_permissions=True)

	return doc


def save_exchange_rate_result(api_result, effective_date, notes):
	updated_rates = []
	for pair in get_supported_currency_pairs(api_result.rates):
		doc = upsert_exchange_rate(
			pair=pair,
			effective_date=effective_date,
			source=api_result.source,
			notes=notes,
		)
		updated_rates.append(
			{
				"name": doc.name,
				"from_currency": doc.from_currency,
				"to_currency": doc.to_currency,
				"exchange_rate": doc.exchange_rate,
				"effective_date": doc.effective_date,
			}
		)

	return updated_rates


@frappe.whitelist()
def sync_exchange_rates_from_api(base_currency="USD", effective_date=None, provider_url=None):
	ensure_can_sync_exchange_rates()
	validate_supported_currency(base_currency, _("Base Currency"))
	effective_date = getdate(effective_date or today())
	api_result = fetch_exchange_rates_from_api(base_currency=base_currency, provider_url=provider_url)

	notes = _("Synced from live exchange-rate API on {0}. Provider timestamp: {1}").format(
		nowdate(), api_result.provider_timestamp or _("not provided")
	)
	updated_rates = save_exchange_rate_result(api_result, effective_date, notes)

	return {
		"effective_date": effective_date,
		"source": api_result.source,
		"source_url": api_result.source_url,
		"provider_timestamp": api_result.provider_timestamp,
		"updated_rates": updated_rates,
	}


@frappe.whitelist()
def sync_exchange_rates_from_sp_today(effective_date=None, rate_type=None):
	ensure_can_sync_exchange_rates()
	effective_date = getdate(effective_date or today())
	api_result = fetch_exchange_rates_from_sp_today(rate_type=rate_type)
	notes = _(
		"Synced from SP Today public currency pages on {0}. Rate type: {1}. "
		"USD buy/sell: {2}/{3}. EUR buy/sell: {4}/{5}."
	).format(
		nowdate(),
		api_result.rate_type,
		api_result.provider_rates["USD"]["buy"],
		api_result.provider_rates["USD"]["sell"],
		api_result.provider_rates["EUR"]["buy"],
		api_result.provider_rates["EUR"]["sell"],
	)
	updated_rates = save_exchange_rate_result(api_result, effective_date, notes)

	return {
		"effective_date": effective_date,
		"source": api_result.source,
		"source_url": api_result.source_url,
		"rate_type": api_result.rate_type,
		"provider_rates": api_result.provider_rates,
		"updated_rates": updated_rates,
	}


def resolve_user_filter(user=None):
	if is_expense_manager():
		return user

	return frappe.session.user


def get_expense_rows(user=None, from_date=None, to_date=None, category=None, currency=None):
	filters = []
	resolved_user = resolve_user_filter(user)
	if resolved_user:
		filters.append(["user", "=", resolved_user])
	if from_date:
		filters.append(["posting_date", ">=", getdate(from_date)])
	if to_date:
		filters.append(["posting_date", "<=", getdate(to_date)])
	if category:
		filters.append(["category", "=", category])
	if currency:
		filters.append(["currency", "=", currency])

	return frappe.get_all(
		"Expense Entry",
		filters=filters,
		fields=[
			"name",
			"posting_date",
			"user",
			"category",
			"amount",
			"currency",
			"exchange_rate_to_base",
			"base_currency",
			"amount_in_base_currency",
		],
		order_by="posting_date asc, creation asc",
	)


def get_total_in_currency(rows, target_currency=BASE_CURRENCY):
	validate_supported_currency(target_currency)
	total = 0
	for row in rows:
		total += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			target_currency,
			row.posting_date,
		)
	return flt(total)


@frappe.whitelist()
def get_expense_summary(user=None, from_date=None, to_date=None, currency=BASE_CURRENCY):
	validate_supported_currency(currency)
	rows = get_expense_rows(user=user, from_date=from_date, to_date=to_date)
	total = get_total_in_currency(rows, currency)

	by_category = defaultdict(float)
	by_currency = defaultdict(float)
	for row in rows:
		converted_amount = convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			currency,
			row.posting_date,
		)
		by_category[row.category] += converted_amount
		by_currency[row.currency] += flt(row.amount)

	return {
		"currency": currency,
		"total_expenses": total,
		"number_of_entries": len(rows),
		"by_category": dict(by_category),
		"by_currency": dict(by_currency),
	}


@frappe.whitelist()
def get_monthly_expense_chart(year=None, user=None):
	year = cint(year) or getdate(today()).year
	start_date = f"{year}-01-01"
	end_date = f"{year}-12-31"
	rows = get_expense_rows(user=user, from_date=start_date, to_date=end_date)

	values = [0.0] * 12
	for row in rows:
		month_index = getdate(row.posting_date).month - 1
		values[month_index] += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			BASE_CURRENCY,
			row.posting_date,
		)

	return {
		"data": {"labels": list(MONTHS), "datasets": [{"name": _("Expenses"), "values": values}]},
		"type": "line",
		"fieldtype": "Currency",
	}


@frappe.whitelist()
def get_category_expense_chart(from_date=None, to_date=None, user=None):
	rows = get_expense_rows(user=user, from_date=from_date, to_date=to_date)
	totals = defaultdict(float)
	for row in rows:
		totals[row.category] += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			BASE_CURRENCY,
			row.posting_date,
		)

	ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
	return {
		"data": {
			"labels": [row[0] for row in ordered],
			"datasets": [{"name": _("Expenses"), "values": [row[1] for row in ordered]}],
		},
		"type": "donut",
		"fieldtype": "Currency",
	}


@frappe.whitelist()
def get_monthly_budget_status(user=None, month=None, year=None, category=None, budget_name=None):
	user = resolve_user_filter(user)
	month = month or calendar.month_name[getdate(nowdate()).month]
	year = cint(year) or getdate(nowdate()).year

	if not category:
		return None

	if budget_name and frappe.db.exists("Monthly Budget", budget_name):
		budget = frappe.get_doc("Monthly Budget", budget_name)
		if not is_expense_manager() and budget.user != frappe.session.user:
			frappe.throw(_("You are not permitted to view this budget."))
	else:
		budget_name = frappe.db.get_value(
			"Monthly Budget",
			{"user": user, "month": month, "year": year, "category": category},
			"name",
		)
		if not budget_name:
			return None
		budget = frappe.get_doc("Monthly Budget", budget_name)

	from_date, to_date = get_month_date_range(budget.month, budget.year)
	rows = get_expense_rows(
		user=budget.user,
		from_date=from_date,
		to_date=to_date,
		category=budget.category,
	)
	spent = get_total_in_currency(rows, BASE_CURRENCY)
	budget_amount = flt(budget.budget_in_base_currency)
	remaining = budget_amount - spent
	usage_percent = (spent / budget_amount * 100) if budget_amount else 0

	return {
		"budget": budget_amount,
		"spent": spent,
		"remaining": remaining,
		"usage_percent": usage_percent,
		"currency": BASE_CURRENCY,
	}


@frappe.whitelist()
def get_this_month_expenses_card(filters=None):
	current = getdate(today())
	start = current.replace(day=1)
	end = current.replace(day=calendar.monthrange(current.year, current.month)[1])
	summary = get_expense_summary(from_date=start, to_date=end, currency=BASE_CURRENCY)
	return {"value": summary["total_expenses"], "fieldtype": "Currency", "options": BASE_CURRENCY}


@frappe.whitelist()
def get_today_expenses_card(filters=None):
	summary = get_expense_summary(from_date=today(), to_date=today(), currency=BASE_CURRENCY)
	return {"value": summary["total_expenses"], "fieldtype": "Currency", "options": BASE_CURRENCY}


@frappe.whitelist()
def get_top_category_card(filters=None):
	current = getdate(today())
	start = current.replace(day=1)
	end = current.replace(day=calendar.monthrange(current.year, current.month)[1])
	chart = get_category_expense_chart(from_date=start, to_date=end)
	labels = chart["data"]["labels"]
	values = chart["data"]["datasets"][0]["values"]
	if not labels:
		return _("No expenses")

	return "{0}: {1}".format(labels[0], fmt_money(values[0], currency=BASE_CURRENCY))


@frappe.whitelist()
def get_budget_usage_card(filters=None):
	current = getdate(today())
	month = calendar.month_name[current.month]
	budgets = frappe.get_all(
		"Monthly Budget",
		filters={"user": frappe.session.user, "month": month, "year": current.year},
		fields=["name", "budget_in_base_currency", "category"],
	)
	if not budgets:
		return {"value": 0, "fieldtype": "Percent"}

	total_budget = sum(flt(row.budget_in_base_currency) for row in budgets)
	from_date, to_date = get_month_date_range(month, current.year)
	rows = get_expense_rows(user=frappe.session.user, from_date=from_date, to_date=to_date)
	spent = get_total_in_currency(rows, BASE_CURRENCY)
	usage = (spent / total_budget * 100) if total_budget else 0
	return {"value": usage, "fieldtype": "Percent"}
