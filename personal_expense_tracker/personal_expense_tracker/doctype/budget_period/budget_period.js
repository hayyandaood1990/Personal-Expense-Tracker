frappe.ui.form.on("Budget Period", {
	from_date(frm) {
		frm.trigger("set_period_defaults");
	},

	to_date(frm) {
		frm.trigger("set_period_defaults");
	},

	set_period_defaults(frm) {
		if (!frm.doc.to_date) {
			return;
		}

		const to_date = frappe.datetime.str_to_obj(frm.doc.to_date);
		const months = [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		];
		frm.set_value("month", months[to_date.getMonth()]);
		frm.set_value("year", to_date.getFullYear());
	},
});
