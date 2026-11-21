"""User model: login accounts, roles, and biometric enrollment data."""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")  # "admin" | "hr" | "employee"
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # Optional link to an employee profile
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), unique=True, nullable=True)
    employee = db.relationship("Employee", back_populates="user")

    # Requests this user submitted or reviewed
    submitted_requests = db.relationship(
        "EmployeeRequest", foreign_keys="EmployeeRequest.submitted_by_id", back_populates="submitted_by"
    )
    reviewed_requests = db.relationship(
        "EmployeeRequest", foreign_keys="EmployeeRequest.reviewed_by_id", back_populates="reviewed_by"
    )

    notifications = db.relationship(
        "Notification", back_populates="user", lazy=True, cascade="all, delete-orphan"
    )

    # --- Face recognition (encoding stored as JSON text, photo kept for reference) ---
    face_encoding = db.Column(db.Text, nullable=True)
    face_enrolled_at = db.Column(db.DateTime, nullable=True)
    face_photo = db.Column(db.String(255), nullable=True)

    # --- Password reset (admin-issued code; null when not pending) ---
    reset_code = db.Column(db.String(6), nullable=True)
    reset_code_expires = db.Column(db.DateTime, nullable=True)

    # --- Valid ID verification ---
    id_document = db.Column(db.String(255), nullable=True)          # uploaded file name
    id_document_type = db.Column(db.String(50), nullable=True)
    id_verified = db.Column(db.Boolean, default=False, nullable=False)
    id_verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def set_password(self, password):
        """Hash and store a new password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the password matches the stored hash."""
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
