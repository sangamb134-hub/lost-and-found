"""SQLAlchemy models for the Lost and Found system."""
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    """Application user — a student, faculty member, or admin."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # user | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship(
        "Item", backref="owner", lazy=True, cascade="all, delete-orphan"
    )
    claims = db.relationship(
        "Claim", backref="claimant", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email}>"


class Item(db.Model):
    """A lost or found item report."""

    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    # item_type: "lost" or "found"
    item_type = db.Column(db.String(10), nullable=False, index=True)
    date_reported = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    incident_date = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(200), nullable=False, index=True)
    # Reporter's private contact info — shared only when a claim is approved
    contact_info = db.Column(db.String(200), nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    # status: pending, approved, returned, rejected
    status = db.Column(db.String(20), nullable=False, default="approved", index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    claims = db.relationship(
        "Claim", backref="item", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Item {self.title} ({self.item_type})>"


class Claim(db.Model):
    """A claim request made by a user for an item."""

    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    claimant_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message = db.Column(db.Text, nullable=False)
    # status: pending, approved, rejected
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Claim item={self.item_id} by={self.claimant_id} status={self.status}>"
