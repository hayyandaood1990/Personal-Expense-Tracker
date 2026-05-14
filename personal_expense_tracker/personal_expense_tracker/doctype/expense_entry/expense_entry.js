frappe.ui.form.on("Expense Entry", {
	refresh(frm) {
		frm.set_query("category", () => ({ filters: { is_active: 1 } }));

		frm.add_custom_button(__("Fetch Exchange Rate"), () => {
			frm.trigger("fetch_exchange_rate");
		}, __("Exchange Rate"));

		if (can_sync_live_rates()) {
			frm.add_custom_button(__("Sync SP Today Rates"), () => {
				sync_sp_today_exchange_rates(frm);
			}, __("Exchange Rate"));
		}

		frm.trigger("show_base_amount_indicator");
	},

	posting_date(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	currency(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	base_currency(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	amount(frm) {
		frm.trigger("calculate_base_amount");
	},

	exchange_rate_to_base(frm) {
		frm.trigger("calculate_base_amount");
	},

	fetch_exchange_rate(frm) {
		const { currency, base_currency, posting_date } = frm.doc;
		if (!currency || !base_currency) {
			return;
		}

		if (currency === base_currency) {
			frm.set_value("exchange_rate_to_base", 1).then(() => frm.trigger("calculate_base_amount"));
			return;
		}

		frappe.call({
			method: "personal_expense_tracker.api.get_latest_exchange_rate",
			args: {
				from_currency: currency,
				to_currency: base_currency,
				posting_date: posting_date || frappe.datetime.nowdate(),
			},
			callback(r) {
				if (r.message && r.message.exchange_rate) {
					frm.set_value("exchange_rate_to_base", r.message.exchange_rate).then(() => {
						frm.trigger("calculate_base_amount");
					});
					frappe.show_alert({
						message: __("Exchange rate fetched from {0}", [r.message.effective_date]),
						indicator: "green",
					});
				} else {
					frappe.show_alert({
						message: __("No active exchange rate found for {0} to {1}.", [
							currency,
							base_currency,
						]),
						indicator: "orange",
					});
				}
			},
		});
	},

	calculate_base_amount(frm) {
		const amount = flt(frm.doc.amount);
		const rate = flt(frm.doc.exchange_rate_to_base);
		frm.set_value("amount_in_base_currency", amount * rate);
		frm.trigger("show_base_amount_indicator");
	},

	show_base_amount_indicator(frm) {
		frm.dashboard.clear_headline();

		if (!frm.doc.amount_in_base_currency) {
			return;
		}

		const currency = frm.doc.base_currency || "SYP";
		const formatted_amount = format_currency(frm.doc.amount_in_base_currency, currency);
		frm.dashboard.set_headline(
			__("Amount in {0}: {1}", [currency, formatted_amount]),
			"blue"
		);
	},
});

function can_sync_live_rates() {
	return frappe.user.has_role("Expense Manager") || frappe.user.has_role("System Manager");
}

function sync_sp_today_exchange_rates(frm) {
	frappe.call({
		method: "personal_expense_tracker.api.sync_exchange_rates_from_sp_today",
		args: {
			effective_date: frm.doc.posting_date || frappe.datetime.nowdate(),
			rate_type: "sell",
		},
		freeze: true,
		freeze_message: __("Syncing SP Today exchange rates..."),
		callback(r) {
			const updated_rates = (r.message && r.message.updated_rates) || [];
			frappe.show_alert({
				message: __("{0} SP Today exchange rates synced.", [updated_rates.length]),
				indicator: "green",
			});
			frm.trigger("fetch_exchange_rate");
		},
	});
}
