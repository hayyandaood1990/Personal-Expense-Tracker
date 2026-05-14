frappe.ui.form.on("Monthly Budget", {
	refresh(frm) {
		frm.set_query("category", () => ({ filters: { is_active: 1 } }));
		frm.add_custom_button(__("Fetch Exchange Rate"), () => {
			frm.trigger("fetch_exchange_rate");
		});
		frm.trigger("calculate_budget_in_base");
		frm.trigger("show_budget_status");
	},

	currency(frm) {
		frm.trigger("fetch_exchange_rate");
	},

	budget_amount(frm) {
		frm.trigger("calculate_budget_in_base");
	},

	exchange_rate_to_base(frm) {
		frm.trigger("calculate_budget_in_base");
	},

	month(frm) {
		frm.trigger("show_budget_status");
	},

	year(frm) {
		frm.trigger("show_budget_status");
	},

	category(frm) {
		frm.trigger("show_budget_status");
	},

	fetch_exchange_rate(frm) {
		if (!frm.doc.currency) {
			return;
		}

		if (frm.doc.currency === "SYP") {
			frm.set_value("exchange_rate_to_base", 1).then(() => frm.trigger("calculate_budget_in_base"));
			return;
		}

		frappe.call({
			method: "personal_expense_tracker.api.get_latest_exchange_rate",
			args: {
				from_currency: frm.doc.currency,
				to_currency: "SYP",
				posting_date: frappe.datetime.nowdate(),
			},
			callback(r) {
				if (r.message && r.message.exchange_rate) {
					frm.set_value("exchange_rate_to_base", r.message.exchange_rate).then(() => {
						frm.trigger("calculate_budget_in_base");
					});
				} else {
					frappe.show_alert({
						message: __("No active exchange rate found for {0} to SYP.", [frm.doc.currency]),
						indicator: "orange",
					});
				}
			},
		});
	},

	calculate_budget_in_base(frm) {
		frm.set_value(
			"budget_in_base_currency",
			flt(frm.doc.budget_amount) * flt(frm.doc.exchange_rate_to_base)
		);
	},

	show_budget_status(frm) {
		if (!frm.doc.user || !frm.doc.month || !frm.doc.year || !frm.doc.category) {
			return;
		}

		frappe.call({
			method: "personal_expense_tracker.api.get_monthly_budget_status",
			args: {
				user: frm.doc.user,
				month: frm.doc.month,
				year: frm.doc.year,
				category: frm.doc.category,
				budget_name: frm.doc.name,
			},
			callback(r) {
				if (!r.message) {
					return;
				}

				const status = r.message;
				const remaining = format_currency(status.remaining, "SYP");
				const indicator = status.remaining >= 0 ? "green" : "red";
				frm.dashboard.clear_headline();
				frm.dashboard.set_headline(
					__("Remaining Budget: {0} ({1}% used)", [
						remaining,
						flt(status.usage_percent, 2),
					]),
					indicator
				);
			},
		});
	},
});
