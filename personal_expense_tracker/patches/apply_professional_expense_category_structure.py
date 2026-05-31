import frappe


CATEGORY_DEFINITIONS = {
	"Housing Rent": "Home rent and housing lease payments.",
	"Groceries & Meals": "Groceries, meals, snacks, drinks, and household food.",
	"Clothing & Personal Items": "Clothes, shoes, accessories, and personal shopping.",
	"Vehicle & Fuel": "Fuel, vehicle maintenance, and personal car expenses.",
	"Public Transport": "Public transport, taxis, buses, and shared rides.",
	"Household Support": "Household help, family support, and recurring home support payments.",
	"Gifts & Social Obligations": "Gifts, Eid money, social occasions, and family obligations.",
	"Charity & Religious Giving": "Zakat, charity, donations, and religious giving.",
	"Visits & Hospitality": "Hospitality items for visits, guests, sweets, and hosted occasions.",
	"Tobacco & Shisha": "Cigarettes, shisha, tobacco, charcoal, and related items.",
	"Utilities": "Electricity, water, gas, internet, and household services.",
	"Health": "Healthcare, medicine, pharmacy, doctor visits, and treatment.",
	"Education": "Courses, school, books, learning, and education fees.",
	"Entertainment": "Entertainment, leisure, outings, movies, and recreation.",
	"Savings": "Money intentionally set aside and not treated as spending.",
	"Miscellaneous": "Rare uncategorized expenses that do not fit another category.",
}

ARABIC_CATEGORY_NAMES = {
	"إيجار السكن",
	"المواد الغذائية والوجبات",
	"الملابس والأغراض الشخصية",
	"السيارة والوقود",
	"المواصلات العامة",
	"دعم المنزل",
	"الهدايا والالتزامات الاجتماعية",
	"الزكاة والتبرعات",
	"الزيارات والضيافة",
	"التبغ والأركيلة",
	"الخدمات",
	"الصحة",
	"التعليم",
	"الترفيه",
	"المدخرات",
	"المتفرقات",
}

RENAME_MAP = {
	"Rent": "Housing Rent",
	"Food": "Groceries & Meals",
	"Shopping": "Clothing & Personal Items",
	"Car Expenses": "Vehicle & Fuel",
	"Transport": "Public Transport",
	"Family": "Household Support",
	"Other": "Gifts & Social Obligations",
	"Smoking": "Tobacco & Shisha",
}


def execute():
	ensure_professional_categories()
	rename_existing_categories()
	ensure_professional_categories()
	reclassify_existing_expenses()
	split_social_obligations_budget()
	update_category_descriptions()
	frappe.db.commit()


def ensure_professional_categories():
	if any(frappe.db.exists("Expense Category", category) for category in ARABIC_CATEGORY_NAMES):
		return

	for category_name, description in CATEGORY_DEFINITIONS.items():
		if frappe.db.exists("Expense Category", category_name):
			continue

		frappe.get_doc(
			{
				"doctype": "Expense Category",
				"category_name": category_name,
				"is_active": 1,
				"description": description,
			}
		).insert(ignore_permissions=True)


def rename_existing_categories():
	for old_name, new_name in RENAME_MAP.items():
		if not frappe.db.exists("Expense Category", old_name):
			continue

		if frappe.db.exists("Expense Category", new_name):
			merge_category_metadata(old_name, new_name)
			move_category_links(old_name, new_name)
			frappe.delete_doc("Expense Category", old_name, ignore_permissions=True, force=True)
		else:
			frappe.rename_doc(
				"Expense Category",
				old_name,
				new_name,
				force=True,
				ignore_permissions=True,
				merge=False,
			)


def merge_category_metadata(old_name, new_name):
	old_category = frappe.db.get_value(
		"Expense Category",
		old_name,
		["monthly_budget"],
		as_dict=True,
	)
	new_category = frappe.db.get_value(
		"Expense Category",
		new_name,
		["monthly_budget"],
		as_dict=True,
	)
	if not old_category or not new_category:
		return

	values = {}
	for fieldname in ("monthly_budget",):
		if old_category.get(fieldname) and not new_category.get(fieldname):
			values[fieldname] = old_category.get(fieldname)

	if values:
		frappe.db.set_value("Expense Category", new_name, values, update_modified=False)


def move_category_links(old_name, new_name):
	linked_tables = (
		("Expense Entry", "category"),
		("Monthly Budget", "category"),
		("Expense Category", "parent_category"),
	)
	for doctype, fieldname in linked_tables:
		frappe.db.sql(
			f"update `tab{doctype}` set `{fieldname}` = %s where `{fieldname}` = %s",
			(new_name, old_name),
		)


def reclassify_existing_expenses():
	rows = frappe.get_all(
		"Expense Entry",
		filters={"category": "Gifts & Social Obligations"},
		fields=["name", "description", "notes"],
	)
	for row in rows:
		text = " ".join(filter(None, [row.description, row.notes]))
		category = classify_social_expense(text)
		if category != "Gifts & Social Obligations":
			frappe.db.set_value(
				"Expense Entry",
				row.name,
				"category",
				category,
				update_modified=False,
			)


def classify_social_expense(text):
	if any(keyword in text for keyword in ("زكاة", "صدقة", "تبرع")):
		return "Charity & Religious Giving"

	if any(keyword in text for keyword in ("صلنفة", "ضيافة", "حلويات", "رز", "بيت عمو", "بيت عمها")):
		return "Visits & Hospitality"

	return "Gifts & Social Obligations"


def split_social_obligations_budget():
	budgets = frappe.get_all(
		"Monthly Budget",
		filters={"category": "Gifts & Social Obligations"},
		fields=[
			"name",
			"user",
			"month",
			"year",
			"budget_amount",
			"currency",
			"exchange_rate_to_base",
			"budget_in_base_currency",
		],
	)
	for budget in budgets:
		if has_social_split_budgets(budget):
			continue

		original_amount = budget.budget_amount or budget.budget_in_base_currency or 0
		if not original_amount:
			continue

		allocations = {
			"Gifts & Social Obligations": 0.50,
			"Visits & Hospitality": 0.35,
			"Charity & Religious Giving": 0.15,
		}
		for category, ratio in allocations.items():
			amount = round(original_amount * ratio, 2)
			if category == "Gifts & Social Obligations":
				frappe.db.set_value(
					"Monthly Budget",
					budget.name,
					{
						"budget_amount": amount,
						"budget_in_base_currency": amount * (budget.exchange_rate_to_base or 1),
					},
					update_modified=False,
				)
				continue

			create_budget_if_missing(budget, category, amount)


def has_social_split_budgets(budget):
	return frappe.db.exists(
		"Monthly Budget",
		{
			"user": budget.user,
			"month": budget.month,
			"year": budget.year,
			"category": ["in", ["Visits & Hospitality", "Charity & Religious Giving"]],
		},
	)


def create_budget_if_missing(source_budget, category, amount):
	if frappe.db.exists(
		"Monthly Budget",
		{
			"user": source_budget.user,
			"month": source_budget.month,
			"year": source_budget.year,
			"category": category,
		},
	):
		return

	frappe.get_doc(
		{
			"doctype": "Monthly Budget",
			"user": source_budget.user,
			"month": source_budget.month,
			"year": source_budget.year,
			"category": category,
			"budget_amount": amount,
			"currency": source_budget.currency,
			"exchange_rate_to_base": source_budget.exchange_rate_to_base or 1,
		}
	).insert(ignore_permissions=True)


def update_category_descriptions():
	if any(frappe.db.exists("Expense Category", category) for category in ARABIC_CATEGORY_NAMES):
		return

	for category_name, description in CATEGORY_DEFINITIONS.items():
		if not frappe.db.exists("Expense Category", category_name):
			continue

		frappe.db.set_value(
			"Expense Category",
			category_name,
			{
				"category_name": category_name,
				"is_active": 1,
				"description": description,
			},
			update_modified=False,
		)
