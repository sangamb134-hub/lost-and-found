# Campus Lost and Found Management System

A full-stack web application where college students, faculty, and security staff can report lost and found items, search listings, and help return belongings to their rightful owners.

## Features

- **Home page** with hero, search bar, recent items, and live statistics
- **Browse items** with filters (lost/found, category, location, date, keyword) and pagination
- **Report Lost / Found items** with image upload, validation, and success/error messages
- **Item details** page with claim functionality
- **User authentication** — registration, login, logout, secure password hashing, sessions
- **User dashboard** — view/edit/delete your reports, track claims on your items, your submitted claims
- **Admin dashboard** — manage all items, approve/reject listings, handle claims, mark returned, view statistics
- **REST API** for items, claims, and statistics (JSON responses)
- **Security** — CSRF protection, password hashing, role-based access control, rate limiting, file-upload validation, private contact info

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| Backend | Python, Flask, Flask REST API |
| Database | PostgreSQL (production) / SQLite (local dev), SQLAlchemy ORM, Flask-Migrate |
| Deployment | Docker, Docker Compose, Render |

## Project Structure

```
lost and found/
├── app/
│   ├── __init__.py          # App factory + extension init
│   ├── config.py            # Environment-based configuration
│   ├── extensions.py        # db, login, csrf, limiter instances
│   ├── models.py            # User, Item, Claim models
│   ├── forms.py             # WTForms with validation
│   ├── auth/                # Authentication blueprint
│   ├── items/               # Report/edit/delete blueprint + API
│   ├── claims/              # Claim request blueprint + API
│   ├── admin/               # Admin blueprint
│   ├── main/                # Home, browse, dashboard, public API
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, uploads
├── run.py                   # Dev entry point
├── wsgi.py                  # Production WSGI entry point (gunicorn)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── render.yaml
```

## Local Development

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your SECRET_KEY and DATABASE_URL

# 4. Run the app
flask run   # or: python run.py
```

The app runs at `http://localhost:5000`.

### Default Admin Account
A default admin is created on first run:
- Email: `admin@lostfound.local`
- Password: `admin123`

Override these with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables in production.

## Database Migrations (Flask-Migrate)

The app creates tables automatically on first run via `db.create_all()`. For schema changes, use Flask-Migrate:

```bash
flask db init        # one-time only (already scaffolded)
flask db migrate -m "describe change"
flask db upgrade     # apply migration
```

## Docker

```bash
# Build and run with PostgreSQL locally
docker-compose up --build
# App at http://localhost:5000
```

## Deploy to Render

1. Push this repo to GitHub.
2. Create a new Blueprint deployment on Render and point it to this repo (uses `render.yaml`).
3. Render creates a PostgreSQL database and the web service automatically.
4. Set the `SECRET_KEY` environment variable in the Render dashboard (uncheck "sync" so you can enter a long random value).

## REST API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/stats` | Item statistics | No |
| GET | `/api/items` | List/search items (filters: type, q, category, page) | No |
| GET | `/api/items/<id>` | Item details | No |
| POST | `/api/items` | Create item | Yes |
| PUT | `/api/items/<id>` | Update item (owner/admin) | Yes |
| DELETE | `/api/items/<id>` | Delete item (owner/admin) | Yes |
| POST | `/api/items/<id>/claims` | Submit a claim | Yes |
| PUT | `/api/claims/<id>` | Approve/reject a claim (owner/admin) | Yes |

## Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash`.
- CSRF protection is enabled on all forms via Flask-WTF.
- Rate limiting on registration and login (Flask-Limiter).
- Image uploads are validated by extension, size (max 5 MB), and processed with Pillow.
- Contact information is private and shared only when a claim is approved.
- Admin routes are restricted to users with `role = admin`.

## License

This project is provided for educational use.
