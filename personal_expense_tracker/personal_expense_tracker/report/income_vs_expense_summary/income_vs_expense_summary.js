frappe.query_reports["Income vs Expense Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "income_source",
			label: __("Income Source"),
			fieldtype: "Select",
			options: ["", "Paycheck", "Freelance", "Gift", "Investment", "Other"],
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
