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
from personal_expense_tracker.budget_period import (
	get_budget_period_date_range,
	get_budget_period_for_date,
)

DEFAULT_EXCHANGE_RATE_API_URL = "https://open.er-api.com/v6/latest/{base_currency}"
DEFAULT_EXCHANGE_RATE_API_SOURCE = "open.er-api.com"
SP_TODAY_RATE_SOURCE = "sp-today.com"
SP_TODAY_CURRENCY_PAGES = {
	"USD": "https://sp-today.com/en/currency/us-dollar",
	"EUR": "https://sp-today.com/en/currency/euro",
}
SP_TODAY_HISTORICAL_URL = "https://sp-today.com/api/historical"
SP_TODAY_HISTORICAL_CITY = "damascus"
SP_TODAY_RATE_TYPES = ("buy", "sell", "mid")
BUDGET_WARNING_PERCENT = 75
BUDGET_DANGER_PERCENT = 90


@frappe.whitelist()
def get_latest_exchange_rate(from_currency, to_currency, posting_date=None):
	return get_latest_rate_record(from_currency, to_currency, posting_date)


@frappe.whitelist()
def get_exchange_rate_for_date(from_currency, to_currency, posting_date=None):
	validate_supported_currency(from_currency, _("From Currency"))
	validate_supported_currency(to_currency, _("To Currency"))
	posting_date = getdate(posting_date or today())

	if from_currency == to_currency:
		return frappe._dict(
			{
				"exchange_rate": 1,
				"from_currency": from_currency,
				"to_currency": to_currency,
				"effective_date": posting_date,
				"name": None,
			}
		)

	rate = frappe.db.get_all(
		"Currency Exchange Rate",
		filters={
			"from_currency": from_currency,
			"to_currency": to_currency,
			"effective_date": posting_date,
			"is_active": 1,
		},
		fields=["name", "from_currency", "to_currency", "exchange_rate", "effective_date"],
		order_by="modified desc",
		limit=1,
	)
	if rate:
		return frappe._dict(rate[0])

	inverse_rate = frappe.db.get_all(
		"Currency Exchange Rate",
		filters={
			"from_currency": to_currency,
			"to_currency": from_currency,
			"effective_date": posting_date,
			"is_active": 1,
		},
		fields=["name", "from_currency", "to_currency", "exchange_rate", "effective_date"],
		order_by="modified desc",
		limit=1,
	)
	if inverse_rate and flt(inverse_rate[0].exchange_rate):
		return frappe._dict(
			{
				"name": inverse_rate[0].name,
				"from_currency": from_currency,
				"to_currency": to_currency,
				"exchange_rate": 1 / flt(inverse_rate[0].exchange_rate),
				"effective_date": inverse_rate[0].effective_date,
			}
		)

	return None


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


def get_sp_today_historical_range(effective_date):
	days_old = (getdate(today()) - getdate(effective_date)).days
	if days_old <= 7:
		return "1w"
	if days_old <= 31:
		return "1m"
	if days_old <= 93:
		return "3m"
	if days_old <= 186:
		return "6m"
	if days_old <= 366:
		return "1y"
	return "all"


def get_sp_today_row_date(row):
	date_value = row.get("date")
	if not date_value:
		return None

	return getdate(str(date_value).split("T", 1)[0])


def fetch_sp_today_historical_rows(currency, date_range):
	try:
		response = requests.get(
			SP_TODAY_HISTORICAL_URL,
			params={
				"code": currency,
				"city": SP_TODAY_HISTORICAL_CITY,
				"range": date_range,
			},
			timeout=20,
			headers={"User-Agent": "PersonalExpenseTracker/0.0.1"},
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.throw(
			_("Could not fetch {0}/SYP historical rates from SP Today: {1}").format(
				currency, str(exc)
			)
		)

	try:
		rows = response.json()
	except ValueError:
		frappe.throw(_("SP Today historical endpoint returned an invalid JSON response."))

	if not isinstance(rows, list):
		frappe.throw(_("SP Today historical endpoint returned an unexpected response."))

	return rows


def fetch_sp_today_historical_currency_rate(currency, effective_date):
	effective_date = getdate(effective_date)
	date_range = get_sp_today_historical_range(effective_date)
	rows = fetch_sp_today_historical_rows(currency, date_range)

	if date_range != "all" and not any(get_sp_today_row_date(row) == effective_date for row in rows):
		# Retry all data when a shorter chart range does not contain the requested date.
		date_range = "all"
		rows = fetch_sp_today_historical_rows(currency, date_range)

	for row in rows:
		if get_sp_today_row_date(row) != effective_date:
			continue

		rates = frappe._dict(
			{
				"buy": flt(row.get("buy")),
				"sell": flt(row.get("sell")),
				"recorded_at": row.get("date"),
				"source_url": get_sp_today_historical_url(currency, date_range),
			}
		)
		if rates.buy <= 0 or rates.sell <= 0:
			frappe.throw(_("SP Today returned an invalid historical {0}/SYP rate.").format(currency))
		return rates

	frappe.throw(
		_("SP Today does not have a historical {0}/SYP rate for {1}.").format(
			currency, effective_date
		)
	)


def get_sp_today_historical_url(currency, date_range):
	return (
		f"{SP_TODAY_HISTORICAL_URL}?code={currency}&city={SP_TODAY_HISTORICAL_CITY}"
		f"&range={date_range}"
	)


def select_sp_today_rate(rates, rate_type):
	if rate_type == "mid":
		return flt((rates.buy + rates.sell) / 2, 9)

	return flt(rates.get(rate_type), 9)


def fetch_live_exchange_rates_from_sp_today(rate_type=None):
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
			"source_mode": "live",
			"rate_type": rate_type,
			"provider_rates": {
				"USD": {"buy": usd_rates.buy, "sell": usd_rates.sell},
				"EUR": {"buy": eur_rates.buy, "sell": eur_rates.sell},
			},
		}
	)


def fetch_historical_exchange_rates_from_sp_today(effective_date, rate_type=None):
	rate_type = get_sp_today_rate_type(rate_type)
	effective_date = getdate(effective_date)
	usd_rates = fetch_sp_today_historical_currency_rate("USD", effective_date)
	eur_rates = fetch_sp_today_historical_currency_rate("EUR", effective_date)

	usd_to_syp = select_sp_today_rate(usd_rates, rate_type)
	eur_to_syp = select_sp_today_rate(eur_rates, rate_type)
	if usd_to_syp <= 0 or eur_to_syp <= 0:
		frappe.throw(_("SP Today returned an invalid historical exchange rate."))

	return frappe._dict(
		{
			"rates": {
				"SYP": 1,
				"USD": 1 / usd_to_syp,
				"EUR": 1 / eur_to_syp,
			},
			"source": SP_TODAY_RATE_SOURCE,
			"source_url": ", ".join([usd_rates.source_url, eur_rates.source_url]),
			"provider_timestamp": ", ".join([usd_rates.recorded_at, eur_rates.recorded_at]),
			"source_mode": "historical",
			"rate_type": rate_type,
			"provider_rates": {
				"USD": {"buy": usd_rates.buy, "sell": usd_rates.sell},
				"EUR": {"buy": eur_rates.buy, "sell": eur_rates.sell},
			},
		}
	)


def fetch_exchange_rates_from_sp_today(rate_type=None, effective_date=None):
	effective_date = getdate(effective_date or today())
	if effective_date > getdate(today()):
		frappe.throw(_("SP Today rates cannot be synced for a future date: {0}.").format(effective_date))

	if effective_date == getdate(today()):
		return fetch_live_exchange_rates_from_sp_today(rate_type=rate_type)

	return fetch_historical_exchange_rates_from_sp_today(
		effective_date=effective_date,
		rate_type=rate_type,
	)


@frappe.whitelist()
def get_sp_today_exchange_rate_for_pair(from_currency, to_currency, effective_date=None, rate_type=None):
	ensure_can_sync_exchange_rates()
	validate_supported_currency(from_currency, _("From Currency"))
	validate_supported_currency(to_currency, _("To Currency"))
	effective_date = getdate(effective_date or today())

	if from_currency == to_currency:
		return {
			"from_currency": from_currency,
			"to_currency": to_currency,
			"exchange_rate": 1,
			"effective_date": effective_date,
			"source": SP_TODAY_RATE_SOURCE,
			"notes": _("Same-currency exchange rate set to 1."),
		}

	api_result = fetch_exchange_rates_from_sp_today(
		rate_type=rate_type,
		effective_date=effective_date,
	)
	from_rate = flt(api_result.rates[from_currency])
	to_rate = flt(api_result.rates[to_currency])
	if from_rate <= 0 or to_rate <= 0:
		frappe.throw(_("Invalid SP Today rate received for {0} or {1}.").format(from_currency, to_currency))

	exchange_rate = flt(to_rate / from_rate, 9)
	notes = get_sp_today_sync_notes(api_result, effective_date)
	return {
		"from_currency": from_currency,
		"to_currency": to_currency,
		"exchange_rate": exchange_rate,
		"effective_date": effective_date,
		"source": api_result.source,
		"source_url": api_result.source_url,
		"provider_timestamp": api_result.provider_timestamp,
		"source_mode": api_result.source_mode,
		"rate_type": api_result.rate_type,
		"provider_rates": api_result.provider_rates,
		"notes": notes,
	}


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


def get_sp_today_sync_notes(api_result, effective_date):
	if api_result.source_mode == "historical":
		return _(
			"Fetched from SP Today public historical endpoint on {0} and saved for effective date {1}. Rate type: {2}. "
			"USD buy/sell: {3}/{4}. EUR buy/sell: {5}/{6}."
		).format(
			nowdate(),
			effective_date,
			api_result.rate_type,
			api_result.provider_rates["USD"]["buy"],
			api_result.provider_rates["USD"]["sell"],
			api_result.provider_rates["EUR"]["buy"],
			api_result.provider_rates["EUR"]["sell"],
		)

	return _(
		"Fetched from SP Today public currency pages on {0} and saved for effective date {1}. Rate type: {2}. "
		"USD buy/sell: {3}/{4}. EUR buy/sell: {5}/{6}."
	).format(
		nowdate(),
		effective_date,
		api_result.rate_type,
		api_result.provider_rates["USD"]["buy"],
		api_result.provider_rates["USD"]["sell"],
		api_result.provider_rates["EUR"]["buy"],
		api_result.provider_rates["EUR"]["sell"],
	)


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
	api_result = fetch_exchange_rates_from_sp_today(
		rate_type=rate_type,
		effective_date=effective_date,
	)
	notes = get_sp_today_sync_notes(api_result, effective_date)
	updated_rates = save_exchange_rate_result(api_result, effective_date, notes)

	return {
		"effective_date": effective_date,
		"source": api_result.source,
		"source_url": api_result.source_url,
		"source_mode": api_result.source_mode,
		"provider_timestamp": api_result.provider_timestamp,
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


def get_income_rows(user=None, from_date=None, to_date=None, income_source=None, currency=None):
	filters = []
	resolved_user = resolve_user_filter(user)
	if resolved_user:
		filters.append(["user", "=", resolved_user])
	if from_date:
		filters.append(["posting_date", ">=", getdate(from_date)])
	if to_date:
		filters.append(["posting_date", "<=", getdate(to_date)])
	if income_source:
		filters.append(["income_source", "=", income_source])
	if currency:
		filters.append(["currency", "=", currency])

	return frappe.get_all(
		"Income Entry",
		filters=filters,
		fields=[
			"name",
			"posting_date",
			"user",
			"income_source",
			"description",
			"amount",
			"currency",
			"exchange_rate_to_base",
			"base_currency",
			"income_in_base_currency",
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


def get_total_income_in_currency(rows, target_currency=BASE_CURRENCY):
	validate_supported_currency(target_currency)
	total = 0
	for row in rows:
		total += convert_amount(
			row.income_in_base_currency,
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
def get_income_summary(user=None, from_date=None, to_date=None, currency=BASE_CURRENCY):
	validate_supported_currency(currency)
	rows = get_income_rows(user=user, from_date=from_date, to_date=to_date)
	total = get_total_income_in_currency(rows, currency)

	by_source = defaultdict(float)
	by_currency = defaultdict(float)
	for row in rows:
		converted_amount = convert_amount(
			row.income_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			currency,
			row.posting_date,
		)
		by_source[row.income_source] += converted_amount
		by_currency[row.currency] += flt(row.amount)

	return {
		"currency": currency,
		"total_income": total,
		"number_of_entries": len(rows),
		"by_source": dict(by_source),
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
			"labels": [_(row[0]) for row in ordered],
			"datasets": [{"name": _("Expenses"), "values": [row[1] for row in ordered]}],
		},
		"type": "donut",
	}


@frappe.whitelist()
def get_monthly_budget_status(
	user=None, month=None, year=None, category=None, budget_name=None, budget_period=None
):
	if not category:
		return None

	if budget_name and frappe.db.exists("Monthly Budget", budget_name):
		budget = frappe.get_doc("Monthly Budget", budget_name)
		if not is_expense_manager() and budget.user != frappe.session.user:
			frappe.throw(_("You are not permitted to view this budget."))

		return get_category_budget_status(
			user=budget.user,
			category=budget.category,
			budget_period=budget.budget_period,
			budget_name=budget.name,
		)

	user = resolve_budget_user(user)
	if not user:
		user = frappe.session.user

	period = None
	if budget_period:
		period = get_budget_period_context(budget_period=budget_period)
	else:
		period = get_budget_period_for_date(create_if_missing=True)

	if not period:
		return None

	budget_name = frappe.db.get_value(
		"Monthly Budget",
		{"user": user, "budget_period": period.name, "category": category},
		"name",
	)
	if not budget_name:
		month = month or period.month
		year = cint(year) or period.year
		budget_name = frappe.db.get_value(
			"Monthly Budget",
			{"user": user, "month": month, "year": year, "category": category},
			"name",
		)
	if not budget_name:
		return get_category_budget_status(user=user, category=category, budget_period=period.name)

	return get_category_budget_status(
		user=user,
		category=category,
		budget_period=period.name,
		budget_name=budget_name,
	)


def resolve_budget_user(user=None, allow_all_users=False):
	if is_expense_manager():
		return user or (None if allow_all_users else frappe.session.user)

	return frappe.session.user


def get_budget_period_context(budget_period=None, posting_date=None, create_if_missing=True):
	if budget_period:
		period = frappe.db.get_value(
			"Budget Period",
			budget_period,
			["name", "period_name", "from_date", "to_date", "month", "year", "status"],
			as_dict=True,
		)
		if not period:
			frappe.throw(_("Budget Period {0} does not exist.").format(budget_period))
		return frappe._dict(period)

	period = get_budget_period_for_date(
		period_date=posting_date,
		create_if_missing=create_if_missing,
	)
	return frappe._dict(period) if period else None


def get_category_default_budget(category):
	if not category:
		return 0

	return flt(frappe.db.get_value("Expense Category", category, "monthly_budget"))


def get_budget_status_code(budget_amount, spent):
	budget_amount = flt(budget_amount)
	spent = flt(spent)
	if budget_amount <= 0:
		return "no_budget"

	usage_percent = flt(spent / budget_amount * 100, 2)
	if spent > budget_amount:
		return "exceeded"
	if usage_percent >= BUDGET_DANGER_PERCENT:
		return "danger"
	if usage_percent >= BUDGET_WARNING_PERCENT:
		return "warning"
	return "safe"


def get_budget_status_label(status):
	labels = {
		"safe": _("Safe"),
		"warning": _("Watch"),
		"danger": _("Near Limit"),
		"exceeded": _("Exceeded"),
		"no_budget": _("No Budget"),
	}
	return labels.get(status, status)


def get_budget_source_label(source):
	labels = {
		"monthly_budget": _("Monthly Budget"),
		"default_category_budget": _("Default category budget"),
		"none": _("No active budget"),
	}
	return labels.get(source, source)


def get_category_period_spend(user, category, from_date, to_date, exclude_expense_entry=None):
	filters = {
		"category": category,
		"posting_date": ["between", [from_date, to_date]],
	}
	if user:
		filters["user"] = user

	if exclude_expense_entry:
		filters["name"] = ["!=", exclude_expense_entry]

	rows = frappe.get_all(
		"Expense Entry",
		filters=filters,
		fields=["posting_date", "amount_in_base_currency", "base_currency"],
	)
	total = 0
	for row in rows:
		total += convert_amount(
			row.amount_in_base_currency,
			row.base_currency or BASE_CURRENCY,
			BASE_CURRENCY,
			row.posting_date,
		)
	return flt(total, 2)


def get_current_expense_contribution(current_expense, user, category, from_date, to_date):
	if not current_expense:
		return 0
	if current_expense.user != user or current_expense.category != category:
		return 0
	if not current_expense.posting_date:
		return 0

	posting_date = getdate(current_expense.posting_date)
	if not (getdate(from_date) <= posting_date <= getdate(to_date)):
		return 0

	return flt(
		convert_amount(
			current_expense.amount_in_base_currency,
			current_expense.base_currency or BASE_CURRENCY,
			BASE_CURRENCY,
			posting_date,
		),
		2,
	)


def get_category_budget_message(status):
	if status.status == "no_budget":
		if status.default_budget:
			return _(
				"No active budget exists for {0} in {1}. Default category budget: {2}."
			).format(status.category, status.period_label, status.default_budget_display)
		return _("No active budget exists for {0} in {1}.").format(
			status.category, status.period_label
		)

	if status.status == "exceeded":
		return _(
			"Warning: You exceeded the budget for this category by {0}. You used {1}% of the allocated budget."
		).format(status.overrun_display, status.usage_percent)

	return _("You have {0} remaining for this category budget. {1}% used.").format(
		status.remaining_display,
		status.usage_percent,
	)


def get_category_budget_insight(status):
	if status.status == "no_budget":
		if status.spent:
			return _("This category has spending in the period but no active Monthly Budget.")
		return _("Create a Monthly Budget when you want this category tracked actively.")
	if status.status == "exceeded":
		return _("Reduce future spending or increase this category budget for the period.")
	if status.status == "danger":
		return _("This category is close to its allocated budget.")
	if status.status == "warning":
		return _("Spending is healthy, but this category deserves attention.")
	return _("This category is inside its planned budget.")


@frappe.whitelist()
def get_category_budget_status(
	user=None,
	category=None,
	posting_date=None,
	budget_period=None,
	budget_name=None,
	current_expense=None,
):
	if not category and not budget_name:
		return None

	budget = None
	if budget_name and frappe.db.exists("Monthly Budget", budget_name):
		budget = frappe.db.get_value(
			"Monthly Budget",
			budget_name,
			[
				"name",
				"user",
				"category",
				"budget_period",
				"budget_amount",
				"currency",
				"budget_in_base_currency",
			],
			as_dict=True,
		)
		user = budget.user
		category = budget.category
		budget_period = budget.budget_period

	user = resolve_budget_user(user)
	if not user:
		user = frappe.session.user

	period = get_budget_period_context(
		budget_period=budget_period,
		posting_date=posting_date,
		create_if_missing=True,
	)
	if not period:
		return None

	if not budget:
		budget = frappe.db.get_value(
			"Monthly Budget",
			{"user": user, "budget_period": period.name, "category": category},
			[
				"name",
				"user",
				"category",
				"budget_period",
				"budget_amount",
				"currency",
				"budget_in_base_currency",
			],
			as_dict=True,
		)

	exclude_name = None
	if current_expense and getattr(current_expense, "name", None) and not current_expense.is_new():
		exclude_name = current_expense.name

	spent = get_category_period_spend(user, category, period.from_date, period.to_date, exclude_name)
	spent += get_current_expense_contribution(
		current_expense,
		user,
		category,
		period.from_date,
		period.to_date,
	)
	spent = flt(spent, 2)
	total_expenses = get_total_in_currency(
		get_expense_rows(user=user, from_date=period.from_date, to_date=period.to_date),
		BASE_CURRENCY,
	)
	total_income = get_total_income_in_currency(
		get_income_rows(user=user, from_date=period.from_date, to_date=period.to_date),
		BASE_CURRENCY,
	)
	income_remaining = flt(total_income - total_expenses, 2)
	income_usage_percent = flt(total_expenses / total_income * 100, 2) if total_income else 0

	default_budget = get_category_default_budget(category)
	budget_amount = flt(budget.budget_in_base_currency) if budget else 0
	usage_percent = flt(spent / budget_amount * 100, 2) if budget_amount else 0
	remaining = flt(budget_amount - spent, 2) if budget_amount else 0
	overrun = flt(max(spent - budget_amount, 0), 2) if budget_amount else 0
	status_code = get_budget_status_code(budget_amount, spent)
	budget_source = "monthly_budget" if budget else ("default_category_budget" if default_budget else "none")

	status = frappe._dict(
		{
			"status": status_code,
			"status_label": get_budget_status_label(status_code),
			"category": category,
			"category_label": _(category or ""),
			"period": period.name,
			"period_label": period.get("period_name") or period.name,
			"from_date": period.from_date,
			"to_date": period.to_date,
			"user": user,
			"budget_name": budget.name if budget else None,
			"budget_source": budget_source,
			"budget_source_label": get_budget_source_label(budget_source),
			"budget": budget_amount,
			"budget_display": fmt_money(budget_amount, currency=BASE_CURRENCY),
			"default_budget": default_budget,
			"default_budget_display": fmt_money(default_budget, currency=BASE_CURRENCY),
			"spent": spent,
			"spent_display": fmt_money(spent, currency=BASE_CURRENCY),
			"remaining": remaining,
			"remaining_display": fmt_money(remaining, currency=BASE_CURRENCY),
			"overrun": overrun,
			"overrun_display": fmt_money(overrun, currency=BASE_CURRENCY),
			"usage_percent": usage_percent,
			"usage_width": min(usage_percent, 100),
			"total_income": total_income,
			"total_expenses": total_expenses,
			"income_remaining": income_remaining,
			"income_remaining_display": fmt_money(income_remaining, currency=BASE_CURRENCY),
			"income_usage_percent": income_usage_percent,
			"currency": BASE_CURRENCY,
		}
	)
	status["message"] = get_category_budget_message(status)
	status["insight"] = get_category_budget_insight(status)
	return status


@frappe.whitelist()
def get_category_budget_dashboard(budget_period=None, user=None):
	resolved_user = resolve_budget_user(user, allow_all_users=True)
	period = get_budget_period_context(budget_period=budget_period, create_if_missing=True)
	if not period:
		return {}

	budget_filters = {"budget_period": period.name}
	if resolved_user:
		budget_filters["user"] = resolved_user

	budget_rows = frappe.get_all(
		"Monthly Budget",
		filters=budget_filters,
		fields=["name", "user", "category", "budget_in_base_currency", "budget_amount", "currency"],
		order_by="category asc",
	)

	budget_map = defaultdict(lambda: {"amount": 0.0, "count": 0, "names": []})
	for row in budget_rows:
		budget_map[row.category]["amount"] += flt(row.budget_in_base_currency)
		budget_map[row.category]["count"] += 1
		budget_map[row.category]["names"].append(row.name)

	expense_rows = get_expense_rows(
		user=resolved_user,
		from_date=period.from_date,
		to_date=period.to_date,
	)
	income_rows = get_income_rows(
		user=resolved_user,
		from_date=period.from_date,
		to_date=period.to_date,
	)
	total_expenses = get_total_in_currency(expense_rows, BASE_CURRENCY)
	total_income = get_total_income_in_currency(income_rows, BASE_CURRENCY)
	income_remaining = flt(total_income - total_expenses, 2)
	income_usage_percent = flt(total_expenses / total_income * 100, 2) if total_income else 0
	expense_map = defaultdict(lambda: {"spent": 0.0, "count": 0, "last_date": None})
	for row in expense_rows:
		category = row.get("category")
		amount = convert_amount(
			row.get("amount_in_base_currency"),
			row.get("base_currency") or BASE_CURRENCY,
			BASE_CURRENCY,
			row.get("posting_date"),
		)
		expense_map[category]["spent"] += flt(amount)
		expense_map[category]["count"] += 1
		posting_date = getdate(row.get("posting_date"))
		if not expense_map[category]["last_date"] or posting_date > expense_map[category]["last_date"]:
			expense_map[category]["last_date"] = posting_date

	active_categories = frappe.get_all(
		"Expense Category",
		filters={"is_active": 1},
		fields=["name", "category_name", "monthly_budget"],
		order_by="category_name asc",
	)
	category_defaults = {row.name: flt(row.monthly_budget) for row in active_categories}
	categories = set(category_defaults) | set(budget_map) | set(expense_map)

	category_rows = []
	total_allocated = 0
	total_spent_budgeted = 0
	total_unbudgeted = 0
	for category in sorted(categories, key=lambda value: _(value or "")):
		budget_amount = flt(budget_map[category]["amount"], 2)
		spent = flt(expense_map[category]["spent"], 2)
		count = cint(expense_map[category]["count"])
		usage_percent = flt(spent / budget_amount * 100, 2) if budget_amount else 0
		remaining = flt(budget_amount - spent, 2) if budget_amount else 0
		overrun = flt(max(spent - budget_amount, 0), 2) if budget_amount else 0
		status_code = get_budget_status_code(budget_amount, spent)
		average_expense = flt(spent / count, 2) if count else 0
		default_budget = flt(category_defaults.get(category))
		budget_source = "monthly_budget" if budget_amount else (
			"default_category_budget" if default_budget else "none"
		)

		if budget_amount:
			total_allocated += budget_amount
			total_spent_budgeted += spent
		else:
			total_unbudgeted += spent

		status = frappe._dict(
			{
				"status": status_code,
				"spent": spent,
				"budget": budget_amount,
				"default_budget": default_budget,
			}
		)
		category_rows.append(
			{
				"category": category,
				"category_label": _(category or ""),
				"period": period.name,
				"period_label": period.get("period_name") or period.name,
				"budget_source": budget_source,
				"budget_source_label": get_budget_source_label(budget_source),
				"budget_count": budget_map[category]["count"],
				"budget": budget_amount,
				"budget_display": fmt_money(budget_amount, currency=BASE_CURRENCY),
				"default_budget": default_budget,
				"default_budget_display": fmt_money(default_budget, currency=BASE_CURRENCY),
				"spent": spent,
				"spent_display": fmt_money(spent, currency=BASE_CURRENCY),
				"remaining": remaining,
				"remaining_display": fmt_money(remaining, currency=BASE_CURRENCY),
				"overrun": overrun,
				"overrun_display": fmt_money(overrun, currency=BASE_CURRENCY),
				"usage_percent": usage_percent,
				"usage_width": min(usage_percent, 100),
				"status": status_code,
				"status_label": get_budget_status_label(status_code),
				"last_expense_date": expense_map[category]["last_date"],
				"expense_count": count,
				"average_expense": average_expense,
				"average_expense_display": fmt_money(average_expense, currency=BASE_CURRENCY),
				"insight": get_category_budget_insight(status),
			}
		)

	total_remaining = flt(total_allocated - total_spent_budgeted, 2)
	budget_usage_percent = flt(total_spent_budgeted / total_allocated * 100, 2) if total_allocated else 0
	highest_usage = max(
		(row for row in category_rows if row["budget"]),
		key=lambda row: row["usage_percent"],
		default=None,
	)

	available_periods = frappe.get_all(
		"Budget Period",
		fields=["name", "period_name", "from_date", "to_date", "status"],
		order_by="from_date desc",
		limit=36,
	)

	return {
		"period": {
			"name": period.name,
			"label": period.get("period_name") or period.name,
			"from_date": period.from_date,
			"to_date": period.to_date,
		},
		"currency": BASE_CURRENCY,
		"user": resolved_user,
		"summary": {
			"total_income": flt(total_income, 2),
			"total_income_display": fmt_money(total_income, currency=BASE_CURRENCY),
			"total_expenses": flt(total_expenses, 2),
			"total_expenses_display": fmt_money(total_expenses, currency=BASE_CURRENCY),
			"income_remaining": income_remaining,
			"income_remaining_display": fmt_money(income_remaining, currency=BASE_CURRENCY),
			"income_usage_percent": income_usage_percent,
			"total_allocated": flt(total_allocated, 2),
			"total_allocated_display": fmt_money(total_allocated, currency=BASE_CURRENCY),
			"total_spent": flt(total_spent_budgeted, 2),
			"total_spent_display": fmt_money(total_spent_budgeted, currency=BASE_CURRENCY),
			"total_remaining": total_remaining,
			"total_remaining_display": fmt_money(total_remaining, currency=BASE_CURRENCY),
			"total_unbudgeted": flt(total_unbudgeted, 2),
			"total_unbudgeted_display": fmt_money(total_unbudgeted, currency=BASE_CURRENCY),
			"budget_usage_percent": budget_usage_percent,
			"exceeded_count": len([row for row in category_rows if row["status"] == "exceeded"]),
			"near_limit_count": len(
				[row for row in category_rows if row["status"] in {"warning", "danger"}]
			),
			"no_budget_count": len([row for row in category_rows if row["status"] == "no_budget"]),
			"highest_usage_category": highest_usage,
		},
		"categories": category_rows,
		"available_periods": [
			{
				"name": row.name,
				"label": row.period_name or row.name,
				"from_date": row.from_date,
				"to_date": row.to_date,
				"status": row.status,
			}
			for row in available_periods
		],
		"status_options": [
			{"value": "", "label": _("All Statuses")},
			{"value": "safe", "label": get_budget_status_label("safe")},
			{"value": "warning", "label": get_budget_status_label("warning")},
			{"value": "danger", "label": get_budget_status_label("danger")},
			{"value": "exceeded", "label": get_budget_status_label("exceeded")},
			{"value": "no_budget", "label": get_budget_status_label("no_budget")},
		],
	}


@frappe.whitelist()
def get_current_budget_period(posting_date=None):
	return get_budget_period_for_date(period_date=posting_date, create_if_missing=True)


def get_current_card_period(user=None):
	period = get_budget_period_for_date(create_if_missing=True)
	return getdate(period.from_date), getdate(period.to_date)


@frappe.whitelist()
def get_this_month_expenses_card(filters=None):
	user = None if is_expense_manager() else frappe.session.user
	start, end = get_current_card_period(user)
	summary = get_expense_summary(from_date=start, to_date=end, currency=BASE_CURRENCY)
	return {"value": summary["total_expenses"], "fieldtype": "Currency", "options": BASE_CURRENCY}


@frappe.whitelist()
def get_today_expenses_card(filters=None):
	summary = get_expense_summary(from_date=today(), to_date=today(), currency=BASE_CURRENCY)
	return {"value": summary["total_expenses"], "fieldtype": "Currency", "options": BASE_CURRENCY}


@frappe.whitelist()
def get_top_category_card(filters=None):
	user = None if is_expense_manager() else frappe.session.user
	start, end = get_current_card_period(user)
	chart = get_category_expense_chart(from_date=start, to_date=end, user=user)
	labels = chart["data"]["labels"]
	values = chart["data"]["datasets"][0]["values"]
	if not labels:
		return _("No expenses")

	return "{0}: {1}".format(_(labels[0]), fmt_money(values[0], currency=BASE_CURRENCY))


@frappe.whitelist()
def get_budget_usage_card(filters=None):
	user = None if is_expense_manager() else frappe.session.user
	dashboard = get_category_budget_dashboard(user=user)
	usage = dashboard.get("summary", {}).get("budget_usage_percent", 0)
	return {"value": flt(usage, 3), "fieldtype": "Percent"}


@frappe.whitelist()
def get_income_used_card(filters=None):
	user = None if is_expense_manager() else frappe.session.user
	dashboard = get_category_budget_dashboard(user=user)
	usage = dashboard.get("summary", {}).get("income_usage_percent", 0)
	return {"value": flt(usage, 3), "fieldtype": "Percent"}


@frappe.whitelist()
def get_remaining_budget_card(filters=None):
	user = None if is_expense_manager() else frappe.session.user
	dashboard = get_category_budget_dashboard(user=user)
	remaining = dashboard.get("summary", {}).get("total_remaining", 0)
	return {
		"value": flt(remaining, 2),
		"fieldtype": "Currency",
		"options": BASE_CURRENCY,
	}


@frappe.whitelist()
def get_income_left_card(filters=None):
	user = None if is_expense_manager() else frappe.session.user
	dashboard = get_category_budget_dashboard(user=user)
	remaining = dashboard.get("summary", {}).get("income_remaining", 0)
	return {
		"value": flt(remaining, 2),
		"fieldtype": "Currency",
		"options": BASE_CURRENCY,
	}
