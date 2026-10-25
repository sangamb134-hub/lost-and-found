"""End-to-end smoke test for the Lost and Found app using Flask's test client.

Run with:  python -m tests.test_app   (from the project root, venv active)
This is a manual integration check, not a pytest suite — it exercises the real
routes (templates + API) the way a browser would.
"""
import io
import os
import sys
import tempfile

# Ensure project root is importable when run as a script
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Item, Claim


def main():
    os.environ["FLASK_ENV"] = "testing"

    # Use a temp-file SQLite DB so all connections share the same state
    # (in-memory SQLite is per-connection, which breaks cross-request checks).
    tmp_db = tempfile.mktemp(suffix="_lf_test.db")

    class FileTestConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_db}"
        SQLALCHEMY_ENGINE_OPTIONS = {}

    app = create_app(FileTestConfig)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["LOGIN_DISABLED"] = False

    failures = []

    def check(name, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    with app.app_context():
        db.drop_all()
        db.create_all()
        # Seed the default admin (create_app does this, but we dropped the tables)
        admin = User(name="Administrator", email="admin@lostfound.local", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

    with app.test_client() as client:
        print("Public pages:")
        for path, label in [
            ("/", "home"),
            ("/browse", "browse"),
            ("/auth/login", "login page"),
            ("/auth/register", "register page"),
        ]:
            r = client.get(path)
            check(f"GET {path} -> 200", r.status_code == 200, f"got {r.status_code}")

        print("\nRegistration:")
        r = client.post(
            "/auth/register",
            data={
                "name": "Test Student",
                "email": "student@test.edu",
                "password": "supersecret",
                "confirm_password": "supersecret",
            },
            follow_redirects=True,
        )
        check("register redirects with success", r.status_code == 200)

        print("\nLogout then login:")
        client.get("/auth/logout")
        r = client.post(
            "/auth/login",
            data={"email": "student@test.edu", "password": "supersecret"},
            follow_redirects=True,
        )
        check("login success", r.status_code == 200)

        print("\nWrong password rejected:")
        client.get("/auth/logout")
        r = client.post(
            "/auth/login",
            data={"email": "student@test.edu", "password": "wrongpass"},
        )
        check("login failure returns 200 (re-renders)", r.status_code == 200)

        # Re-login for the rest of the flow
        client.post(
            "/auth/login",
            data={"email": "student@test.edu", "password": "supersecret"},
        )

        # Re-login
        client.post(
            "/auth/login",
            data={"email": "student@test.edu", "password": "supersecret"},
        )

        print("\nReport lost item:")
        r = client.post(
            "/report/lost",
            data={
                "title": "Black leather wallet",
                "description": "Lost near the library, contains student ID.",
                "category": "Wallet",
                "incident_date": "2026-10-20",
                "location": "Central Library",
                "contact": "student@test.edu",
            },
            follow_redirects=True,
        )
        check("report lost -> 200", r.status_code == 200)
        with app.app_context():
            item = Item.query.filter_by(title="Black leather wallet").first()
            check("lost item saved to DB", item is not None)
            lost_id = item.id if item else None
            check("item_type == lost", item and item.item_type == "lost")

        print("\nReport found item:")
        r = client.post(
            "/report/found",
            data={
                "title": "Blue notebook",
                "description": "Found in cafeteria, name written inside.",
                "category": "Book/Notebook",
                "incident_date": "2026-10-21",
                "location": "Cafeteria",
                "contact": "student@test.edu",
            },
            follow_redirects=True,
        )
        check("report found -> 200", r.status_code == 200)
        with app.app_context():
            found = Item.query.filter_by(title="Blue notebook").first()
            found_id = found.id if found else None
            check("found item saved to DB", found is not None)

        print("\nBrowse filters:")
        r = client.get("/browse?type=lost")
        check("browse lost returns 200", r.status_code == 200)
        check("browse shows lost item", b"Black leather wallet" in r.data)
        r = client.get("/browse?type=found")
        check("browse shows found item", b"Blue notebook" in r.data)

        print("\nItem details page:")
        r = client.get(f"/item/{lost_id}")
        check("item details -> 200", r.status_code == 200)

        print("\nImage upload (invalid type rejected):")
        r = client.post(
            "/report/lost",
            data={
                "title": "Test with bad file",
                "description": "Trying to upload an executable.",
                "category": "Keys",
                "incident_date": "2026-10-22",
                "location": "Gym",
                "contact": "student@test.edu",
                "image": (io.BytesIO(b"MZbinary"), "malware.exe"),
            },
            content_type="multipart/form-data",
        )
        check("invalid image type rejected (re-renders)", r.status_code == 200)
        with app.app_context():
            bad = Item.query.filter_by(title="Test with bad file").first()
            check("bad upload NOT saved", bad is None)

        print("\nValid image upload:")
        # Generate a valid PNG using Pillow
        from PIL import Image as PILImage
        buf = io.BytesIO()
        PILImage.new("RGB", (50, 50), color=(70, 130, 180)).save(buf, format="PNG")
        buf.seek(0)
        r = client.post(
            "/report/lost",
            data={
                "title": "Lost phone",
                "description": "Black Samsung phone with cracked screen.",
                "category": "Mobile/Electronics",
                "incident_date": "2026-10-23",
                "location": "Parking Lot B",
                "contact": "student@test.edu",
                "image": (buf, "phone.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        check("valid image upload -> 200", r.status_code == 200)
        with app.app_context():
            phone = Item.query.filter_by(title="Lost phone").first()
            check("item with image saved", phone is not None)
            check("image filename stored", phone and bool(phone.image_filename))

        print("\nSubmit a claim:")
        # Create a second user to submit a claim on the first item
        with app.app_context():
            other = User(name="Other User", email="other@test.edu", role="user")
            other.set_password("anotherpass")
            db.session.add(other)
            db.session.commit()
            first_item = Item.query.filter_by(title="Black leather wallet").first()
            claim_item_id = first_item.id

        # Logout, login as other user, submit claim
        client.get("/auth/logout")
        client.post(
            "/auth/login",
            data={"email": "other@test.edu", "password": "anotherpass"},
        )
        r = client.post(
            f"/item/{claim_item_id}/claim",
            data={"message": "The wallet has my student ID inside, name on the card is mine."},
            follow_redirects=True,
        )
        check("claim submission -> 200", r.status_code == 200)
        with app.app_context():
            claim = Claim.query.filter_by(item_id=claim_item_id).first()
            check("claim saved to DB", claim is not None)
            claim_id = claim.id if claim else None

        print("\nOwner approves claim (item marked returned):")
        # Login as original owner
        client.get("/auth/logout")
        client.post(
            "/auth/login",
            data={"email": "student@test.edu", "password": "supersecret"},
        )
        r = client.post(
            f"/claim/{claim_id}/approve",
            follow_redirects=True,
        )
        check("claim approval -> 200", r.status_code == 200)
        with app.app_context():
            c = db.session.get(Claim, claim_id)
            it = db.session.get(Item, claim_item_id)
            check("claim status approved", c and c.status == "approved")
            check("item status returned", it and it.status == "returned")

        print("\nDashboard:")
        r = client.get("/dashboard")
        check("user dashboard -> 200", r.status_code == 200)

        print("\nAdmin access:")
        # Regular user denied admin dashboard
        r = client.get("/admin/dashboard")
        check("regular user denied admin (403)", r.status_code == 403)

        # Login as admin
        client.get("/auth/logout")
        client.post(
            "/auth/login",
            data={"email": "admin@lostfound.local", "password": "admin123"},
        )
        r = client.get("/admin/dashboard")
        check("admin dashboard -> 200", r.status_code == 200)

        print("\nREST API:")
        r = client.get("/api/stats")
        check("/api/stats -> 200", r.status_code == 200)
        check("stats has total_lost", b"total_lost" in r.data)

        r = client.get("/api/items")
        check("/api/items -> 200", r.status_code == 200)

        r = client.get(f"/api/items/{lost_id}" if lost_id else "/api/items/1")
        check("/api/items/<id> -> 200", r.status_code == 200)

        # Create item via API
        r = client.post(
            "/api/items",
            json={
                "title": "API Item",
                "description": "Created via REST API",
                "category": "Keys",
                "item_type": "lost",
                "location": "Lab 101",
                "incident_date": "2026-10-24",
            },
        )
        check("POST /api/items -> 201", r.status_code == 201, f"got {r.status_code}")

        # Missing fields
        r = client.post("/api/items", json={"title": "Incomplete"})
        check("POST /api/items missing fields -> 400", r.status_code == 400)

        # Unauthorized access (logout then try API create)
        client.get("/auth/logout")
        r = client.post("/api/items", json={
            "title": "x", "description": "x", "category": "Keys",
            "item_type": "lost", "location": "x", "incident_date": "2026-10-24",
        })
        check("API create without auth -> 302 (redirect to login)", r.status_code == 302)

    print("\n" + "=" * 50)
    if failures:
        print(f"FAILED: {len(failures)} check(s): {failures}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
