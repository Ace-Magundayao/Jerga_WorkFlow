"""Biometrics routes: face enrollment/login, valid ID upload, and admin verification."""
import base64
import json
import os
from datetime import datetime

import cv2
import numpy as np

from flask import (
    Blueprint, abort, render_template, redirect, url_for, flash,
    request, current_app, send_from_directory,
)
from flask_login import login_user, login_required, current_user

from extensions import db
from models.user import User

biometrics_bp = Blueprint("biometrics", __name__, url_prefix="/biometrics")

UPLOAD_SUBFOLDER = "biometrics"                     # static/biometrics
FACE_MODEL = "face_detection_yunet_2023mar.onnx"    # face detector model in project root
MATCH_THRESHOLD = 0.90                              # minimum cosine similarity for a face match
ALLOWED_ID_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
VALID_ID_TYPES = [
    "PhilID / National ID",
    "Driver's License",
    "Passport",
    "SSS ID",
    "PhilHealth ID",
    "TIN ID",
    "Voter's ID",
    "Company ID",
]


def biometrics_folder():
    """Return the static/biometrics folder, creating it if needed."""
    folder = os.path.join(current_app.static_folder, UPLOAD_SUBFOLDER)
    os.makedirs(folder, exist_ok=True)
    return folder


def decode_uploaded_image(image_b64):
    """Decode a base64 data-URI ('data:image/...;base64,...') into raw bytes."""
    if not image_b64 or "," not in image_b64:
        return None
    try:
        return base64.b64decode(image_b64.split(",", 1)[1])
    except Exception:
        return None


def get_face_detector(image_width, image_height):
    """Create the YuNet face detector sized for the given image."""
    model_path = os.path.join(current_app.root_path, FACE_MODEL)
    return cv2.FaceDetectorYN.create(
        model_path, "", (image_width, image_height), score_threshold=0.6
    )


def extract_face_encoding(image_bytes):
    """Detect the largest face in the image and return a normalized
    HOG-style gradient histogram encoding, or None if no usable face."""
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return None

    height, width = image.shape[:2]
    if width < 100 or height < 100:
        return None

    try:
        detector = get_face_detector(width, height)
    except Exception:
        return None

    _, faces = detector.detect(image)
    if faces is None or len(faces) == 0:
        return None

    # Use the highest-confidence face (index 14 of each detection row)
    face_data = max(faces, key=lambda f: f[14])
    x, y, w, h = [int(v) for v in face_data[:4]]

    # Expand the box slightly for better face coverage
    pad_x, pad_y = int(w * 0.15), int(h * 0.15)
    x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
    x2, y2 = min(width, x + w + pad_x), min(height, y + h + pad_y)

    face = image[y1:y2, x1:x2]
    if face.size == 0:
        return None

    # Normalize to a fixed size, grayscale, and contrast-equalized
    face = cv2.resize(face, (128, 128))
    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    face = cv2.equalizeHist(face)

    # HOG-style signature using only core OpenCV: gradient magnitude and
    # angle, histogrammed into 16x16-pixel blocks with 9 orientation bins
    gx = cv2.Sobel(face, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(face, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    angle = np.arctan2(gy, gx)

    encoding = []
    for by in range(0, 128, 16):
        for bx in range(0, 128, 16):
            block_angle = angle[by:by + 16, bx:bx + 16]
            bins = ((block_angle + np.pi) / (2 * np.pi) * 9).astype(int) % 9

            hist = np.bincount(
                bins.ravel(),
                weights=magnitude[by:by + 16, bx:bx + 16].ravel(),
                minlength=9,
            )
            norm = np.linalg.norm(hist)
            if norm > 0:
                hist = hist / norm
            encoding.extend(hist.tolist())

    encoding = np.asarray(encoding, dtype=np.float32)
    norm = np.linalg.norm(encoding)
    if norm == 0:
        return None

    return (encoding / norm).tolist()


def compare_faces(encoding_a, encoding_b):
    """Cosine similarity between two normalized encodings (1.0 = identical)."""
    a = np.asarray(encoding_a, dtype=np.float32)
    b = np.asarray(encoding_b, dtype=np.float32)
    return float(np.dot(a, b))


# ==========================================
# ENROLLMENT (logged-in users)
# ==========================================

@biometrics_bp.route("/enroll", methods=["GET", "POST"])
@login_required
def enroll():
    """Capture and store the user's face encoding + photo."""
    if request.method == "POST":
        image_bytes = decode_uploaded_image(request.form.get("image", ""))

        if image_bytes is None:
            flash("No face captured. Please try again.", "danger")
        else:
            encoding = extract_face_encoding(image_bytes)
            if encoding is None:
                flash(
                    "No clear face was detected. Make sure your face is "
                    "well-lit and centered, then try again.",
                    "danger",
                )
            else:
                try:
                    # Save the enrollment photo under static/biometrics/
                    filename = f"user_{current_user.id}_face.jpg"
                    with open(os.path.join(biometrics_folder(), filename), "wb") as handle:
                        handle.write(image_bytes)

                    current_user.face_encoding = json.dumps(encoding)
                    current_user.face_photo = filename
                    current_user.face_enrolled_at = datetime.now()
                    db.session.commit()

                    flash("Face enrolled successfully! You can now use Face ID to sign in.", "success")
                    return redirect(url_for("biometrics.enroll"))
                except Exception:
                    db.session.rollback()
                    flash("Unable to save your face data. Please try again.", "danger")

    return render_template("biometrics/enroll.html")


@biometrics_bp.route("/unenroll", methods=["POST"])
@login_required
def unenroll():
    """Remove the user's face enrollment (photo and stored encoding)."""
    try:
        if current_user.face_photo:
            path = os.path.join(biometrics_folder(), current_user.face_photo)
            if os.path.exists(path):
                os.remove(path)

        current_user.face_encoding = None
        current_user.face_photo = None
        current_user.face_enrolled_at = None
        db.session.commit()

        flash("Face enrollment removed.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to remove face enrollment.", "danger")

    return redirect(url_for("biometrics.enroll"))


# ==========================================
# FACE LOGIN (unauthenticated)
# ==========================================

@biometrics_bp.route("/login", methods=["GET", "POST"])
def face_login():
    """Sign a user in by matching their face against all enrolled users."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        image_bytes = decode_uploaded_image(request.form.get("image", ""))

        if image_bytes is None:
            flash("No face captured. Please try again.", "danger")
            return render_template("biometrics/face_login.html")

        encoding = extract_face_encoding(image_bytes)
        if encoding is None:
            flash(
                "No clear face was detected. Make sure your face is "
                "well-lit and centered, then try again.",
                "danger",
            )
            return render_template("biometrics/face_login.html")

        # Compare against every enrolled, active user; keep the best match
        enrolled_users = User.query.filter(
            User.face_encoding.isnot(None), User.is_active.is_(True)
        ).all()

        if not enrolled_users:
            flash(
                "No accounts are enrolled with Face ID yet. "
                "Log in with your password first and enroll.",
                "danger",
            )
            return render_template("biometrics/face_login.html")

        best_match, best_score = None, 0.0
        for user in enrolled_users:
            try:
                stored = json.loads(user.face_encoding)
            except Exception:
                continue
            score = compare_faces(encoding, stored)
            if score > best_score:
                best_match, best_score = user, score

        if best_match and best_score >= MATCH_THRESHOLD:
            login_user(best_match)
            flash(f"Welcome back, {best_match.username}! Signed in with Face ID.", "success")
            return redirect(url_for("auth.dashboard"))

        flash("Face not recognized. Please try again or sign in with your password.", "danger")

    return render_template("biometrics/face_login.html")


# ==========================================
# VALID ID UPLOAD + VERIFICATION
# ==========================================

@biometrics_bp.route("/verify-id", methods=["GET", "POST"])
@login_required
def verify_id():
    """Upload a photo of a valid ID for admin verification."""
    if request.method == "POST":
        id_type = request.form.get("id_type", "").strip()
        document = request.files.get("id_document")

        # Validate ID type, file presence, and file extension
        extension = ""
        if document and "." in document.filename:
            extension = document.filename.rsplit(".", 1)[-1].lower()

        if id_type not in VALID_ID_TYPES:
            flash("Please select a valid ID type.", "danger")
        elif not document or document.filename == "":
            flash("Please upload a photo of your valid ID.", "danger")
        elif extension not in ALLOWED_ID_EXTENSIONS:
            flash("ID image must be PNG, JPG, JPEG, or WEBP.", "danger")
        else:
            try:
                filename = f"user_{current_user.id}_id.{extension}"
                document.save(os.path.join(biometrics_folder(), filename))

                current_user.id_document = filename
                current_user.id_document_type = id_type
                current_user.id_verified = False       # reset any previous verification
                current_user.id_verified_by_id = None
                db.session.commit()

                flash("Valid ID submitted! An administrator will verify it shortly.", "success")
                return redirect(url_for("biometrics.verify_id"))
            except Exception:
                db.session.rollback()
                flash("Unable to upload your ID. Please try again.", "danger")

    return render_template("biometrics/verify_id.html", id_types=VALID_ID_TYPES)


@biometrics_bp.route("/id-image/<int:user_id>")
@login_required
def id_image(user_id):
    """Serve an uploaded ID image; only admins and the ID owner may view it."""
    if current_user.role != "admin" and current_user.id != user_id:
        flash("You are not allowed to view this document.", "danger")
        return redirect(url_for("auth.dashboard"))

    user = db.session.get(User, user_id)
    if not user or not user.id_document:
        abort(404)

    return send_from_directory(biometrics_folder(), user.id_document)


@biometrics_bp.route("/face-image/<path:filename>")
@login_required
def face_image(filename):
    """Serve an enrollment photo; users may only view their own."""
    owner = filename.replace("user_", "").split("_")[0]
    if current_user.role != "admin" and str(current_user.id) != owner:
        abort(403)

    return send_from_directory(biometrics_folder(), filename)


# ==========================================
# ADMIN VERIFICATION QUEUE
# ==========================================

def admin_required():
    """Redirect non-admins away from the admin pages. Returns True if allowed."""
    if current_user.role != "admin":
        flash("Only administrators can access this page.", "danger")
        return False
    return True


@biometrics_bp.route("/admin/verifications")
@login_required
def admin_verifications():
    if not admin_required():
        return redirect(url_for("auth.dashboard"))

    # Split users with an uploaded ID into pending and verified lists
    filters = [User.id_document.isnot(None)]
    pending = User.query.filter(*filters, User.id_verified.is_(False)).order_by(User.username.asc()).all()
    verified = User.query.filter(*filters, User.id_verified.is_(True)).order_by(User.username.asc()).all()

    return render_template(
        "biometrics/admin_verifications.html", pending=pending, verified=verified
    )


@biometrics_bp.route("/admin/verify/<int:user_id>", methods=["POST"])
@login_required
def admin_verify(user_id):
    """Mark a user's ID as verified."""
    if not admin_required():
        return redirect(url_for("auth.dashboard"))

    user = db.session.get(User, user_id)
    if not user or not user.id_document:
        flash("No ID document found for this account.", "danger")
        return redirect(url_for("biometrics.admin_verifications"))

    try:
        user.id_verified = True
        user.id_verified_by_id = current_user.id
        db.session.commit()
        flash(f"ID verified for {user.username}.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to update verification status.", "danger")

    return redirect(url_for("biometrics.admin_verifications"))


@biometrics_bp.route("/admin/unverify/<int:user_id>", methods=["POST"])
@login_required
def admin_unverify(user_id):
    """Remove a user's ID verification."""
    if not admin_required():
        return redirect(url_for("auth.dashboard"))

    user = db.session.get(User, user_id)
    if not user:
        flash("Account not found.", "danger")
        return redirect(url_for("biometrics.admin_verifications"))

    try:
        user.id_verified = False
        user.id_verified_by_id = None
        db.session.commit()
        flash(f"Verification removed for {user.username}.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to update verification status.", "danger")

    return redirect(url_for("biometrics.admin_verifications"))
