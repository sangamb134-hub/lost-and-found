"""Items blueprint: report, view, update, delete lost/found items."""
from flask import Blueprint

items = Blueprint("items", __name__)

from app.items import routes  # noqa: E402
