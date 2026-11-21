"""Employee request routes: submit, view, edit, approve, and reject."""
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models.request import EmployeeRequest
from models.notification import Notification

request_bp = Blueprint("requests", __name__, url_prefix="/requests")

REQUEST_TYPES = ["Leave", "Overtime", "Cash Advance", "Reimbursement", "Other"]


# ==========================================
# ACCESS CONTROL
# ==========================================

def admin_or_hr_required(function):
    """Decorator: allow only Admin and HR users."""
    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ("admin", "hr"):
            abort(403)
        return function(*args, **kwargs)
    return decorated_function


def get_request_or_404(request_id):
    """Fetch a request or abort with a 404 page."""
    employee_request = db.session.get(EmployeeRequest, request_id)
    if employee_request is None:
        abort(404)
    return employee_request


def can_access_request(employee_request):
    """Admin/HR can view anything; others only their own requests."""
    if current_user.role in ("admin", "hr"):
        return True
    return employee_request.submitted_by_id == current_user.id


def redirect_to_view(employee_request):
    """Redirect back to the request's detail page."""
    return redirect(url_for("requests.view_request", request_id=employee_request.id))


# ==========================================
# VALIDATION HELPERS
# ==========================================

def generate_reference_number():
    """Unique reference like 'REQ-20260118-A1B2C3'."""
    return "REQ-" + datetime.now().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()


def parse_optional_date(value):
    """Convert 'YYYY-MM-DD' to a date, or None if empty."""
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def parse_optional_amount(value):
    """Parse a non-negative decimal amount, or None if empty."""
    if not value:
        return None
    amount = Decimal(value)
    if not amount.is_finite():
        raise ValueError("Invalid amount.")
    if amount < 0:
        raise ValueError("Amount cannot be negative.")
    return amount


def validate_request_form():
    """Read the form, validate it, and return a dict of cleaned values.
    Raises ValueError with a user-friendly message on bad input."""
    request_type = request.form.get("request_type", "").strip()
    subject = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()

    if request_type not in REQUEST_TYPES:
        raise ValueError("Please select a valid request type.")
    if not subject or not description:
        raise ValueError("Subject and description are required.")

    start_date = parse_optional_date(request.form.get("start_date", ""))
    end_date = parse_optional_date(request.form.get("end_date", ""))
    amount = parse_optional_amount(request.form.get("amount", "").strip())

    if start_date and end_date and end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    return {
        "request_type": request_type,
        "subject": subject,
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "amount": amount,
    }


def notify_user(user_id, title, message):
    """Create and commit an in-app notification for a user."""
    db.session.add(Notification(
        user_id=user_id, title=title, message=message, notification_type="Request", is_read=False
    ))


@request_bp.route("/")
@login_required
def list_requests():
    """Admin/HR sees all requests; employees see only their own."""
    query = EmployeeRequest.query
    if current_user.role not in ("admin", "hr"):
        query = query.filter_by(submitted_by_id=current_user.id)

    requests_list = query.order_by(EmployeeRequest.submitted_at.desc()).all()
    return render_template("requests/list.html", requests=requests_list)


@request_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_request():
    # Requests must belong to a linked employee profile
    if not current_user.employee_id:
        flash("Your account is not linked to an employee profile. Please contact HR.", "warning")
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        try:
            data = validate_request_form()
            employee_request = EmployeeRequest(
                reference_number=generate_reference_number(),
                employee_id=current_user.employee_id,
                submitted_by_id=current_user.id,
                **data,
                status="Pending",
            )
            db.session.add(employee_request)
            db.session.commit()
            flash("Request submitted successfully!", "success")
            return redirect_to_view(employee_request)

        except (ValueError, InvalidOperation) as error:
            db.session.rollback()
            flash(str(error), "danger")
        except Exception:
            db.session.rollback()
            flash("Unable to submit your request. Please try again.", "danger")

    return render_template(
        "requests/form.html", employee_request=None, request_types=REQUEST_TYPES, page_title="Submit Request"
    )


@request_bp.route("/<int:request_id>")
@login_required
def view_request(request_id):
    employee_request = get_request_or_404(request_id)

    if not can_access_request(employee_request):
        abort(403)

    return render_template("requests/view.html", employee_request=employee_request)


@request_bp.route("/<int:request_id>/edit", methods=["GET", "POST"])
@login_required
def edit_request(request_id):
    employee_request = get_request_or_404(request_id)

    if not can_access_request(employee_request):
        abort(403)

    if employee_request.status != "Pending":
        flash("Only pending requests can be edited.", "warning")
        return redirect_to_view(employee_request)

    if request.method == "POST":
        try:
            data = validate_request_form()
            employee_request.request_type = data["request_type"]
            employee_request.subject = data["subject"]
            employee_request.description = data["description"]
            employee_request.start_date = data["start_date"]
            employee_request.end_date = data["end_date"]
            employee_request.amount = data["amount"]

            db.session.commit()
            flash("Request updated successfully!", "success")
            return redirect_to_view(employee_request)

        except (ValueError, InvalidOperation) as error:
            db.session.rollback()
            flash(str(error), "danger")
        except Exception:
            db.session.rollback()
            flash("Unable to update the request.", "danger")

    return render_template(
        "requests/form.html", employee_request=employee_request, request_types=REQUEST_TYPES, page_title="Edit Request"
    )


def review_request(employee_request, new_status, title_prefix):
    """Shared logic for approve/reject: guard rails, update status, notify the owner."""
    # Reviewers cannot act on their own requests
    if employee_request.submitted_by_id == current_user.id:
        flash(f"You cannot {new_status.lower()} your own request.", "danger")
        return False
    if employee_request.status != "Pending":
        flash("This request has already been reviewed.", "warning")
        return False

    remarks = request.form.get("remarks", "").strip()
    if new_status == "Rejected" and not remarks:
        flash("Please provide a reason for rejecting this request.", "danger")
        return False

    employee_request.status = new_status
    employee_request.remarks = remarks
    employee_request.reviewed_by_id = current_user.id
    employee_request.reviewed_at = datetime.now()

    message = f"Your request {employee_request.reference_number} has been {new_status.lower()}."
    if remarks:
        message += f" Reason: {remarks}"

    notify_user(employee_request.submitted_by_id, title_prefix, message)
    return True


@request_bp.route("/<int:request_id>/approve", methods=["POST"])
@admin_or_hr_required
def approve_request(request_id):
    employee_request = get_request_or_404(request_id)

    try:
        if review_request(employee_request, "Approved", "Request Approved"):
            db.session.commit()
            flash("Request approved successfully!", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to approve the request.", "danger")

    return redirect_to_view(employee_request)


@request_bp.route("/<int:request_id>/reject", methods=["POST"])
@admin_or_hr_required
def reject_request(request_id):
    employee_request = get_request_or_404(request_id)

    try:
        if review_request(employee_request, "Rejected", "Request Rejected"):
            db.session.commit()
            flash("Request rejected successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to reject the request.", "danger")

    return redirect_to_view(employee_request)
