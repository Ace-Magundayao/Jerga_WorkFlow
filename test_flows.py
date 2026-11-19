"""End-to-end smoke test of every button/flow.
Run with:  python test_flows.py
"""
from app import app
from extensions import db
from models.user import User
from models.employee import Employee
from models.request import EmployeeRequest
from models.notification import Notification

# Disable CSRF so the test client can POST directly
app.config["WTF_CSRF_ENABLED"] = False
app.config["TESTING"] = True

c = app.test_client()

# Idempotent: reset records that may exist from a previous run
with app.app_context():
    Employee.query.filter_by(email="emp@jerga.com").delete()
    EmployeeRequest.query.delete()
    for uname in ("testemp", "admin", "testemp2"):
        user = User.query.filter_by(username=uname).first()
        if user:
            db.session.delete(user)
    db.session.commit()

results = []


def check(name, condition):
    """Record and print one PASS/FAIL result."""
    results.append((name, condition))
    print(("PASS" if condition else "FAIL"), "-", name)


# --- Register a new employee user (Register button) ---
r = c.post("/register", data={
    "username": "testemp", "email": "emp@jerga.com",
    "password": "password123", "confirm_password": "password123",
}, follow_redirects=True)
check("Register", r.status_code == 200)

# --- Login button ---
r = c.post("/login", data={"username": "testemp", "password": "password123"}, follow_redirects=True)
check("Login -> Dashboard", b"Welcome" in r.data)

# --- Requests list + create request (Submit button) ---
r = c.get("/requests/")
check("Requests list", r.status_code == 200)

# Link the account to an employee profile (required to submit requests)
with app.app_context():
    emp = Employee(employee_number="E-001", first_name="Test",
                   last_name="Employee", email="emp@jerga.com", status="Active")
    db.session.add(emp)
    db.session.commit()
    emp_id = emp.id
    user = User.query.filter_by(username="testemp").first()
    user.employee_id = emp_id
    db.session.commit()

r = c.post("/requests/create", data={
    "request_type": "Leave", "subject": "Vacation", "description": "Family vacation",
}, follow_redirects=True)
check("Submit request", b"submitted successfully" in r.data or b"Request Details" in r.data)

# --- Edit request button ---
r = c.post("/requests/1/edit", data={
    "request_type": "Leave", "subject": "Vacation Edit", "description": "Updated description",
}, follow_redirects=True)
check("Edit pending request", b"updated successfully" in r.data)

# --- Logout ---
r = c.get("/logout", follow_redirects=True)
check("Logout", b"logged out" in r.data)

# --- Admin login, then employee management ---
with app.app_context():
    admin = User(username="admin", email="admin2@jerga.com", role="admin")
    admin.set_password("adminpass123")
    db.session.add(admin)
    db.session.commit()

r = c.post("/login", data={"username": "admin", "password": "adminpass123"}, follow_redirects=True)
check("Admin login", b"admin" in r.data)

r = c.get("/employees/")
check("Employee list", r.status_code == 200)
with app.app_context():
    Employee.query.filter_by(employee_number="E-002").delete()
    db.session.commit()
r = c.post("/employees/add", data={
    "employee_number": "E-002", "first_name": "Juan", "last_name": "Dela Cruz",
}, follow_redirects=True)
check("Add employee", b"added successfully" in r.data)

# --- View + edit employee ---
with app.app_context():
    emp2_id = db.session.get(Employee, Employee.query.filter_by(employee_number="E-002").first().id).id
r = c.post(f"/employees/{emp2_id}/edit", data={
    "employee_number": "E-002", "first_name": "Juan", "last_name": "Dela Cruz Jr.",
}, follow_redirects=True)
check("Edit employee", b"updated successfully" in r.data)

# --- Approve request (Approve button) ---
r = c.post("/requests/1/approve", data={"remarks": "Enjoy!"}, follow_redirects=True)
check("Approve request", b"approved successfully" in r.data)

# --- Notifications for the employee (Mark Read buttons) ---
c.get("/logout", follow_redirects=True)
c.post("/login", data={"username": "testemp", "password": "password123"}, follow_redirects=True)
r = c.get("/notifications/")
check("Notifications page", r.status_code == 200 and b"Request Approved" in r.data)

with app.app_context():
    test_user = User.query.filter_by(username="testemp").first()
    notification = Notification.query.filter_by(user_id=test_user.id)\
        .order_by(Notification.id.desc()).first()
    notification_id = notification.id
r = c.post(f"/notifications/{notification_id}/read", follow_redirects=True)
check("Mark notification read", b"marked as read" in r.data)

# Second account used for the email-mismatch linking test
with app.app_context():
    db.session.add(User(username="testemp2", email="e2@jerga.com",
                        role="employee", password_hash="x"))
    db.session.commit()
    user2_id = User.query.filter_by(username="testemp2").first().id
    emp1_id = Employee.query.filter_by(email="emp@jerga.com").first().id

# --- Deactivate / reactivate employee buttons ---
c.get("/logout")
c.post("/login", data={"username": "admin", "password": "adminpass123"}, follow_redirects=True)
r = c.post("/employees/1/deactivate", follow_redirects=True)
check("Deactivate employee", b"deactivated successfully" in r.data)
r = c.post("/employees/1/reactivate", follow_redirects=True)
check("Reactivate employee", b"reactivated successfully" in r.data)

# --- Link account button ---
# Employee 1 has email emp@jerga.com, so linking testemp2 (e2@jerga.com)
# must be rejected. Employee 2 has no email, so it must succeed.
with app.app_context():
    employee1 = db.session.get(Employee, emp1_id)
    if employee1.user:  # unlink anything left over from a prior run
        employee1.user.employee_id = None
        employee1.user = None
    db.session.commit()

r = c.post(f"/employees/{emp1_id}/link-account", data={"user_id": str(user2_id)}, follow_redirects=True)
check("Link account rejects email mismatch", b"does not match" in r.data)
r = c.post(f"/employees/{emp2_id}/link-account", data={"user_id": str(user2_id)}, follow_redirects=True)
check("Link employee account", b"linked successfully" in r.data)

# --- Mark all read ---
c.post("/login", data={"username": "testemp", "password": "password123"}, follow_redirects=True)
r = c.post("/notifications/read-all", follow_redirects=True)
check("Mark all read", b"All notifications marked as read" in r.data)

# --- Summary ---
failed = [name for name, passed in results if not passed]
print()
print("RESULT:", "ALL PASS" if not failed else f"{len(failed)} FAILED: {failed}")
