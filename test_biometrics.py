
"""End-to-end test of the new features:
- Change password
- Face enrollment + face login (using real face photos)
- Valid ID upload + admin verification
"""
import base64
import re
import os

import numpy as np
import cv2

from app import app


# Download/prepare two different real-face test images if not present
FACE_A = "test_face_a.jpg"
FACE_B = "test_face_b.jpg"

if not os.path.exists(FACE_A):
    import urllib.request
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg",
        FACE_A
    )

if not os.path.exists(FACE_B):
    # Second face: crop a different region / use a mirrored, recolored variant
    # Note: for a true negative test a different person is ideal; a heavily
    # modified image should also fail to match above threshold.
    img = cv2.imread(FACE_A)
    img = cv2.flip(img, 1)
    img = cv2.convertScaleAbs(img, alpha=0.6, beta=-30)
    cv2.imwrite(FACE_B, img)


def face_b64(path):
    data = open(path, "rb").read()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def csrf(client, path="/login"):
    page = client.get(path)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.data.decode())
    if m is None:
        # Not logged in -> page redirected to login; grab token from there
        page = client.get("/login")
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.data.decode())
    return m.group(1)


app.config["TESTING"] = True

results = []
def check(name, cond):
    results.append((name, cond))
    print(("PASS" if cond else "FAIL"), "-", name)


# ---------- Reset admin password to a known state ----------
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(username="admin").first()
    admin.password_hash = generate_password_hash("Admin@12345")
    admin.face_encoding = None
    admin.face_photo = None
    admin.face_enrolled_at = None
    admin.id_document = None
    admin.id_document_type = None
    admin.id_verified = False
    db.session.commit()

# ---------- Change password ----------
c = app.test_client()
c.post("/login", data={"username": "admin", "password": "Admin@12345",
                       "csrf_token": csrf(c)})

r = c.get("/account/password")
check("Change password page loads", r.status_code == 200)

# Wrong current password rejected
r = c.post("/account/password", data={
    "current_password": "wrong", "new_password": "NewPass@999",
    "confirm_password": "NewPass@999", "csrf_token": csrf(c, "/account/password")
}, follow_redirects=True)
check("Wrong current password rejected", b"incorrect" in r.data)

# Mismatch rejected
r = c.post("/account/password", data={
    "current_password": "Admin@12345", "new_password": "NewPass@999",
    "confirm_password": "different", "csrf_token": csrf(c, "/account/password")
}, follow_redirects=True)
check("Password mismatch rejected", b"do not match" in r.data)

# Successful change
r = c.post("/account/password", data={
    "current_password": "Admin@12345", "new_password": "NewPass@999",
    "confirm_password": "NewPass@999", "csrf_token": csrf(c, "/account/password")
}, follow_redirects=True)
check("Change password success", b"changed successfully" in r.data)

# Login with new password works, old fails
c.get("/logout")
r = c.post("/login", data={"username": "admin", "password": "Admin@12345",
                           "csrf_token": csrf(c)}, follow_redirects=True)
check("Old password rejected after change", b"Invalid username or password" in r.data)

r = c.post("/login", data={"username": "admin", "password": "NewPass@999",
                           "csrf_token": csrf(c)}, follow_redirects=True)
check("New password works", b"Welcome back" in r.data)

# ---------- Face enrollment ----------
img1 = face_b64(FACE_A)
r = c.post("/biometrics/enroll", data={"image": img1,
                                       "csrf_token": csrf(c, "/biometrics/enroll")},
           follow_redirects=True)
check("Face enrollment success", b"enrolled successfully" in r.data)

# No face / garbage image rejected
r = c.post("/biometrics/enroll", data={"image": "data:image/jpeg;base64," +
                                       base64.b64encode(b"notanimage").decode(),
                                       "csrf_token": csrf(c, "/biometrics/enroll")},
           follow_redirects=True)
check("Garbage image rejected at enroll", b"No clear face" in r.data)

# ---------- Face login ----------
c.get("/logout")

# Same face should log us in as admin
r = c.post("/biometrics/login", data={
    "image": face_b64(FACE_A),
    "csrf_token": csrf(c, "/biometrics/login")
}, follow_redirects=True)
check("Face login with matching face", b"Signed in with Face ID" in r.data)
check("Face login went to dashboard", r.request.path == "/dashboard")

# Different face should be rejected
c.get("/logout")
r = c.post("/biometrics/login", data={
    "image": face_b64(FACE_B),
    "csrf_token": csrf(c, "/biometrics/login")
}, follow_redirects=True)
check("Face login rejects unknown face", b"Face not recognized" in r.data)

# ---------- Valid ID upload + verification ----------
# Log admin back in with the NEW password
c.post("/login", data={"username": "admin", "password": "NewPass@999",
                       "csrf_token": csrf(c)})

png = cv2.imencode(".png", np.full((200, 300, 3), 180, np.uint8))[1].tobytes()

# Proper multipart upload
from io import BytesIO
from werkzeug.datastructures import FileStorage

r = c.post("/biometrics/verify-id", content_type="multipart/form-data", data={
    "id_type": "Driver's License",
    "id_document": FileStorage(
        stream=BytesIO(png), filename="id.png",
        content_type="image/png"),
    "csrf_token": csrf(c, "/biometrics/verify-id")
}, follow_redirects=True)
check("ID upload success", b"ID submitted" in r.data)

r = c.get("/biometrics/admin/verifications")
check("Admin verifications page loads", r.status_code == 200)

with app.app_context():
    admin_id = User.query.filter_by(username="admin").first().id
r = c.post(f"/biometrics/admin/verify/{admin_id}",
           data={"csrf_token": csrf(c, "/biometrics/admin/verifications")},
           follow_redirects=True)
check("Admin verifies ID", b"ID verified for admin" in r.data)

# Unverify (remove)
r = c.post(f"/biometrics/admin/unverify/{admin_id}",
           data={"csrf_token": csrf(c, "/biometrics/admin/verifications")},
           follow_redirects=True)
check("Admin removes verification", b"removed" in r.data)

# Restore the original admin password at the end
with app.app_context():
    admin = User.query.filter_by(username="admin").first()
    admin.password_hash = generate_password_hash("Admin@12345")
    admin.face_encoding = None
    admin.face_photo = None
    admin.face_enrolled_at = None
    admin.id_document = None
    admin.id_document_type = None
    admin.id_verified = False
    db.session.commit()

failed = [n for n, v in results if not v]
print()
print("RESULT:", "ALL PASS" if not failed else f"{len(failed)} FAILED: {failed}")
