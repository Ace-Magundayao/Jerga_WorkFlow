"""Application configuration."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key for sessions / CSRF (override with SECRET_KEY env var)
    SECRET_KEY = os.environ.get("SECRET_KEY", "workflow-development-secret-key")

    # SQLite database stored next to this file
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "workflow.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
