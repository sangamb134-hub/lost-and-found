"""WSGI entry point for production (used by gunicorn and flask CLI)."""
import os
import click
from app import create_app

app = create_app()


@app.cli.command("seed-admin")
def seed_admin():
    """Manually seed the default admin account (safe to run multiple times)."""
    from app.extensions import db
    from app.models import User

    email = os.environ.get("ADMIN_EMAIL", "admin@lostfound.local")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")

    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(f"Admin already exists: {email}")
        return

    admin = User(name="Administrator", email=email, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Admin created: {email}")


if __name__ == "__main__":
    app.run()
