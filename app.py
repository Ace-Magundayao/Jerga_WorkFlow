"""Application factory: creates and wires up the Flask app."""
import click

from flask import Flask, render_template
from flask_login import current_user
from werkzeug.security import generate_password_hash

from config import Config
from extensions import db, login_manager, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import all models so db.create_all() knows every table
    from models.user import User
    from models.employee import Employee
    from models.request import EmployeeRequest
    from models.notification import Notification

    # Register all route blueprints
    from routes.auth import auth_bp
    from routes.employee import employee_bp
    from routes.requests import request_bp
    from routes.notification import notification_bp
    from routes.account import account_bp
    from routes.biometrics import biometrics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(request_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(biometrics_bp)

    @app.context_processor
    def inject_notification_count():
        """Make the unread notification count available in every template."""
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
        return dict(unread_notification_count=unread_count)

    # Error pages
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    # Offline fallback page served by the service worker
    @app.route("/offline")
    def offline():
        return render_template("offline.html")

    # Create database tables on startup
    with app.app_context():
        db.create_all()

    @app.cli.command("create-admin")
    def create_admin():
        """CLI command: flask --app app create-admin"""
        username = click.prompt("Admin username").strip()
        email = click.prompt("Admin email").strip().lower()
        password = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)

        if not username or not email:
            raise click.ClickException("Username and email are required.")
        if len(password) < 8:
            raise click.ClickException("Password must contain at least 8 characters.")

        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            raise click.ClickException("Username or email is already registered.")

        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        click.echo("Administrator account created successfully!")

    return app


app = create_app()

if __name__ == "__main__":
    # Accessible from other devices (e.g. phones) on the same network
    app.run(debug=True, host="0.0.0.0", port=5000)
