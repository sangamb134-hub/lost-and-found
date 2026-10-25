"""Full end-to-end flow over real HTTP against the running dev server.

Verifies that forms connect to the backend end-to-end: register, login,
report a lost item (with CSRF token + image), and confirm it appears in browse
and the public API. Requires the dev server running at http://127.0.0.1:5000.

Run:  python -m tests.test_http_flow
"""
import http.client
import io
import re
import sys
from urllib.parse import urlencode, quote

HOST, PORT = "127.0.0.1", 5000
BASE = f"http://{HOST}:{PORT}"


class Session:
    def __init__(self):
        self.cookie = ""
        self.conn = http.client.HTTPConnection(HOST, PORT)

    def _req(self, method, path, body=None, headers=None, form=False):
        hdrs = {"Host": f"{HOST}:{PORT}"}
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        if form and body is not None:
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
            body = urlencode(body)
            hdrs["Content-Length"] = str(len(body))
        if headers:
            hdrs.update(headers)
        self.conn.request(method, path, body=body, headers=hdrs)
        resp = self.conn.getresponse()
        data = resp.read().decode("utf-8", "replace")
        set_cookie = resp.getheader("Set-Cookie")
        if set_cookie:
            self.cookie = set_cookie.split(";")[0]
        return resp.status, resp.getheader("Location"), data

    def get(self, path):
        return self._req("GET", path)

    def post(self, path, fields, form=True):
        return self._req("POST", path, body=fields, form=form)

    def post_multipart(self, path, fields, file_field=None, filename=None, data=b""):
        boundary = "----lfboundary123"
        parts = []
        for k, v in fields.items():
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
            )
        if file_field:
            file_header = (
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="{file_field}"; filename="{filename}"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            )
            body = "".join(parts).encode() + file_header.encode() + data + f"\r\n--{boundary}--\r\n".encode()
        else:
            body = ("".join(parts) + f"--{boundary}--\r\n").encode()
        hdrs = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "Cookie": self.cookie,
        }
        self.conn.request("POST", path, body=body, headers=hdrs)
        resp = self.conn.getresponse()
        d = resp.read().decode("utf-8", "replace")
        sc = resp.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        return resp.status, resp.getheader("Location"), d


def csrf_token(html):
    # Flask-WTF renders: name="csrf_token" type="hidden" value="..."
    m = re.search(r'name="csrf_token"\s+(?:type="hidden"\s+)?value="([^"]+)"', html)
    return m.group(1) if m else ""


def main():
    s = Session()
    failures = []

    def check(name, cond, detail=""):
        st = "PASS" if cond else "FAIL"
        print(f"  [{st}] {name}" + (f"  -- {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    print("Live HTTP end-to-end flow:")
    # Home
    st, _, html = s.get("/")
    check("GET / -> 200", st == 200, f"got {st}")
    check("hero text present", "Let's Find It" in html)

    # Register a new user
    st, _, html = s.get("/auth/register")
    token = csrf_token(html)
    check("register page has csrf token", bool(token))
    email = "liveuser@test.edu"
    st, loc, html = s.post("/auth/register", {
        "csrf_token": token, "name": "Live User", "email": email,
        "password": "password123", "confirm_password": "password123",
    })
    check("register redirects (302)", st == 302, f"got {st}")
    # follow to home (logged in)
    if loc:
        st, _, _ = s.get(loc)
        check("after register, home reachable", st == 200)

    # Report a lost item WITH an image (multipart)
    st, _, html = s.get("/report/lost")
    token = csrf_token(html)
    check("report lost page has csrf token", bool(token))
    from PIL import Image
    img_buf = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 100, 50)).save(img_buf, "PNG")
    png_bytes = img_buf.getvalue()
    st, loc, html = s.post_multipart(
        "/report/lost",
        {
            "csrf_token": token,
            "title": "Live Test Wallet",
            "description": "Brown leather wallet lost in the science block.",
            "category": "Wallet",
            "incident_date": "2026-10-25",
            "location": "Science Block",
            "contact": email,
        },
        file_field="image", filename="wallet.png", data=png_bytes,
    )
    check("report lost -> 302 redirect", st == 302, f"got {st}")
    if loc:
        st, _, html = s.get(loc)
        check("item details page renders after report", st == 200 and "Live Test Wallet" in html)

    # Browse should show the new item
    st, _, html = s.get("/browse?type=lost")
    check("browse shows new lost item", "Live Test Wallet" in html)

    # Public API should include it
    st, _, body = s.get("/api/items?type=lost")
    check("API lists new lost item", "Live Test Wallet" in body)

    # Logout
    st, loc, _ = s.get("/auth/logout")
    check("logout -> 302", st == 302, f"got {st}")

    # Dashboard now requires login
    st, loc, _ = s.get("/dashboard")
    check("dashboard redirected when logged out", st == 302 and "login" in (loc or ""), f"got {st} {loc}")

    print("\n" + "=" * 50)
    if failures:
        print(f"FAILED: {len(failures)}: {failures}")
        return 1
    print("ALL LIVE-HTTP CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
