"""Notification routes: list, mark one as read, mark all as read."""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models.notification import Notification

notification_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notification_bp.route("/")
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return render_template("notifications/list.html", notifications=notifications, unread_count=unread_count)


@notification_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    """Mark a single notification as read (owner only)."""
    notification = db.session.get(Notification, notification_id)

    if notification is None or notification.user_id != current_user.id:
        flash("Notification not found.", "danger")
        return redirect(url_for("notifications.list_notifications"))

    try:
        notification.is_read = True
        db.session.commit()
        flash("Notification marked as read.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to update the notification.", "danger")

    return redirect(url_for("notifications.list_notifications"))


@notification_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    """Mark every unread notification of the current user as read."""
    try:
        Notification.query.filter_by(user_id=current_user.id, is_read=False)\
            .update({"is_read": True})
        db.session.commit()
        flash("All notifications marked as read.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to update notifications.", "danger")

    return redirect(url_for("notifications.list_notifications"))
