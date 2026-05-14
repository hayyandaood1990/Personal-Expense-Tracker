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
	frappe.call({
		method: "personal_expense_tracker.api.sync_exchange_rates_from_sp_today",
		args: {
			effective_date: frm.doc.effective_date || frappe.datetime.nowdate(),
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
			frm.reload_doc();
		},
	});
}
