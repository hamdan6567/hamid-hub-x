from flask import Flask, request, jsonify, session, send_file
from werkzeug.security import check_password_hash
import sqlite3
import os
from functools import wraps

app = Flask(__name__)

# =========================
# SECURITY
# =========================
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

# =========================
# DATABASE
# =========================
DB = "hamid_hub.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT,
            priority TEXT,
            status TEXT DEFAULT 'new',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# ADMIN PROTECTION
# =========================
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 401

        return func(*args, **kwargs)

    return wrapper


# =========================
# WEBSITE
# =========================
@app.route("/")
def home():
    return send_file("index.html")


# =========================
# ADMIN LOGIN
# =========================
@app.post("/api/admin/login")
def admin_login():

    data = request.get_json() or {}
    password = data.get("password", "")

    if not ADMIN_PASSWORD_HASH:
        return jsonify({
            "success": False,
            "error": "ADMIN_PASSWORD_HASH is not configured"
        }), 500

    if check_password_hash(ADMIN_PASSWORD_HASH, password):
        session["admin"] = True

        return jsonify({
            "success": True,
            "message": "Admin login successful"
        })

    return jsonify({
        "success": False,
        "error": "Wrong password"
    }), 401


@app.post("/api/admin/logout")
def admin_logout():
    session.clear()

    return jsonify({
        "success": True
    })


@app.get("/api/admin/check")
def admin_check():
    return jsonify({
        "admin": bool(session.get("admin"))
    })


# =========================
# CREATE TICKET
# =========================
@app.post("/api/tickets")
def create_ticket():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()
    subject = str(data.get("subject", "")).strip()
    message = str(data.get("message", "")).strip()
    category = str(data.get("category", "")).strip()
    priority = str(data.get("priority", "normal")).strip()

    if not name or not subject or not message:
        return jsonify({
            "success": False,
            "error": "Missing information"
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO tickets
        (name, subject, message, category, priority)
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        subject,
        message,
        category,
        priority
    ))

    conn.commit()

    ticket_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "ticket_id": ticket_id
    })


# =========================
# ADMIN: VIEW TICKETS
# =========================
@app.get("/api/admin/tickets")
@admin_required
def admin_tickets():

    conn = get_db()

    tickets = conn.execute("""
        SELECT *
        FROM tickets
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "tickets": [dict(ticket) for ticket in tickets]
    })


# =========================
# ADMIN: CHANGE TICKET STATUS
# =========================
@app.post("/api/admin/tickets/<int:ticket_id>/status")
@admin_required
def update_ticket_status(ticket_id):

    data = request.get_json() or {}
    status = data.get("status", "new")

    allowed = ["new", "processing", "closed"]

    if status not in allowed:
        return jsonify({
            "success": False,
            "error": "Invalid status"
        }), 400

    conn = get_db()

    conn.execute("""
        UPDATE tickets
        SET status = ?
        WHERE id = ?
    """, (status, ticket_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================
# CREATE INQUIRY
# =========================
@app.post("/api/inquiries")
def create_inquiry():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()
    subject = str(data.get("subject", "")).strip()
    message = str(data.get("message", "")).strip()

    if not name or not subject or not message:
        return jsonify({
            "success": False,
            "error": "Missing information"
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO inquiries
        (name, subject, message)
        VALUES (?, ?, ?)
    """, (
        name,
        subject,
        message
    ))

    conn.commit()

    inquiry_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "inquiry_id": inquiry_id
    })


# =========================
# ADMIN: VIEW INQUIRIES
# =========================
@app.get("/api/admin/inquiries")
@admin_required
def admin_inquiries():

    conn = get_db()

    inquiries = conn.execute("""
        SELECT *
        FROM inquiries
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "inquiries": [dict(item) for item in inquiries]
    })


# =========================
# HEALTH CHECK
# =========================
@app.get("/api/status")
def status():

    return jsonify({
        "online": True,
        "security": True,
        "tickets": True,
        "inquiries": True
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
