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

ARABIC_TO_ENGLISH_CATEGORY_MAP = {
	"إيجار السكن": "Housing Rent",
	"المواد الغذائية والوجبات": "Groceries & Meals",
	"الملابس والأغراض الشخصية": "Clothing & Personal Items",
	"السيارة والوقود": "Vehicle & Fuel",
	"المواصلات العامة": "Public Transport",
	"دعم المنزل": "Household Support",
	"الهدايا والالتزامات الاجتماعية": "Gifts & Social Obligations",
	"الزكاة والتبرعات": "Charity & Religious Giving",
	"الزيارات والضيافة": "Visits & Hospitality",
	"التبغ والأركيلة": "Tobacco & Shisha",
	"الخدمات": "Utilities",
	"الصحة": "Health",
	"التعليم": "Education",
	"الترفيه": "Entertainment",
	"المدخرات": "Savings",
	"المتفرقات": "Miscellaneous",
}


def execute():
	enable_category_translation()
	ensure_english_categories()
	rename_arabic_categories_to_english()
	update_english_category_metadata()
	frappe.db.commit()


def enable_category_translation():
	frappe.db.set_value(
		"DocType",
		"Expense Category",
		"translated_doctype",
		1,
		update_modified=False,
	)


def ensure_english_categories():
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


def rename_arabic_categories_to_english():
	for arabic_name, english_name in ARABIC_TO_ENGLISH_CATEGORY_MAP.items():
		if not frappe.db.exists("Expense Category", arabic_name):
			continue

		if frappe.db.exists("Expense Category", english_name):
			merge_category_metadata(arabic_name, english_name)
			move_category_links(arabic_name, english_name)
			frappe.delete_doc("Expense Category", arabic_name, ignore_permissions=True, force=True)
		else:
			frappe.rename_doc(
				"Expense Category",
				arabic_name,
				english_name,
				force=True,
				ignore_permissions=True,
				merge=False,
			)
			frappe.db.set_value(
				"Expense Category",
				english_name,
				"category_name",
				english_name,
				update_modified=False,
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


def update_english_category_metadata():
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
