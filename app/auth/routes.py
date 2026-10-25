"""Authentication routes for users and administrators."""
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth
from app.extensions import db, limiter
from app.forms import RegistrationForm, LoginForm
from app.models import User


@auth.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            role="user",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Account created. Welcome to Lost and Found!", "success")
        return redirect(url_for("main.index"))

    return render_template("register.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=request.form.get("remember"))
            next_url = request.args.get("next")
            # Prevent open redirect attacks: only allow same-origin relative paths
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            flash("Logged in successfully.", "success")
            return redirect(url_for("main.index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
