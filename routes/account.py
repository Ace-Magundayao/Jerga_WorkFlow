"""Account routes: change password."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from extensions import db

account_bp = Blueprint("account", __name__)


@account_bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate: correct current password, strong enough, matching, and different
        if not current_user.check_password(current_password):
            flash("Your current password is incorrect.", "danger")
        elif len(new_password) < 8:
            flash("New password must contain at least 8 characters.", "danger")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "danger")
        elif new_password == current_password:
            flash("New password must be different from the current password.", "danger")
        else:
            try:
                current_user.set_password(new_password)
                db.session.commit()
                flash("Password changed successfully!", "success")
                return redirect(url_for("account.change_password"))
            except Exception:
                db.session.rollback()
                flash("Unable to change the password. Please try again.", "danger")

    return render_template("account/change_password.html")
