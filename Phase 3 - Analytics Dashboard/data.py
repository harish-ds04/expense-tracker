"""
Data layer for the Student Expense Tracker.

v2.0: expenses are now stored in SQLite (see database.py) so they
survive a Flask restart. Categories remain a simple in-memory dict
for now -- that part of the app wasn't in scope for this upgrade.

Every function here keeps the same name and signature it had in the
in-memory version, so app.py and the templates didn't need to change.
"""

import calendar
import sqlite3
from datetime import date as _date

import database

DEFAULT_CATEGORIES = {
    "Food": "🍔",
    "Travel": "🚌",
    "Shopping": "🛍️",
    "Bills": "🧾",
    "Entertainment": "🎬",
    "Other": "📦",
}

# name -> icon (unchanged from v1: still in-memory, resets on restart)
categories = dict(DEFAULT_CATEGORIES)


# ---------------------------------------------------------------------------
# Categories (unchanged behavior from v1)
# ---------------------------------------------------------------------------

def add_category(name):
    name = name.strip()
    if not name or name in categories:
        return False
    categories[name] = "🏷️"
    return True


def is_default_category(name):
    return name in DEFAULT_CATEGORIES


def category_has_expenses(name):
    try:
        conn = database.get_connection()
        row = conn.execute(
            "SELECT 1 FROM expenses WHERE category = ? LIMIT 1", (name,)
        ).fetchone()
        conn.close()
        return row is not None
    except sqlite3.Error as e:
        print(f"[database error] category_has_expenses: {e}")
        return False


def delete_category(name):
    if is_default_category(name):
        return False, "Default categories cannot be deleted."
    if category_has_expenses(name):
        return False, "Reassign that category's expenses before deleting it."
    categories.pop(name, None)
    return True, ""


# ---------------------------------------------------------------------------
# Expenses (now backed by SQLite)
# ---------------------------------------------------------------------------

def is_duplicate(amount, category, description, date, exclude_id=None):
    try:
        conn = database.get_connection()
        if exclude_id is None:
            row = conn.execute(
                """SELECT 1 FROM expenses
                   WHERE amount = ? AND category = ? AND description = ? AND date = ?""",
                (amount, category, description, date),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT 1 FROM expenses
                   WHERE amount = ? AND category = ? AND description = ? AND date = ?
                   AND id != ?""",
                (amount, category, description, date, exclude_id),
            ).fetchone()
        conn.close()
        return row is not None
    except sqlite3.Error as e:
        print(f"[database error] is_duplicate: {e}")
        # Fail safe: don't block the user from saving just because the check failed.
        return False


def add_expense(amount, category, description, date):
    try:
        conn = database.get_connection()
        cursor = conn.execute(
            """INSERT INTO expenses (amount, category, description, date)
               VALUES (?, ?, ?, ?)""",
            (amount, category, description, date),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return get_expense(new_id)
    except sqlite3.Error as e:
        print(f"[database error] add_expense: {e}")
        raise RuntimeError("Could not save the expense. Please try again.") from e


def get_expense(expense_id):
    try:
        conn = database.get_connection()
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        conn.close()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[database error] get_expense: {e}")
        return None


def update_expense(expense_id, amount, category, description, date):
    try:
        conn = database.get_connection()
        conn.execute(
            """UPDATE expenses SET amount = ?, category = ?, description = ?, date = ?
               WHERE id = ?""",
            (amount, category, description, date, expense_id),
        )
        conn.commit()
        conn.close()
        return get_expense(expense_id)
    except sqlite3.Error as e:
        print(f"[database error] update_expense: {e}")
        raise RuntimeError("Could not update the expense. Please try again.") from e


def delete_expense(expense_id):
    try:
        conn = database.get_connection()
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[database error] delete_expense: {e}")
        raise RuntimeError("Could not delete the expense. Please try again.") from e


def get_total():
    try:
        conn = database.get_connection()
        row = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses").fetchone()
        conn.close()
        return round(row["total"], 2)
    except sqlite3.Error as e:
        print(f"[database error] get_total: {e}")
        return 0


def get_category_breakdown():
    """Returns {category: {"amount": x, "percent": y}} for categories that have spending."""
    try:
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses GROUP BY category"
        ).fetchall()
        conn.close()
    except sqlite3.Error as e:
        print(f"[database error] get_category_breakdown: {e}")
        return {}

    total = get_total()
    breakdown = {}
    for row in rows:
        amount = round(row["total"], 2)
        if amount > 0:
            percent = round((amount / total) * 100) if total > 0 else 0
            breakdown[row["category"]] = {"amount": amount, "percent": percent}
    return breakdown


def get_recent_expenses(limit=5):
    try:
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT * FROM expenses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[database error] get_recent_expenses: {e}")
        return []


# Fixed, known-safe set of ORDER BY clauses -- sort_by never goes into SQL directly.
_SORT_CLAUSES = {
    "date_old": "date ASC, id ASC",
    "amount_high": "amount DESC",
    "amount_low": "amount ASC",
    "category": "category ASC",
}


def get_sorted_expenses(sort_by="date_new"):
    """Kept for backward compatibility -- now just calls get_expenses() with no filters."""
    return get_expenses(sort_by=sort_by)


def get_expenses(search=None, category=None, month=None, sort_by="date_new"):
    """
    The main query behind the "All Expenses" table: optional search
    (matches description OR category, case-insensitive), optional exact
    category filter, optional month filter ("YYYY-MM"), and sorting --
    all combined in one parameterized query so nothing is ever pulled
    into Python just to be filtered there.
    """
    clauses = []
    params = []

    if search:
        clauses.append("(LOWER(description) LIKE ? OR LOWER(category) LIKE ?)")
        like_term = f"%{search.lower()}%"
        params.extend([like_term, like_term])

    if category:
        clauses.append("category = ?")
        params.append(category)

    if month:
        clauses.append("date LIKE ?")
        params.append(f"{month}%")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_clause = _SORT_CLAUSES.get(sort_by, "date DESC, id DESC")  # date_new = default

    try:
        conn = database.get_connection()
        rows = conn.execute(
            f"SELECT * FROM expenses {where_sql} ORDER BY {order_clause}", params
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[database error] get_expenses: {e}")
        return []


def get_available_months():
    """Distinct 'YYYY-MM' values that have at least one expense, newest first."""
    try:
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT DISTINCT substr(date, 1, 7) AS month FROM expenses ORDER BY month DESC"
        ).fetchall()
        conn.close()
        return [r["month"] for r in rows if r["month"]]
    except sqlite3.Error as e:
        print(f"[database error] get_available_months: {e}")
        return []


def reset_all():
    global categories
    categories = dict(DEFAULT_CATEGORIES)
    try:
        conn = database.get_connection()
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'expenses'")
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[database error] reset_all: {e}")
        raise RuntimeError("Could not reset data. Please try again.") from e


# ---------------------------------------------------------------------------
# Phase 3: Analytics
#
# Everything here reads from the WHOLE expenses table (not the filtered
# view behind search/category/month on the dashboard's expense list).
# Each function is a single grouped SQL query -- no per-day/per-month
# loops of individual queries.
# ---------------------------------------------------------------------------

def _month_key(year, month):
    return f"{year:04d}-{month:02d}"


def _shift_month(year, month, delta):
    """Returns (year, month) `delta` calendar months away (delta may be negative)."""
    total = year * 12 + (month - 1) + delta
    new_year, new_month0 = divmod(total, 12)
    return new_year, new_month0 + 1


def _month_total(month_key):
    try:
        conn = database.get_connection()
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE date LIKE ?",
            (f"{month_key}%",),
        ).fetchone()
        conn.close()
        return round(row["total"], 2)
    except sqlite3.Error as e:
        print(f"[database error] _month_total: {e}")
        return 0


def get_overall_stats():
    """
    All-time stats: how many expenses, the average, the single highest
    expense, and the category with the highest total spending.
    """
    try:
        conn = database.get_connection()
        row = conn.execute(
            "SELECT COUNT(*) AS count, COALESCE(AVG(amount), 0) AS avg_amount FROM expenses"
        ).fetchone()
        count = row["count"]
        average = round(row["avg_amount"], 2) if count else 0

        highest_row = conn.execute(
            "SELECT * FROM expenses ORDER BY amount DESC LIMIT 1"
        ).fetchone()
        highest_expense = dict(highest_row) if highest_row else None
        conn.close()
    except sqlite3.Error as e:
        print(f"[database error] get_overall_stats: {e}")
        return {
            "count": 0,
            "average": 0,
            "highest_expense": None,
            "highest_category": None,
            "highest_category_amount": 0,
        }

    # Reuses get_category_breakdown() rather than running another grouped query.
    breakdown = get_category_breakdown()
    if breakdown:
        top_category, top_info = max(breakdown.items(), key=lambda kv: kv[1]["amount"])
        top_amount = top_info["amount"]
    else:
        top_category, top_amount = None, 0

    return {
        "count": count,
        "average": average,
        "highest_expense": highest_expense,
        "highest_category": top_category,
        "highest_category_amount": top_amount,
    }


def get_current_month_total():
    today = _date.today()
    return _month_total(_month_key(today.year, today.month))


def get_daily_totals(year=None, month=None):
    """
    Spending per day for one calendar month (defaults to the current
    month). Every day of the month is included, even ones with ₹0 --
    one grouped query, then a Python pass to fill in the gaps.
    """
    today = _date.today()
    year = year or today.year
    month = month or today.month
    month_key = _month_key(year, month)
    days_in_month = calendar.monthrange(year, month)[1]

    try:
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT date, SUM(amount) AS total FROM expenses WHERE date LIKE ? GROUP BY date",
            (f"{month_key}%",),
        ).fetchall()
        conn.close()
    except sqlite3.Error as e:
        print(f"[database error] get_daily_totals: {e}")
        rows = []

    totals_by_date = {r["date"]: round(r["total"], 2) for r in rows}
    daily = []
    for day in range(1, days_in_month + 1):
        day_date = f"{month_key}-{day:02d}"
        daily.append({"day": day, "date": day_date, "total": totals_by_date.get(day_date, 0)})
    return daily


def get_monthly_totals(num_months=6):
    """
    Spending per calendar month for the last `num_months` months
    (oldest first, current month last). Months with no expenses show
    ₹0 -- one grouped query, no per-month queries.
    """
    today = _date.today()
    month_keys = []
    for i in range(num_months - 1, -1, -1):
        y, m = _shift_month(today.year, today.month, -i)
        month_keys.append((y, m, _month_key(y, m)))

    try:
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT substr(date, 1, 7) AS month, SUM(amount) AS total FROM expenses GROUP BY month"
        ).fetchall()
        conn.close()
    except sqlite3.Error as e:
        print(f"[database error] get_monthly_totals: {e}")
        rows = []

    totals_by_month = {r["month"]: round(r["total"], 2) for r in rows}
    monthly = []
    for y, m, key in month_keys:
        label = _date(y, m, 1).strftime("%b %Y")
        monthly.append({"month": key, "label": label, "total": totals_by_month.get(key, 0)})
    return monthly


def get_month_comparison():
    """Current calendar month's spending vs the previous calendar month's."""
    today = _date.today()
    current_key = _month_key(today.year, today.month)
    prev_year, prev_month = _shift_month(today.year, today.month, -1)
    previous_key = _month_key(prev_year, prev_month)

    current_total = _month_total(current_key)
    previous_total = _month_total(previous_key)
    difference = round(current_total - previous_total, 2)

    if previous_total == 0:
        # Can't compute a meaningful percentage change from a ₹0 base.
        percent_change = None if current_total != 0 else 0
    else:
        percent_change = round((difference / previous_total) * 100, 1)

    return {
        "current_total": current_total,
        "previous_total": previous_total,
        "difference": difference,
        "percent_change": percent_change,
        "current_label": today.strftime("%B %Y"),
        "previous_label": _date(prev_year, prev_month, 1).strftime("%B %Y"),
    }
