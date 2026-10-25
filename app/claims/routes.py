"""Routes for item claim requests."""
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

from app.claims import claims
from app.extensions import db
from app.forms import ClaimForm
from app.models import Item, Claim


def _claim_to_dict(claim):
    return {
        "id": claim.id,
        "item_id": claim.item_id,
        "claimant_id": claim.claimant_id,
        "message": claim.message,
        "status": claim.status,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
    }


@claims.route("/item/<int:item_id>/claim", methods=["GET", "POST"])
@login_required
def create_claim(item_id):
    """Submit a claim request for an item."""
    item = db.session.get(Item, item_id)
    if not item or item.status not in ("approved", "returned"):
        abort(404)

    # The owner can't claim their own listing
    if item.user_id == current_user.id:
        flash("You cannot claim your own listing.", "warning")
        return redirect(url_for("main.item_details", item_id=item.id))

    existing = Claim.query.filter_by(
        item_id=item.id, claimant_id=current_user.id
    ).first()
    if existing:
        flash("You have already submitted a claim for this item.", "info")
        return redirect(url_for("main.item_details", item_id=item.id))

    form = ClaimForm()
    if form.validate_on_submit():
        claim = Claim(
            item_id=item.id,
            claimant_id=current_user.id,
            message=form.message.data.strip(),
            status="pending",
        )
        db.session.add(claim)
        db.session.commit()
        flash("Your claim has been submitted. The reporter will review it.", "success")
        return redirect(url_for("main.item_details", item_id=item.id))

    return render_template("claim_item.html", form=form, item=item)


@claims.route("/claim/<int:claim_id>/approve", methods=["POST"])
@login_required
def approve_claim(claim_id):
    """Approve a claim request — marks the item as returned."""
    claim = db.session.get(Claim, claim_id)
    if not claim:
        abort(404)

    item = claim.item
    if not item:
        abort(404)
    # Only the item owner or an admin can approve
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    claim.status = "approved"
    item.status = "returned"
    # Reject all other pending claims on this item
    for other in item.claims:
        if other.id != claim.id and other.status == "pending":
            other.status = "rejected"
    db.session.commit()
    flash("Claim approved. Item marked as returned.", "success")
    return redirect(url_for("main.dashboard"))


@claims.route("/claim/<int:claim_id>/reject", methods=["POST"])
@login_required
def reject_claim(claim_id):
    """Reject a claim request."""
    claim = db.session.get(Claim, claim_id)
    if not claim:
        abort(404)
    item = claim.item
    if not item:
        abort(404)
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    claim.status = "rejected"
    db.session.commit()
    flash("Claim rejected.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
@claims.route("/api/items/<int:item_id>/claims", methods=["POST"])
@login_required
def api_create_claim(item_id):
    item = db.session.get(Item, item_id)
    if not item or item.status not in ("approved", "returned"):
        return jsonify({"error": "Item not found"}), 404
    if item.user_id == current_user.id:
        return jsonify({"error": "You cannot claim your own listing"}), 400

    data = request.get_json(silent=True) or request.form
    message = (data.get("message") or "").strip()
    if len(message) < 10:
        return jsonify({"error": "Message must be at least 10 characters"}), 400

    existing = Claim.query.filter_by(
        item_id=item.id, claimant_id=current_user.id
    ).first()
    if existing:
        return jsonify({"error": "You have already claimed this item"}), 409

    claim = Claim(
        item_id=item.id,
        claimant_id=current_user.id,
        message=message,
        status="pending",
    )
    db.session.add(claim)
    db.session.commit()
    return jsonify(_claim_to_dict(claim)), 201


@claims.route("/api/claims/<int:claim_id>", methods=["PUT"])
@login_required
def api_update_claim(claim_id):
    claim = db.session.get(Claim, claim_id)
    if not claim:
        return jsonify({"error": "Claim not found"}), 404
    item = claim.item
    if item.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    data = request.get_json(silent=True) or request.form
    action = (data.get("status") or "").lower()
    if action == "approved":
        claim.status = "approved"
        item.status = "returned"
        for other in item.claims:
            if other.id != claim.id and other.status == "pending":
                other.status = "rejected"
    elif action == "rejected":
        claim.status = "rejected"
    else:
        return jsonify({"error": "status must be 'approved' or 'rejected'"}), 400

    db.session.commit()
    return jsonify(_claim_to_dict(claim))
