"""Routes for public pages: home, browse, item details, search."""
from datetime import datetime

from flask import render_template, request, abort, jsonify, redirect, url_for, flash

from app.main import main
from app.models import Item, db


def _parse_date(value):
    """Parse a YYYY-MM-DD string safely; return None if invalid/empty."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@main.route("/")
def index():
    """Home page with hero, recent items, and statistics."""
    recent_lost = (
        Item.query.filter_by(item_type="lost")
        .order_by(Item.created_at.desc())
        .limit(4)
        .all()
    )
    recent_found = (
        Item.query.filter_by(item_type="found")
        .order_by(Item.created_at.desc())
        .limit(4)
        .all()
    )

    stats = {
        "total_lost": Item.query.filter_by(item_type="lost").count(),
        "total_found": Item.query.filter_by(item_type="found").count(),
        "returned": Item.query.filter_by(status="returned").count(),
        "total": Item.query.count(),
    }

    return render_template(
        "index.html",
        recent_lost=recent_lost,
        recent_found=recent_found,
        stats=stats,
    )


@main.route("/browse")
def browse():
    """Browse items with filters: status (lost/found), category, date, keyword, location."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    per_page = min(max(per_page, 1), 36)

    query = Item.query

    # Filter by item_type (lost/found)
    item_type = request.args.get("type")
    if item_type in ("lost", "found"):
        query = query.filter(Item.item_type == item_type)

    # Filter by status — only show approved/returned to the public
    status = request.args.get("status")
    if status:
        query = query.filter(Item.status == status)
    else:
        query = query.filter(Item.status.in_(["approved", "returned"]))

    # Keyword search across title and description
    keyword = request.args.get("q", "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(Item.title.ilike(like), Item.description.ilike(like))
        )

    # Category filter
    category = request.args.get("category")
    if category:
        query = query.filter(Item.category == category)

    # Location filter
    location = request.args.get("location", "").strip()
    if location:
        query = query.filter(Item.location.ilike(f"%{location}%"))

    # Date filter (incident date on or after)
    from_date = _parse_date(request.args.get("from_date"))
    if from_date:
        query = query.filter(Item.incident_date >= from_date)
    to_date = _parse_date(request.args.get("to_date"))
    if to_date:
        query = query.filter(Item.incident_date <= to_date)

    query = query.order_by(Item.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "browse.html",
        items=pagination.items,
        pagination=pagination,
        filters={
            "type": item_type or "",
            "q": keyword,
            "category": category or "",
            "location": location,
            "from_date": request.args.get("from_date", ""),
            "to_date": request.args.get("to_date", ""),
        },
    )


@main.route("/item/<int:item_id>")
def item_details(item_id):
    """Public item details page."""
    item = db.session.get(Item, item_id)
    if not item or item.status not in ("approved", "returned"):
        abort(404)
    return render_template("item_details.html", item=item)


# ---------------------------------------------------------------------------
# REST API (read-only, public)
# ---------------------------------------------------------------------------
@main.route("/api/stats")
def api_stats():
    return jsonify(
        {
            "total_lost": Item.query.filter_by(item_type="lost").count(),
            "total_found": Item.query.filter_by(item_type="found").count(),
            "returned": Item.query.filter_by(status="returned").count(),
            "total": Item.query.count(),
        }
    )


@main.route("/api/items")
def api_items():
    """JSON listing of items with the same filters as the browse page."""
    query = Item.query.filter(Item.status.in_(["approved", "returned"]))

    item_type = request.args.get("type")
    if item_type in ("lost", "found"):
        query = query.filter(Item.item_type == item_type)

    keyword = request.args.get("q", "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(Item.title.ilike(like), Item.description.ilike(like))
        )

    category = request.args.get("category")
    if category:
        query = query.filter(Item.category == category)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    pagination = query.order_by(Item.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "items": [_item_dict(i) for i in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


def _item_dict(item):
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "item_type": item.item_type,
        "location": item.location,
        "incident_date": item.incident_date.isoformat() if item.incident_date else None,
        "status": item.status,
        "image_url": (
            url_for("static", filename=f"uploads/{item.image_filename}")
            if item.image_filename
            else None
        ),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@main.route("/api/items/<int:item_id>")
def api_item_detail(item_id):
    item = db.session.get(Item, item_id)
    if not item or item.status not in ("approved", "returned"):
        return jsonify({"error": "Item not found"}), 404
    return jsonify(_item_dict(item))


from flask_login import login_required, current_user
from app.models import Claim


@main.route("/dashboard")
@login_required
def dashboard():
    """User dashboard: my reports, my claims, and claim requests on my items."""
    my_items = (
        Item.query.filter_by(user_id=current_user.id)
        .order_by(Item.created_at.desc())
        .all()
    )
    my_claims = (
        Claim.query.filter_by(claimant_id=current_user.id)
        .order_by(Claim.created_at.desc())
        .all()
    )

    # Claims made on items the user reported
    claims_on_my_items = []
    for item in my_items:
        for claim in item.claims:
            claims_on_my_items.append(claim)
    claims_on_my_items.sort(key=lambda c: c.created_at, reverse=True)

    return render_template(
        "dashboard.html",
        my_items=my_items,
        my_claims=my_claims,
        claims_on_my_items=claims_on_my_items,
    )
