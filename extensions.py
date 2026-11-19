"""Shared Flask extension instances (created here, initialized in app.py)."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Database
db = SQLAlchemy()

# Login handling: unauthenticated users are sent to the login page
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# CSRF protection for all POST forms
csrf = CSRFProtect()
