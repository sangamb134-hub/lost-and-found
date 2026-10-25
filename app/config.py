"""Application configuration using environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared across environments."""

    # Secret key for sessions and CSRF tokens
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-do-not-use-in-production")

    # Database: Render exposes the production DB as DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # SQLAlchemy 1.4+ requires postgresql:// scheme while Render provides postgres://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            "DATABASE_URL", "sqlite:///lostfound.db"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
        os.environ.get("UPLOAD_FOLDER", "app/static/uploads"),
    )
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"
    AUTO_CREATE_TABLES = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # In production, schema is managed by Flask-Migrate (`flask db upgrade`)
    AUTO_CREATE_TABLES = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    AUTO_CREATE_TABLES = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the config class based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
