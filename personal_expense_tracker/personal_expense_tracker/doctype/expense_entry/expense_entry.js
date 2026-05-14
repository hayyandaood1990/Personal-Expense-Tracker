frappe.ui.form.on("Expense Entry", {
	refresh(frm) {
		frm.set_query("category", () => ({ filters: { is_active: 1 } }));

		frm.add_custom_button(__("Fetch Exchange Rate"), () => {
			frm.trigger("fetch_exchange_rate");
		});

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
