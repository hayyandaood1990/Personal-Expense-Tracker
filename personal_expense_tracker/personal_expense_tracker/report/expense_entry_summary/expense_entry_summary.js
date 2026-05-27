frappe.query_reports["Expense Entry Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
		},
		{
			fieldname: "category",
			label: __("Expense Category"),
			fieldtype: "Link",
			options: "Expense Category",
		},
		{
			fieldname: "description",
			label: __("Description"),
			fieldtype: "Data",
		},
		{
			fieldname: "notes",
			label: __("Notes"),
			fieldtype: "Data",
		},
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: ["", "SYP", "USD", "EUR"],
		},
	],
};
