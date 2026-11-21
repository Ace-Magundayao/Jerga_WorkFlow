"""Employee model: staff profiles managed by Admin/HR."""
from extensions import db


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_number = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)

    # Personal details
    gender = db.Column(db.String(20), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    address = db.Column(db.Text, nullable=True)
    contact_number = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)

    # Work details
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    employment_type = db.Column(db.String(50), nullable=True)
    date_hired = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="Active", nullable=False)  # "Active" | "Inactive"

    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # Linked login account (one-to-one) and submitted requests
    user = db.relationship("User", back_populates="employee", uselist=False)
    requests = db.relationship("EmployeeRequest", back_populates="employee")

    @property
    def full_name(self):
        """First + middle + last name, skipping any missing parts."""
        return " ".join(part for part in [self.first_name, self.middle_name, self.last_name] if part)
