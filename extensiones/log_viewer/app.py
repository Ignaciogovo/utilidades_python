import hmac
import os
import secrets
from datetime import date

from flask import Flask, abort, redirect, render_template, request, session, url_for

from log_reader import read_logs


def _required(name, minimum=1):
    value = os.environ.get(name, "")
    if len(value) < minimum:
        raise RuntimeError(f"Configura {name} con al menos {minimum} caracteres")
    return value


SECRET_KEY = _required("SECRET_KEY", 32)
ADMIN_USERNAME = _required("ADMIN_USERNAME")
ADMIN_PASSWORD = _required("ADMIN_PASSWORD", 12)
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "true").lower() in {"1", "true", "yes"},
    MAX_CONTENT_LENGTH=4096,
)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _valid_csrf():
    expected = session.get("csrf", "").encode()
    provided = request.form.get("csrf_token", "").encode()
    return bool(expected) and hmac.compare_digest(expected, provided)


@app.context_processor
def _template_globals():
    return {"csrf_token": csrf_token, "theme": session.get("theme", "retro")}


@app.before_request
def _require_login():
    theme = request.args.get("theme")
    if theme in {"classic", "retro"}:
        session["theme"] = theme
    if request.endpoint in {"login", "static"}:
        return None
    if not session.get("authenticated"):
        return redirect(url_for("login", next=request.full_path))
    return None


@app.after_request
def _security_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    next_url = request.values.get("next", "")
    if request.method == "POST":
        if not _valid_csrf():
            abort(400)
        username = request.form.get("username", "").encode()
        password = request.form.get("password", "").encode()
        if hmac.compare_digest(username, ADMIN_USERNAME.encode()) and hmac.compare_digest(password, ADMIN_PASSWORD.encode()):
            session.clear()
            session["authenticated"] = True
            session["csrf"] = secrets.token_urlsafe(32)
            if next_url.startswith("/") and not next_url.startswith("//") and "\\" not in next_url:
                return redirect(next_url)
            return redirect(url_for("index"))
        error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error, next_url=next_url)


@app.post("/logout")
def logout():
    if not _valid_csrf():
        abort(400)
    session.clear()
    return redirect(url_for("login"))


def _date_filter(name):
    value = request.args.get(name, "")
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


@app.get("/")
def index():
    level = request.args.get("level", "").upper()
    if level not in {"", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "RAW"}:
        level = ""
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1
    query = request.args.get("q", "")[:200]
    project = request.args.get("project", "")
    date_from, date_to = _date_filter("from"), _date_filter("to")
    data = read_logs(
        os.environ.get("LOGS_DIR", "/logs"),
        project=project or None,
        level=level or None,
        query=query,
        date_from=date_from,
        date_to=date_to,
        page=page,
    )
    filters = {
        "project": project,
        "level": level,
        "q": query,
        "from": date_from.isoformat() if date_from else "",
        "to": date_to.isoformat() if date_to else "",
    }
    refresh_url = url_for("index", **filters)
    page = data["page"]
    pages = data["pages"]
    prev_url = url_for("index", **dict(filters, page=page - 1)) if page > 1 else None
    next_url = url_for("index", **dict(filters, page=page + 1)) if page < pages else None
    return render_template("dashboard.html", data=data, filters=filters, refresh_url=refresh_url, prev_url=prev_url, next_url=next_url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
