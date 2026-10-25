"""WTForms for server-side validation and CSRF protection."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import (
    StringField,
    TextAreaField,
    SelectField,
    DateField,
    PasswordField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    Optional,
    EqualTo,
    ValidationError,
)

from app.models import User

# Format-only email validation: avoids slow DNS lookups and accepts internal
# domains (e.g. *.local) used in self-hosted or offline environments.
EMAIL_VALIDATOR = Email(check_deliverability=False)


class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    email = StringField(
        "Email", validators=[DataRequired(), EMAIL_VALIDATOR, Length(max=120)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Register")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("An account with that email already exists.")


class LoginForm(FlaskForm):
    # Login only authenticates an existing user; we intentionally do NOT re-run
    # the email format/deliverability validator here (the address was validated
    # at registration), so internal accounts like admin@host.local can log in.
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class ItemForm(FlaskForm):
    """Shared form for reporting lost or found items."""

    title = StringField("Item Name", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField(
        "Description", validators=[DataRequired(), Length(max=2000)]
    )
    category = SelectField(
        "Category",
        choices=[
            ("ID Card", "ID Card"),
            ("Wallet", "Wallet"),
            ("Book/Notebook", "Book/Notebook"),
            ("Bag", "Bag"),
            ("Mobile/Electronics", "Mobile/Electronics"),
            ("Keys", "Keys"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()],
    )
    incident_date = DateField("Date", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired(), Length(max=200)])
    contact = StringField(
        "Contact Information",
        validators=[DataRequired(), Length(max=200)],
        description="Email or phone number where you can be reached.",
    )
    contact = StringField(
        "Contact Information",
        validators=[DataRequired(), Length(max=200)],
        description="Email or phone number where you can be reached.",
    )
    image = FileField(
        "Item Image (optional)",
        validators=[
            Optional(),
            FileAllowed(
                ["png", "jpg", "jpeg", "gif", "webp"],
                "Only image files (PNG, JPG, GIF, WEBP) are allowed.",
            ),
        ],
    )
    submit = SubmitField("Submit Report")


class ClaimForm(FlaskForm):
    message = TextAreaField(
        "Why is this yours?",
        validators=[DataRequired(), Length(min=10, max=1000)],
        description="Describe identifying details only the owner would know.",
    )
    submit = SubmitField("Submit Claim")
