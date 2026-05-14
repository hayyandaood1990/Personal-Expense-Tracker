frappe.query_reports["Monthly Expense Summary"] = {
	filters: [
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			default: frappe.datetime.str_to_obj(frappe.datetime.nowdate()).getFullYear(),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
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
			options: ["SYP", "USD", "EUR"],
			default: "SYP",
			reqd: 1,
		},
	],
};
