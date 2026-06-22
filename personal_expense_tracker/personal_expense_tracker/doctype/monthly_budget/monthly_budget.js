frappe.ui.form.on("Monthly Budget", {
	refresh(frm) {
		frm.set_query("category", () => ({ filters: { is_active: 1 } }));
		frm.set_query("budget_period", () => ({ filters: { status: "Open" } }));
		frm.add_custom_button(__("Fetch Exchange Rate"), () => {
			frm.trigger("fetch_exchange_rate");
		});
		frm.trigger("set_default_budget_period");
		frm.trigger("calculate_budget_in_base");
		frm.trigger("show_budget_status");
	},

	budget_period(frm) {
		frm.trigger("sync_budget_period_fields");
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

	set_default_budget_period(frm) {
		if (!frm.is_new() || frm.doc.budget_period) {
			return;
		}

		frappe.call({
			method: "personal_expense_tracker.api.get_current_budget_period",
			callback(r) {
				if (r.message && r.message.name) {
					frm.set_value("budget_period", r.message.name);
				}
			},
		});
	},

	sync_budget_period_fields(frm) {
		if (!frm.doc.budget_period) {
			return;
		}

		frappe.db
			.get_value("Budget Period", frm.doc.budget_period, ["from_date", "to_date", "month", "year"])
			.then((r) => {
				const values = r.message;
				if (!values) {
					return;
				}

				frm.set_value("from_date", values.from_date);
				frm.set_value("to_date", values.to_date);
				frm.set_value("month", values.month);
				frm.set_value("year", values.year);
			});
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
		if (!frm.doc.user || !frm.doc.budget_period || !frm.doc.category) {
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
				budget_period: frm.doc.budget_period,
			},
			callback(r) {
				if (!r.message) {
					return;
				}

				const status = r.message;
				const income_remaining = format_currency(status.income_remaining, "SYP");
				const indicators = {
					safe: "green",
					warning: "yellow",
					danger: "orange",
					exceeded: "red",
					no_budget: "blue",
				};
				const indicator = indicators[status.status] || "blue";
				frm.dashboard.clear_headline();
				frm.dashboard.set_headline(
					`${status.message}<br>${__("Income left after all expenses: {0}", [income_remaining])}`,
					indicator
				);
			},
		});
	},
});
