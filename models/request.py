"""EmployeeRequest model: requests submitted by employees and reviewed by Admin/HR."""
from extensions import db


class EmployeeRequest(db.Model):
    __tablename__ = "employee_requests"

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)  # e.g. REQ-20260101-A1B2C3

    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Request content
    request_type = db.Column(db.String(100), nullable=False)  # Leave, Overtime, etc.
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=True)  # for cash advances / reimbursements

    # Review workflow
    status = db.Column(db.String(20), default="Pending", nullable=False)  # Pending | Approved | Rejected
    remarks = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    submitted_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # Relationships
    employee = db.relationship("Employee", back_populates="requests")
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id], back_populates="submitted_requests")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id], back_populates="reviewed_requests")
