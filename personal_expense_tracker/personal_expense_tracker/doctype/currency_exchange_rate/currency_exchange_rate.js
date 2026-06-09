frappe.ui.form.on("Currency Exchange Rate", {
	refresh(frm) {
		if (!can_sync_live_rates()) {
			return;
		}

		frm.add_custom_button(__("Sync SP Today Rates"), () => {
			sync_sp_today_exchange_rates(frm);
		});
	},
});

function can_sync_live_rates() {
	return frappe.user.has_role("Expense Manager") || frappe.user.has_role("System Manager");
}

function sync_sp_today_exchange_rates(frm) {
	if (!frm.doc.from_currency || !frm.doc.to_currency) {
		frappe.msgprint({
			title: __("Missing Currency Pair"),
			message: __("Please select From Currency and To Currency before syncing SP Today rates."),
			indicator: "blue",
		});
		return;
	}

	if (!frm.doc.effective_date) {
		frappe.msgprint({
			title: __("Missing Date"),
			message: __("Please select Effective Date before syncing SP Today rates."),
			indicator: "blue",
		});
		return;
	}

	frappe.call({
		method: "personal_expense_tracker.api.get_sp_today_exchange_rate_for_pair",
		args: {
			from_currency: frm.doc.from_currency,
			to_currency: frm.doc.to_currency,
			effective_date: frm.doc.effective_date,
			rate_type: "sell",
		},
		freeze: true,
		freeze_message: __("Fetching SP Today exchange rate..."),
		callback(r) {
			if (!r.message) {
				return;
			}

			frm.set_value("exchange_rate", r.message.exchange_rate);
			frm.set_value("source", r.message.source);
			frm.set_value("notes", r.message.notes);
			frappe.show_alert({
				message: __("SP Today exchange rate fetched for {0} on {1}.", [
					`${r.message.from_currency}/${r.message.to_currency}`,
					r.message.effective_date,
				]),
				indicator: "green",
			});
		},
	});
}
