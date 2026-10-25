"""Admin routes for managing the entire system."""
from functools import wraps

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
)
from flask_login import login_required, current_user

from app.admin import admin
from app.extensions import db
from app.models import Item, Claim, User


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


@admin.route("/dashboard")
@login_required
def admin_dashboard():
    """Admin dashboard with statistics and management tools."""
    if not current_user.is_admin:
        abort(403)

    stats = {
        "total_users": User.query.count(),
        "total_items": Item.query.count(),
        "total_lost": Item.query.filter_by(item_type="lost").count(),
        "total_found": Item.query.filter_by(item_type="found").count(),
        "returned": Item.query.filter_by(status="returned").count(),
        "pending_claims": Claim.query.filter_by(status="pending").count(),
    }

    # Optional filters on the admin item list
    status = request.args.get("status")
    item_type = request.args.get("type")
    query = Item.query
    if status:
        query = query.filter(Item.status == status)
    if item_type in ("lost", "found"):
        query = query.filter(Item.item_type == item_type)
    items = query.order_by(Item.created_at.desc()).limit(50).all()

    pending_claims = (
        Claim.query.filter_by(status="pending")
        .order_by(Claim.created_at.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        items=items,
        pending_claims=pending_claims,
    )


@admin.route("/item/<int:item_id>/approve", methods=["POST"])
@admin_required
def approve_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    item.status = "approved"
    db.session.commit()
    flash("Item approved.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/item/<int:item_id>/reject", methods=["POST"])
@admin_required
def reject_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    item.status = "rejected"
    db.session.commit()
    flash("Item rejected.", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/item/<int:item_id>/mark-returned", methods=["POST"])
@admin_required
def mark_returned(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    item.status = "returned"
    db.session.commit()
    flash("Item marked as returned.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/item/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    from app.items.routes import delete_image_file

    delete_image_file(item.image_filename)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted by admin.", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/claim/<int:claim_id>/approve", methods=["POST"])
@admin_required
def approve_claim(claim_id):
    claim = db.session.get(Claim, claim_id)
    if not claim:
        abort(404)
    item = claim.item
    if item:
        claim.status = "approved"
        item.status = "returned"
        for other in item.claims:
            if other.id != claim.id and other.status == "pending":
                other.status = "rejected"
    db.session.commit()
    flash("Claim approved.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/claim/<int:claim_id>/reject", methods=["POST"])
@admin_required
def reject_claim(claim_id):
    claim = db.session.get(Claim, claim_id)
    if not claim:
        abort(404)
    claim.status = "rejected"
    db.session.commit()
    flash("Claim rejected.", "info")
    return redirect(url_for("admin.admin_dashboard"))
