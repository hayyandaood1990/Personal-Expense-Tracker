frappe.ui.form.on("Income Entry", {
	refresh(frm) {
		frm.add_custom_button(__("Fetch Exchange Rate"), () => {
			frm.trigger("fetch_exchange_rate");
		}, __("Exchange Rate"));

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

	fetch_exchange_rate(frm) {
		if (!frm.doc.currency || !frm.doc.base_currency) return;

		if (frm.doc.currency === frm.doc.base_currency) {
			frm.set_value("exchange_rate_to_base", 1).then(() => frm.trigger("calculate_income_in_base"));
			return;
		}

		frappe.call({
			method: "personal_expense_tracker.api.get_latest_exchange_rate",
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
					frappe.msgprint({
						title: __("Exchange Rate"),
						message: __("No active exchange rate found for {0} to {1}.", [
							frm.doc.currency,
							frm.doc.base_currency,
						]),
						indicator: "orange",
					});
				}
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
