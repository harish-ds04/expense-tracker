from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for

import data
import database

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # fine for a local learning project

database.init_db()  # create expense_tracker.db / the expenses table if they don't exist yet


@app.route("/")
def dashboard():
    sort_by = request.args.get("sort", "date_new")
    search = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "").strip()
    month_filter = request.args.get("month", "").strip()
    is_filtered = bool(search or category_filter or month_filter)

    # Month dropdown needs friendly labels ("September 2026") for each "YYYY-MM" value.
    available_months = [
        (m, datetime.strptime(m, "%Y-%m").strftime("%B %Y")) for m in data.get_available_months()
    ]

    # Breakdown is reused for both the existing progress-bar card AND the new
    # category chart below -- one query, two views of the same data.
    breakdown = data.get_category_breakdown()

    # --- Phase 3: analytics. Always OVERALL / current-month data, regardless
    # of whatever search/category/month filter is applied to the expense
    # table above -- searching "food" must never change these numbers.
    overall_stats = data.get_overall_stats()
    daily_totals = data.get_daily_totals()
    monthly_totals = data.get_monthly_totals()
    month_comparison = data.get_month_comparison()

    return render_template(
        "dashboard.html",
        # Totals/breakdown/recent always reflect ALL expenses, not the current
        # search/filter -- only the "All Expenses" table below responds to those.
        total=data.get_total(),
        breakdown=breakdown,
        recent=data.get_recent_expenses(),
        expenses=data.get_expenses(
            search=search or None,
            category=category_filter or None,
            month=month_filter or None,
            sort_by=sort_by,
        ),
        categories=data.categories,
        sort_by=sort_by,
        search=search,
        category_filter=category_filter,
        month_filter=month_filter,
        is_filtered=is_filtered,
        available_months=available_months,
        # Analytics (chart-ready lists, built here so the template stays free of logic)
        overall_stats=overall_stats,
        current_month_label=date.today().strftime("%B %Y"),
        month_comparison=month_comparison,
        category_labels=list(breakdown.keys()),
        category_values=[info["amount"] for info in breakdown.values()],
        daily_labels=[str(d["day"]) for d in daily_totals],
        daily_values=[d["total"] for d in daily_totals],
        monthly_labels=[m["label"] for m in monthly_totals],
        monthly_values=[m["total"] for m in monthly_totals],
    )


@app.route("/add", methods=["GET", "POST"])
def add_expense():
    error = None
    if request.method == "POST":
        error = _validate_and_save(request.form)
        if error is None:
            flash("Expense added successfully.", "success")
            return redirect(url_for("dashboard"))

    return render_template(
        "add_expense.html",
        categories=data.categories,
        today=date.today().isoformat(),
        error=error,
        form=request.form,
        is_edit=False,
        expense_id=None,
    )


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    expense = data.get_expense(expense_id)
    if expense is None:
        flash("That expense no longer exists.", "error")
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        error = _validate_and_save(request.form, exclude_id=expense_id)
        if error is None:
            flash("Expense updated.", "success")
            return redirect(url_for("dashboard"))
        form_values = request.form
    else:
        form_values = expense

    return render_template(
        "add_expense.html",
        categories=data.categories,
        today=date.today().isoformat(),
        error=error,
        form=form_values,
        is_edit=True,
        expense_id=expense_id,
    )


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    data.delete_expense(expense_id)
    flash("Expense deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/category/add", methods=["POST"])
def add_category():
    name = request.form.get("category_name", "")
    if data.add_category(name):
        flash(f"Category '{name.strip()}' added.", "success")
    else:
        flash("Category name is empty or already exists.", "error")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/reset", methods=["POST"])
def reset_all():
    data.reset_all()
    flash("All data has been reset.", "success")
    return redirect(url_for("dashboard"))


def _validate_and_save(form, exclude_id=None):
    """Shared validation for add + edit. Returns an error string, or None on success."""
    amount_raw = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    description = form.get("description", "").strip()
    expense_date = form.get("date", "").strip()

    if not amount_raw:
        return "Amount is required."
    try:
        amount = round(float(amount_raw), 2)
    except ValueError:
        return "Amount must be a valid number."
    if amount <= 0:
        return "Amount must be greater than zero."

    if category not in data.categories:
        return "Please choose a valid category."

    if not expense_date:
        return "Date is required."
    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        return "Please enter a valid date."

    if data.is_duplicate(amount, category, description, expense_date, exclude_id=exclude_id):
        return "This looks like a duplicate (same amount, category, description and date)."

    if exclude_id is None:
        data.add_expense(amount, category, description, expense_date)
    else:
        data.update_expense(exclude_id, amount, category, description, expense_date)
    return None


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
