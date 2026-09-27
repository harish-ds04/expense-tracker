from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for

import data

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # fine for a local learning project


@app.route("/")
def dashboard():
    sort_by = request.args.get("sort", "date_new")
    return render_template(
        "dashboard.html",
        total=data.get_total(),
        breakdown=data.get_category_breakdown(),
        expenses=data.get_sorted_expenses(sort_by),
        recent=data.get_recent_expenses(),
        categories=data.categories,
        sort_by=sort_by,
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
