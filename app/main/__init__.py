"""Main blueprint: home, browse, item details, search."""
from flask import Blueprint

main = Blueprint("main", __name__)

from app.main import routes  # noqa: E402
