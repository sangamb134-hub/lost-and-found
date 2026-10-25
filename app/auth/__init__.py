"""Authentication blueprint: register, login, logout."""
from flask import Blueprint

auth = Blueprint("auth", __name__)

from app.auth import routes  # noqa: E402
