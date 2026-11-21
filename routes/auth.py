"""Authentication routes: register, login, logout, dashboard, password reset."""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models.user import User

auth_bp = Blueprint("auth", __name__)

# Email must end in a valid .com domain, e.g. name@gmail.com
EMAIL_SUFFIX = ".com"


def is_valid_com_email(email):
    """Basic shape check + require the address to end in '.com'."""
    import re
    if not email or not email.lower().endswith(EMAIL_SUFFIX):
        return False
    # something@domain.com  (local part, @, domain, then .com)
    return re.match(r"^[^@\s]+@[^@\s]+\.com$", email.lower()) is not None


@auth_bp.route("/")
def index():
    """Send logged-in users to the dashboard, everyone else to login."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate the form
        if not username or not email or not password:
            flash("Please complete all required fields.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif not is_valid_com_email(email):
            flash("Please enter a valid email address ending in .com (e.g. name@gmail.com).", "danger")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email is already registered.", "danger")
        else:
            # Create the new account
            new_user = User(username=username, email=email, role="employee")
            new_user.set_password(password)
            try:
                db.session.add(new_user)
                db.session.commit()
                flash("Registration successful! You can now log in.", "success")
                return redirect(url_for("auth.login"))
            except Exception:
                db.session.rollback()
                flash("Registration failed. Please try again.", "danger")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")

            # Honor ?next= only for safe, local paths
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("auth.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have successfully logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


# ==========================================
# FORGOT PASSWORD (admin-issued reset code)
# ==========================================

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """User requests a reset code; the code is issued by an admin
    on the dashboard and relayed to the user in person."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = User.query.filter_by(username=username).first()

        # Always show the same message so accounts can't be enumerated
        flash(
            "If that account exists, ask an administrator for your "
            "6-digit reset code, then continue below.",
            "info",
        )
        return render_template("auth/forgot_password.html", reset_username=username)

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Reset the password using username + the admin-issued 6-digit code."""
    username = request.form.get("username", "").strip() if request.method == "POST" \
        else request.args.get("username", "").strip()

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        user = User.query.filter_by(username=username).first()

        if not user or not user.reset_code:
            flash("No password reset is pending for this account.", "danger")
        elif user.reset_code_expires and user.reset_code_expires < datetime.now():
            flash("This reset code has expired. Ask for a new one.", "danger")
        elif code != user.reset_code:
            flash("Incorrect reset code. Please try again.", "danger")
        elif len(new_password) < 8:
            flash("New password must contain at least 8 characters.", "danger")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            try:
                user.set_password(new_password)
                user.reset_code = None
                user.reset_code_expires = None
                db.session.commit()
                flash("Password reset successfully! You can now log in.", "success")
                return redirect(url_for("auth.login"))
            except Exception:
                db.session.rollback()
                flash("Unable to reset the password. Please try again.", "danger")

    return render_template("auth/reset_password.html", reset_username=username)


@auth_bp.route("/admin/issue-reset-code", methods=["POST"])
@login_required
def admin_issue_reset_code():
    """Admin generates a 6-digit reset code for a user (shown once)."""
    if current_user.role != "admin":
        flash("Only administrators can issue reset codes.", "danger")
        return redirect(url_for("auth.dashboard"))

    username = request.form.get("username", "").strip()
    user = User.query.filter_by(username=username).first()

    if not user:
        flash(f"No account found with the username '{username}'.", "danger")
    else:
        import secrets
        code = f"{secrets.randbelow(1000000):06d}"  # zero-padded 6 digits
        try:
            user.reset_code = code
            user.reset_code_expires = datetime.now() + timedelta(minutes=30)
            db.session.commit()
            flash(
                f"Reset code for '{username}': {code} "
                "(valid for 30 minutes — share it with the user securely).",
                "success",
            )
        except Exception:
            db.session.rollback()
            flash("Unable to generate a reset code. Please try again.", "danger")

    return redirect(url_for("auth.dashboard"))
