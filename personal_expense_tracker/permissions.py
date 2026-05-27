import frappe

from personal_expense_tracker.utils import is_expense_manager


def _user_condition(doctype: str, user: str | None = None):
	user = user or frappe.session.user
	if is_expense_manager(user):
		return None

	return f"`tab{doctype}`.`user` = {frappe.db.escape(user)}"


def get_expense_entry_query_conditions(user=None):
	return _user_condition("Expense Entry", user)


def get_income_entry_query_conditions(user=None):
	return _user_condition("Income Entry", user)


def get_monthly_budget_query_conditions(user=None):
	return _user_condition("Monthly Budget", user)


def has_expense_entry_permission(doc, ptype=None, user=None):
	return _has_user_owned_permission(doc, ptype, user)


def has_income_entry_permission(doc, ptype=None, user=None):
	return _has_user_owned_permission(doc, ptype, user)


def has_monthly_budget_permission(doc, ptype=None, user=None):
	return _has_user_owned_permission(doc, ptype, user)


def _has_user_owned_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if is_expense_manager(user):
		return True

	if ptype == "create":
		return True

	if not doc:
		return True

	return doc.get("user") == user
