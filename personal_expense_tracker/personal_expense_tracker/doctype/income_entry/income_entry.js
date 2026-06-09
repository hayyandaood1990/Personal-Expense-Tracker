frappe.ui.form.on("Income Entry", {
	refresh(frm) {
		frm.trigger("setup_exchange_rate_buttons");
		frm.trigger("show_income_indicator");
	},

	amount(frm) {
		frm.trigger("calculate_income_in_base");
	},

	currency(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	base_currency(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	posting_date(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	exchange_rate_to_base(frm) {
		frm.trigger("calculate_income_in_base");
	},

	setup_exchange_rate_buttons(frm) {
		setup_exchange_rate_buttons(frm);
	},

	fetch_exchange_rate(frm) {
		if (!frm.doc.currency || !frm.doc.base_currency) {
			frm.trigger("setup_exchange_rate_buttons");
			return;
		}

		if (frm.doc.currency === frm.doc.base_currency) {
			frm.set_value("exchange_rate_to_base", 1).then(() => {
				frm.trigger("calculate_income_in_base");
				frm.trigger("setup_exchange_rate_buttons");
			});
			return;
		}

		frappe.call({
			method: "personal_expense_tracker.api.get_exchange_rate_for_date",
			args: {
				from_currency: frm.doc.currency,
				to_currency: frm.doc.base_currency,
				posting_date: frm.doc.posting_date || frappe.datetime.nowdate(),
			},
			callback(r) {
				if (r.message && r.message.exchange_rate) {
					frm.set_value("exchange_rate_to_base", r.message.exchange_rate).then(() => {
						frm.trigger("calculate_income_in_base");
						frappe.show_alert({
							message: __("Exchange rate fetched from {0}", [r.message.effective_date]),
							indicator: "green",
						});
					});
				} else {
					show_missing_exchange_rate_info(
						frm,
						frm.doc.currency,
						frm.doc.base_currency,
						frm.doc.posting_date
					);
				}
				frm.trigger("setup_exchange_rate_buttons");
			},
		});
	},

	calculate_income_in_base(frm) {
		const amount = flt(frm.doc.amount);
		const rate = flt(frm.doc.exchange_rate_to_base);
		frm.set_value("income_in_base_currency", amount * rate);
		frm.trigger("show_income_indicator");
	},

	show_income_indicator(frm) {
		if (!frm.doc.income_in_base_currency) return;

		const currency = frm.doc.base_currency || "SYP";
		const formatted_amount = format_currency(frm.doc.income_in_base_currency, currency);
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(
			__("Income in {0}: {1}", [currency, formatted_amount]),
			"green"
		);
	},
});

function can_sync_live_rates() {
	return frappe.user.has_role("Expense Manager") || frappe.user.has_role("System Manager");
}

function setup_exchange_rate_buttons(frm) {
	frm.remove_custom_button(__("Fetch Exchange Rate"), __("Exchange Rate"));
	frm.remove_custom_button(__("Sync SP Today Rates"), __("Exchange Rate"));

	const { currency, base_currency, posting_date } = frm.doc;
	if (!currency || !base_currency) {
		return;
	}

	if (currency === base_currency) {
		add_fetch_exchange_rate_button(frm);
		return;
	}

	const button_key = [currency, base_currency, posting_date || frappe.datetime.nowdate()].join("|");
	frm._pet_exchange_rate_button_key = button_key;
	frappe.call({
		method: "personal_expense_tracker.api.get_exchange_rate_for_date",
		args: {
			from_currency: currency,
			to_currency: base_currency,
			posting_date: posting_date || frappe.datetime.nowdate(),
		},
		callback(r) {
			if (frm._pet_exchange_rate_button_key !== button_key) {
				return;
			}

			if (r.message && r.message.exchange_rate) {
				add_fetch_exchange_rate_button(frm);
			} else if (can_sync_live_rates()) {
				add_sync_sp_today_button(frm);
			}
		},
	});
}

function add_fetch_exchange_rate_button(frm) {
	frm.remove_custom_button(__("Fetch Exchange Rate"), __("Exchange Rate"));
	frm.add_custom_button(__("Fetch Exchange Rate"), () => {
		frm.trigger("fetch_exchange_rate");
	}, __("Exchange Rate"));
}

function add_sync_sp_today_button(frm) {
	frm.remove_custom_button(__("Sync SP Today Rates"), __("Exchange Rate"));
	frm.add_custom_button(__("Sync SP Today Rates"), () => {
		sync_sp_today_exchange_rates(frm);
	}, __("Exchange Rate"));
}

function show_missing_exchange_rate_info(frm, currency, base_currency, posting_date) {
	const rate_date = posting_date || frappe.datetime.nowdate();
	const message = get_missing_exchange_rate_message(rate_date);
	frappe.show_alert({
		message: message(currency, base_currency, rate_date),
		indicator: "blue",
	});
}

function get_missing_exchange_rate_message(rate_date) {
	if (can_sync_live_rates()) {
		return (currency, base_currency, date) =>
			__("No exchange rate found for {0} to {1} on {2}. Click Sync SP Today Rates to save rates for this date.", [
				currency,
				base_currency,
				date,
			]);
	}

	return (currency, base_currency, date) =>
		__("No exchange rate found for {0} to {1} on {2}. Ask an Expense Manager to sync SP Today rates for this date.", [
			currency,
			base_currency,
			date,
		]);
}

function sync_sp_today_exchange_rates(frm) {
	if (!frm.doc.posting_date) {
		frappe.msgprint({
			title: __("Missing Date"),
			message: __("Please select Posting Date before syncing SP Today rates."),
			indicator: "blue",
		});
		return;
	}

	frappe.call({
		method: "personal_expense_tracker.api.sync_exchange_rates_from_sp_today",
		args: {
			effective_date: frm.doc.posting_date,
			rate_type: "sell",
		},
		freeze: true,
		freeze_message: __("Syncing SP Today exchange rates..."),
		callback(r) {
			const updated_rates = (r.message && r.message.updated_rates) || [];
			frappe.show_alert({
				message: __("{0} SP Today exchange rates synced for {1}.", [
					updated_rates.length,
					r.message.effective_date,
				]),
				indicator: "green",
			});
			frm.trigger("fetch_exchange_rate");
			frm.trigger("setup_exchange_rate_buttons");
		},
	});
}
