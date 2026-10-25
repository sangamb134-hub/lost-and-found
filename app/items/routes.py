"""Routes for reporting, editing, and deleting lost/found items."""
import os
import uuid
from datetime import datetime

from PIL import Image
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    jsonify,
)
from flask_login import login_required, current_user

from app.items import items
from app.extensions import db
from app.forms import ItemForm
from app.models import Item


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_image(file_storage):
    """Validate, save, and resize an uploaded image. Returns filename or None."""
    if not file_storage or not file_storage.filename:
        return None

    filename = file_storage.filename
    if not allowed_file(filename):
        flash("Invalid file type. Only images are allowed.", "danger")
        return None

    ext = filename.rsplit(".", 1)[1].lower()
    # Generate a safe, unique filename
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, safe_name)

    try:
        file_storage.save(save_path)
    except Exception:
        current_app.logger.exception("Failed to save uploaded file")
        flash("Could not save the uploaded image.", "danger")
        return None

    # Downscale large images to keep storage reasonable
    try:
        with Image.open(save_path) as img:
            img.thumbnail((1024, 1024))
            img = img.convert("RGB") if img.mode in ("RGBA", "P") else img
            img.save(save_path, optimize=True)
    except Exception:
        # If Pillow fails, remove the broken file
        try:
            os.remove(save_path)
        except OSError:
            pass
        current_app.logger.exception("Image processing failed")
        flash("Uploaded file is not a valid image.", "danger")
        return None

    return safe_name


def delete_image_file(filename):
    """Remove an uploaded image file if it exists."""
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        current_app.logger.warning("Could not remove image file: %s", path)


@items.route("/report/lost", methods=["GET", "POST"])
@login_required
def report_lost():
    """Report a lost item."""
    form = ItemForm()
    form.submit.label.text = "Report Lost Item"
    if form.validate_on_submit():
        image_name = save_uploaded_image(form.image.data) if form.image.data else None
        item = Item(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category=form.category.data,
            item_type="lost",
            incident_date=form.incident_date.data,
            location=form.location.data.strip(),
            contact_info=form.contact.data.strip(),
            image_filename=image_name,
            status="approved",
            user_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash("Your lost item has been reported.", "success")
        return redirect(url_for("main.item_details", item_id=item.id))
    return render_template("report_lost.html", form=form)


@items.route("/report/found", methods=["GET", "POST"])
@login_required
def report_found():
    """Report a found item."""
    form = ItemForm()
    form.submit.label.text = "Report Found Item"
    if form.validate_on_submit():
        image_name = save_uploaded_image(form.image.data) if form.image.data else None
        item = Item(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category=form.category.data,
            item_type="found",
            incident_date=form.incident_date.data,
            location=form.location.data.strip(),
            contact_info=form.contact.data.strip(),
            image_filename=image_name,
            status="approved",
            user_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash("Thank you for reporting a found item.", "success")
        return redirect(url_for("main.item_details", item_id=item.id))
    return render_template("report_found.html", form=form)


@items.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    """Edit an item owned by the current user."""
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = ItemForm(obj=item)
    if form.validate_on_submit():
        item.title = form.title.data.strip()
        item.description = form.description.data.strip()
        item.category = form.category.data
        item.incident_date = form.incident_date.data
        item.location = form.location.data.strip()
        item.contact_info = form.contact.data.strip()

        if form.image.data and form.image.data.filename:
            old_image = item.image_filename
            new_image = save_uploaded_image(form.image.data)
            if new_image:
                item.image_filename = new_image
                delete_image_file(old_image)

        db.session.commit()
        flash("Item updated.", "success")
        return redirect(url_for("main.item_details", item_id=item.id))

    return render_template("edit_item.html", form=form, item=item)


@items.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    """Delete an item owned by the current user (or an admin)."""
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    delete_image_file(item.image_filename)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted.", "info")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# REST API (authenticated)
# ---------------------------------------------------------------------------
def _item_to_dict(item):
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


@items.route("/api/items", methods=["POST"])
@login_required
def api_create_item():
    data = request.get_json(silent=True) or request.form
    required = ["title", "description", "category", "item_type", "location", "incident_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if data.get("item_type") not in ("lost", "found"):
        return jsonify({"error": "item_type must be 'lost' or 'found'"}), 400

    try:
        incident_date = datetime.strptime(data["incident_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"error": "incident_date must be YYYY-MM-DD"}), 400

    item = Item(
        title=data["title"].strip()[:150],
        description=data["description"].strip()[:2000],
        category=data["category"],
        item_type=data["item_type"],
        incident_date=incident_date,
        location=data["location"].strip()[:200],
        status="approved",
        user_id=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(_item_to_dict(item)), 201


@items.route("/api/items/<int:item_id>", methods=["PUT"])
@login_required
def api_update_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    if item.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    data = request.get_json(silent=True) or request.form
    for field in ("title", "description", "category", "location"):
        if data.get(field):
            setattr(item, field, data[field])
    if data.get("incident_date"):
        try:
            item.incident_date = datetime.strptime(
                data["incident_date"], "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            return jsonify({"error": "incident_date must be YYYY-MM-DD"}), 400

    db.session.commit()
    return jsonify(_item_to_dict(item))


@items.route("/api/items/<int:item_id>", methods=["DELETE"])
@login_required
def api_delete_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    if item.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    delete_image_file(item.image_filename)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted"}), 200
