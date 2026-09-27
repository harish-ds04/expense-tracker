"""
In-memory data store for the Student Expense Tracker.

This is intentionally simple: everything lives in plain Python
lists/dicts, and it resets whenever the Flask server restarts.
Later, this file can be swapped for a real database without
touching app.py much, since app.py only calls these functions.
"""

DEFAULT_CATEGORIES = {
    "Food": "🍔",
    "Travel": "🚌",
    "Shopping": "🛍️",
    "Bills": "🧾",
    "Entertainment": "🎬",
    "Other": "📦",
}

# name -> icon
categories = dict(DEFAULT_CATEGORIES)

# list of {"id", "amount", "category", "description", "date"}
expenses = []

_next_id = 1


def add_category(name):
    name = name.strip()
    if not name or name in categories:
        return False
    categories[name] = "🏷️"
    return True


def is_default_category(name):
    return name in DEFAULT_CATEGORIES


def category_has_expenses(name):
    return any(e["category"] == name for e in expenses)


def delete_category(name):
    if is_default_category(name):
        return False, "Default categories cannot be deleted."
    if category_has_expenses(name):
        return False, "Reassign that category's expenses before deleting it."
    categories.pop(name, None)
    return True, ""


def is_duplicate(amount, category, description, date, exclude_id=None):
    for e in expenses:
        if e["id"] == exclude_id:
            continue
        if (
            e["amount"] == amount
            and e["category"] == category
            and e["description"] == description
            and e["date"] == date
        ):
            return True
    return False


def add_expense(amount, category, description, date):
    global _next_id
    expense = {
        "id": _next_id,
        "amount": amount,
        "category": category,
        "description": description,
        "date": date,
    }
    expenses.append(expense)
    _next_id += 1
    return expense


def get_expense(expense_id):
    for e in expenses:
        if e["id"] == expense_id:
            return e
    return None


def update_expense(expense_id, amount, category, description, date):
    e = get_expense(expense_id)
    if e:
        e["amount"] = amount
        e["category"] = category
        e["description"] = description
        e["date"] = date
    return e


def delete_expense(expense_id):
    global expenses
    expenses[:] = [e for e in expenses if e["id"] != expense_id]


def get_total():
    return round(sum(e["amount"] for e in expenses), 2)


def get_category_breakdown():
    """Returns {category: total} for categories that have spending."""
    breakdown = {}
    total = get_total()
    for name in categories:
        amount = round(sum(e["amount"] for e in expenses if e["category"] == name), 2)
        if amount > 0:
            percent = round((amount / total) * 100) if total > 0 else 0
            breakdown[name] = {"amount": amount, "percent": percent}
    return breakdown


def get_recent_expenses(limit=5):
    return sorted(expenses, key=lambda e: e["id"], reverse=True)[:limit]


def get_sorted_expenses(sort_by="date_new"):
    if sort_by == "date_old":
        return sorted(expenses, key=lambda e: e["date"])
    if sort_by == "amount_high":
        return sorted(expenses, key=lambda e: e["amount"], reverse=True)
    if sort_by == "amount_low":
        return sorted(expenses, key=lambda e: e["amount"])
    if sort_by == "category":
        return sorted(expenses, key=lambda e: e["category"])
    # default: newest first
    return sorted(expenses, key=lambda e: (e["date"], e["id"]), reverse=True)


def reset_all():
    global categories, expenses, _next_id
    categories = dict(DEFAULT_CATEGORIES)
    expenses = []
    _next_id = 1
