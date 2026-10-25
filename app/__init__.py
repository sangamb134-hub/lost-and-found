"""Application factory for the Lost and Found Management System."""
import os

from flask import Flask, render_template
from flask_login import current_user

from app.config import get_config
from app.extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register blueprints
    from app.main import main as main_bp
    from app.auth import auth as auth_bp
    from app.items import items as items_bp
    from app.claims import claims as claims_bp
    from app.admin import admin as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(items_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # Jinja globals
    @app.context_processor
    def inject_globals():
        from app.models import Item
        return {
            "current_user": current_user,
            "item_categories": [
                "ID Card",
                "Wallet",
                "Book/Notebook",
                "Bag",
                "Mobile/Electronics",
                "Keys",
                "Other",
            ],
        }

    # App-wide error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="Access forbidden."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template(
            "error.html",
            code=413,
            message="The uploaded file is too large (max 5 MB).",
        ), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template(
            "error.html", code=429, message="Too many requests. Please slow down."
        ), 429

    # Ensure default admin + seed data on first run
    with app.app_context():
        _init_database(app)

    return app


def _init_database(app):
    """Create tables (dev only) and seed a default admin account if needed."""
    from app.models import User, Item

    if app.config.get("AUTO_CREATE_TABLES", False):
        db.create_all()

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@lostfound.local")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Seed the default admin only if the users table exists
    try:
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(name="Administrator", email=admin_email, role="admin")
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Created default admin: %s", admin_email)
    except Exception:
        # Table may not exist yet (production before first migration); skip seeding
        db.session.rollback()
