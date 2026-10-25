"""Claims blueprint: submit, approve, reject claims."""
from flask import Blueprint

claims = Blueprint("claims", __name__)

from app.claims import routes  # noqa: E402
