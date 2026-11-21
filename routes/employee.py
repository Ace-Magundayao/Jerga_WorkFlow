"""Employee management routes (Admin/HR only): list, add, view, edit,
activate/deactivate, and link a login account to an employee."""
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models.employee import Employee
from models.user import User

employee_bp = Blueprint("employees", __name__, url_prefix="/employees")


def admin_or_hr_required(function):
    """Decorator: allow only Admin and HR users."""
    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ("admin", "hr"):
            abort(403)
        return function(*args, **kwargs)
    return decorated_function


def get_employee_or_404(employee_id):
    """Fetch an employee or abort with a 404 page."""
    employee = db.session.get(Employee, employee_id)
    if employee is None:
        abort(404)
    return employee


def parse_date(value):
    """Convert a 'YYYY-MM-DD' string into a date (or None if empty)."""
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def redirect_to_view(employee):
    """Redirect back to the employee's detail page."""
    return redirect(url_for("employees.view_employee", employee_id=employee.id))


@employee_bp.route("/")
@admin_or_hr_required
def list_employees():
    employees = Employee.query.order_by(Employee.created_at.desc()).all()
    return render_template("employees/list.html", employees=employees)


@employee_bp.route("/add", methods=["GET", "POST"])
@admin_or_hr_required
def add_employee():
    if request.method == "POST":
        employee_number = request.form.get("employee_number", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower() or None

        # Validate required fields and uniqueness
        if not employee_number or not first_name or not last_name:
            flash("Employee number, first name, and last name are required.", "danger")
        elif Employee.query.filter_by(employee_number=employee_number).first():
            flash("Employee number already exists.", "danger")
        elif email and Employee.query.filter_by(email=email).first():
            flash("Email address already exists.", "danger")
        else:
            try:
                employee = Employee(
                    employee_number=employee_number,
                    first_name=first_name,
                    middle_name=request.form.get("middle_name", "").strip() or None,
                    last_name=last_name,
                    gender=request.form.get("gender") or None,
                    birth_date=parse_date(request.form.get("birth_date")),
                    address=request.form.get("address", "").strip() or None,
                    contact_number=request.form.get("contact_number", "").strip() or None,
                    email=email,
                    department=request.form.get("department", "").strip() or None,
                    position=request.form.get("position", "").strip() or None,
                    employment_type=request.form.get("employment_type") or None,
                    date_hired=parse_date(request.form.get("date_hired")),
                    status="Active",
                )
                db.session.add(employee)
                db.session.commit()
                flash("Employee added successfully!", "success")
                return redirect(url_for("employees.list_employees"))
            except ValueError:
                db.session.rollback()
                flash("Invalid date. Please check your date fields.", "danger")
            except Exception:
                db.session.rollback()
                flash("Unable to add employee. Please check the information.", "danger")

    return render_template("employees/form.html", employee=None, page_title="Add Employee")


@employee_bp.route("/<int:employee_id>")
@admin_or_hr_required
def view_employee(employee_id):
    employee = get_employee_or_404(employee_id)

    # Candidate accounts: active, unlinked employee-role users.
    # If the profile has an email, only accounts with that same email qualify.
    query = User.query.filter(
        User.role == "employee",
        User.employee_id.is_(None),
        User.is_active.is_(True),
    )
    if employee.email:
        query = query.filter(User.email == employee.email.lower())

    available_accounts = query.order_by(User.username.asc()).all()

    return render_template(
        "employees/view.html", employee=employee, available_accounts=available_accounts
    )


@employee_bp.route("/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_or_hr_required
def edit_employee(employee_id):
    employee = get_employee_or_404(employee_id)

    if request.method == "POST":
        employee_number = request.form.get("employee_number", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower() or None

        # Required fields + uniqueness (excluding this employee itself)
        duplicate_number = Employee.query.filter(
            Employee.employee_number == employee_number, Employee.id != employee.id
        ).first()
        duplicate_email = (
            Employee.query.filter(Employee.email == email, Employee.id != employee.id).first()
            if email else None
        )

        if not employee_number or not first_name or not last_name:
            flash("Employee number, first name, and last name are required.", "danger")
        elif duplicate_number or duplicate_email:
            flash("Employee number or email is already in use.", "danger")
        else:
            try:
                employee.employee_number = employee_number
                employee.first_name = first_name
                employee.middle_name = request.form.get("middle_name", "").strip() or None
                employee.last_name = last_name
                employee.gender = request.form.get("gender") or None
                employee.birth_date = parse_date(request.form.get("birth_date"))
                employee.address = request.form.get("address", "").strip() or None
                employee.contact_number = request.form.get("contact_number", "").strip() or None
                employee.email = email
                employee.department = request.form.get("department", "").strip() or None
                employee.position = request.form.get("position", "").strip() or None
                employee.employment_type = request.form.get("employment_type") or None
                employee.date_hired = parse_date(request.form.get("date_hired"))

                db.session.commit()
                flash("Employee information updated successfully!", "success")
                return redirect_to_view(employee)
            except ValueError:
                db.session.rollback()
                flash("Invalid date. Please check your date fields.", "danger")
            except Exception:
                db.session.rollback()
                flash("Unable to update employee information.", "danger")

    return render_template("employees/form.html", employee=employee, page_title="Edit Employee")


@employee_bp.route("/<int:employee_id>/deactivate", methods=["POST"])
@admin_or_hr_required
def deactivate_employee(employee_id):
    """Mark the employee inactive and disable their login account."""
    employee = get_employee_or_404(employee_id)

    if employee.status == "Inactive":
        flash("Employee is already inactive.", "warning")
        return redirect(url_for("employees.list_employees"))

    employee.status = "Inactive"
    if employee.user:
        employee.user.is_active = False

    try:
        db.session.commit()
        flash("Employee deactivated successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to deactivate employee.", "danger")

    return redirect(url_for("employees.list_employees"))


@employee_bp.route("/<int:employee_id>/reactivate", methods=["POST"])
@admin_or_hr_required
def reactivate_employee(employee_id):
    """Mark the employee active again and re-enable their login account."""
    employee = get_employee_or_404(employee_id)

    if employee.status == "Active":
        flash("This employee is already active.", "info")
        return redirect_to_view(employee)

    employee.status = "Active"
    if employee.user:
        employee.user.is_active = True

    try:
        db.session.commit()
        flash("Employee reactivated successfully!", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to reactivate employee. Please try again.", "danger")

    return redirect_to_view(employee)


@employee_bp.route("/<int:employee_id>/link-account", methods=["POST"])
@admin_or_hr_required
def link_employee_account(employee_id):
    """Attach an existing user account to this employee profile."""
    employee = get_employee_or_404(employee_id)

    # Refuse inactive employees and employees that already have an account
    if employee.status != "Active":
        flash("Cannot link an account to an inactive employee.", "danger")
    elif employee.user:
        flash("This employee already has a linked account.", "warning")
    else:
        user_id = request.form.get("user_id", "").strip()

        if not user_id.isdigit():
            flash("Please select a valid account.", "danger")
        else:
            user = User.query.filter_by(
                id=int(user_id), role="employee", employee_id=None, is_active=True
            ).first()

            if not user:
                flash("Account is unavailable or already linked.", "danger")
            elif employee.email and user.email.lower() != employee.email.lower():
                # Emails must match when the profile has an email
                flash("The account email does not match the employee email.", "danger")
            else:
                try:
                    employee.user = user
                    db.session.commit()
                    flash("Employee login account linked successfully!", "success")
                except Exception:
                    db.session.rollback()
                    flash("Unable to link the account. Please try again.", "danger")

    return redirect_to_view(employee)
