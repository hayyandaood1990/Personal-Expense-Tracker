import frappe


ARABIC_CATEGORY_MAP = {
	"Housing Rent": "إيجار السكن",
	"Groceries & Meals": "المواد الغذائية والوجبات",
	"Clothing & Personal Items": "الملابس والأغراض الشخصية",
	"Vehicle & Fuel": "السيارة والوقود",
	"Public Transport": "المواصلات العامة",
	"Household Support": "دعم المنزل",
	"Gifts & Social Obligations": "الهدايا والالتزامات الاجتماعية",
	"Charity & Religious Giving": "الزكاة والتبرعات",
	"Visits & Hospitality": "الزيارات والضيافة",
	"Tobacco & Shisha": "التبغ والأركيلة",
	"Utilities": "الخدمات",
	"Health": "الصحة",
	"Education": "التعليم",
	"Entertainment": "الترفيه",
	"Savings": "المدخرات",
	"Miscellaneous": "المتفرقات",
}

ARABIC_DESCRIPTIONS = {
	"إيجار السكن": "إيجار المنزل ومدفوعات السكن.",
	"المواد الغذائية والوجبات": "مواد غذائية ووجبات ومشروبات وطعام المنزل.",
	"الملابس والأغراض الشخصية": "ملابس وأحذية وإكسسوارات ومشتريات شخصية.",
	"السيارة والوقود": "وقود وصيانة ومصاريف السيارة الشخصية.",
	"المواصلات العامة": "مواصلات عامة وتكاسي وباصات وتنقلات مشتركة.",
	"دعم المنزل": "مساعدة منزلية ودعم عائلي ومدفوعات دعم منزلية متكررة.",
	"الهدايا والالتزامات الاجتماعية": "هدايا وعيديات ومناسبات اجتماعية والتزامات عائلية.",
	"الزكاة والتبرعات": "زكاة وصدقات وتبرعات وعطاء ديني.",
	"الزيارات والضيافة": "مستلزمات ضيافة للزيارات والضيوف والحلويات والمناسبات المستضافة.",
	"التبغ والأركيلة": "سجائر وأركيلة وتبغ وفحم ومستلزمات مرتبطة.",
	"الخدمات": "كهرباء وماء وغاز وإنترنت وخدمات منزلية.",
	"الصحة": "رعاية صحية ودواء وصيدلية وزيارات طبيب وعلاج.",
	"التعليم": "دورات ومدرسة وكتب وتعلم ورسوم تعليمية.",
	"الترفيه": "ترفيه وراحة ومشاوير وأفلام ونشاطات ترفيهية.",
	"المدخرات": "مال يتم تخصيصه للادخار ولا يعامل كمصروف.",
	"المتفرقات": "مصاريف نادرة غير مصنفة ولا تناسب فئة أخرى.",
}


def execute():
	# Category document names must stay in English so Frappe can translate
	# them per user language through translated_doctype + ar.csv.
	return


def ensure_arabic_categories():
	for arabic_name, description in ARABIC_DESCRIPTIONS.items():
		if frappe.db.exists("Expense Category", arabic_name):
			continue

		frappe.get_doc(
			{
				"doctype": "Expense Category",
				"category_name": arabic_name,
				"is_active": 1,
				"description": description,
			}
		).insert(ignore_permissions=True)


def rename_categories_to_arabic():
	for english_name, arabic_name in ARABIC_CATEGORY_MAP.items():
		if not frappe.db.exists("Expense Category", english_name):
			continue

		if frappe.db.exists("Expense Category", arabic_name):
			merge_category_metadata(english_name, arabic_name)
			move_category_links(english_name, arabic_name)
			frappe.delete_doc("Expense Category", english_name, ignore_permissions=True, force=True)
		else:
			frappe.rename_doc(
				"Expense Category",
				english_name,
				arabic_name,
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


def update_arabic_descriptions():
	for arabic_name, description in ARABIC_DESCRIPTIONS.items():
		if not frappe.db.exists("Expense Category", arabic_name):
			continue

		frappe.db.set_value(
			"Expense Category",
			arabic_name,
			{
				"category_name": arabic_name,
				"is_active": 1,
				"description": description,
			},
			update_modified=False,
		)
