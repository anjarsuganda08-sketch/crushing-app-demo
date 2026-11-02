from flask import Flask, render_template, redirect, url_for, request, jsonify
from sqlalchemy import inspect, text
import os
import secrets
from flask import session, abort
from werkzeug.security import generate_password_hash

from datetime import datetime, timedelta

from database.db import db
from database.models import (
    Part,
    CrushingTicket,
    CrushingTransaction,
    ActivityLog
)

# ==================================================
# BLUEPRINT
# ==================================================

from routes.production import production_bp
from routes.production_detail import production_detail_bp
from routes.monitoring import monitoring_bp
from routes.detailticket import detailticket_bp
from routes.pulling import pulling_bp
from routes.upload_photo import upload_photo_bp
from routes.import_master import import_master_bp
from routes.admin_maris import admin_maris_bp  
from export_crushing import export_crushing_bp 
from routes.dashboard import dashboard_bp
from routes.auth import auth_bp
from routes.import_members import import_members_bp
from routes.auth import get_current_user, role_required


app = Flask(__name__)

# ==================================================
# CONFIG
# ==================================================

app.secret_key = os.environ.get("CRUSHING_SECRET_KEY") or secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RENDER", "").lower() == "true" or os.environ.get("HTTPS_ONLY", "").lower() == "true"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ==================================================
# AUTO CLEANUP APPROVED TICKET
# ==================================================
def cleanup_old_approved_tickets():
    """Tidak menghapus tiket Approved otomatis; tiket harus tetap terlacak."""
    return None


@app.before_request
def enforce_public_demo_scope():
    """Batasi akun publik demo ke alur transaksi produksi saja.

    Semua perubahan data oleh akun demo hanya boleh melalui POST /production,
    yang menangani tambah part dan penyelesaian ticket. Endpoint mutasi lain
    tetap ditolak, termasuk impor, administrasi, unggah foto, dan perubahan role.
    Database aplikasi demo harus tetap terpisah dari database operasional.
    """
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None

    user = get_current_user()
    if not user:
        return None

    username = str(getattr(user, "username", "") or "").strip().lower()
    if username == "public_demo_operator":
        # Izinkan alur transaksi demo: Production, Pulling, konfirmasi Leader, dan MARIS.
        # Endpoint impor/pengelolaan akun tetap tidak dapat mengubah data melalui akun publik.
        workflow_prefixes = ("/production", "/pulling", "/monitoring", "/need-leader", "/detail-ticket", "/detailticket", "/leader", "/admin-maris", "/maris")
        if request.path == "/production" or request.path.startswith(workflow_prefixes):
            return None
        abort(403, description="Akun Demo hanya boleh mengubah data melalui alur transaksi demo.")

    if str(getattr(user, "role", "")).strip().lower() == "viewer":
        abort(403, description="Akun Viewer hanya memiliki akses baca.")

# ==================================================
# REGISTER BLUEPRINT
# ==================================================

app.register_blueprint(production_bp)
app.register_blueprint(production_detail_bp)
app.register_blueprint(monitoring_bp)
app.register_blueprint(detailticket_bp)
app.register_blueprint(pulling_bp)
app.register_blueprint(upload_photo_bp)
app.register_blueprint(import_master_bp)
app.register_blueprint(admin_maris_bp)
app.register_blueprint(export_crushing_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(import_members_bp)


# ==================================================
# CREATE DATABASE
# ==================================================

with app.app_context():
    db.create_all()

    # ==================================================
    # DATABASE COMPATIBILITY MIGRATION
    # ==================================================
    # db.create_all() tidak menambahkan kolom baru ke tabel
    # yang sudah ada. Kolom operator ditambahkan otomatis
    # agar database trial lama tetap dapat digunakan.
    try:
        inspector = inspect(db.engine)
        ticket_columns = {
            column["name"]
            for column in inspector.get_columns("crushing_ticket")
        }

        if "operator_npk" not in ticket_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE crushing_ticket ADD COLUMN operator_npk VARCHAR(50)")
                )

        if "operator_name" not in ticket_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE crushing_ticket ADD COLUMN operator_name VARCHAR(100)")
                )

        # Kolom tambahan Master Part dan sumber item; aman untuk DB lama.
        part_columns = {column["name"] for column in inspector.get_columns("part")}
        if "sku" not in part_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE part ADD COLUMN sku VARCHAR(100)"))
        if "qty_child" not in part_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE part ADD COLUMN qty_child INTEGER NOT NULL DEFAULT 1"))

        transaction_columns = {column["name"] for column in inspector.get_columns("crushing_transaction")}
        if "source_type" not in transaction_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE crushing_transaction ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'manual'"))
    except Exception as error:
        print("DATABASE MIGRATION WARNING:", error)

    # Seed only fictional demo records. Never copy production database here.
    from database.models import User, NgClassification, NgType
    demo_user = User.query.filter_by(username="public_demo_operator").first()
    if not demo_user:
        demo_user = User(
            npk="DEMO-OPERATOR", username="public_demo_operator",
            nickname="Demo Operator", full_name="Public Demo Operator",
            password_hash=generate_password_hash(secrets.token_urlsafe(32)),
            role="operator", is_active=True
        )
        db.session.add(demo_user)
    else:
        # Akun demo tidak boleh mendapat role admin atau role internal.
        demo_user.role = "operator"
        demo_user.is_active = True
    for label in ["Demo - Internal", "Demo - Supplier"]:
        if not NgClassification.query.filter_by(name=label).first():
            db.session.add(NgClassification(name=label))
    for label in ["Demo - Visual", "Demo - Function"]:
        if not NgType.query.filter_by(name=label).first():
            db.session.add(NgType(name=label))
    from database.models import Part
    demo_parts = [
        ("DEMO-LINE-1", "DEMO-MODEL-A", "DEMO-PART-001", "Demo Component A", "Demo Return Area A", 12500),
        ("DEMO-LINE-1", "DEMO-MODEL-A", "DEMO-PART-002", "Demo Component B", "Demo Return Area B", 18750),
        ("DEMO-LINE-2", "DEMO-MODEL-B", "DEMO-PART-003", "Demo Component C", "Demo Return Area C", 25000),
    ]
    for line, model, part_number, part_name, return_location, demo_price in demo_parts:
        existing_part = Part.query.filter_by(line=line, model=model, part_number=part_number).first()
        if not existing_part:
            db.session.add(Part(line=line, model=model, part_number=part_number, part_name=part_name, return_location=return_location, price=demo_price, qty_child=1))
        else:
            existing_part.price = demo_price
    db.session.commit()

# ==================================================
# HOME
# ==================================================


@app.get("/api/demo-notification-counts")
def demo_notification_counts():
    """Jumlah tiket pada tiga antrean yang ditampilkan di navbar demo."""
    user = get_current_user()
    if not user:
        return jsonify({"pulling": 0, "leader": 0, "maris": 0}), 401

    # Status mengikuti alur aplikasi: Production -> Pulling -> Leader (bila perlu) -> MARIS.
    counts = {
        "pulling": CrushingTicket.query.filter_by(status="Pending Pulling").count(),
        "leader": CrushingTicket.query.filter_by(status="Need Leader Confirmation").count(),
        "maris": CrushingTicket.query.filter_by(status="Approved").count(),
    }
    response = jsonify(counts)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response

@app.route("/")
def home():
    return redirect(url_for("public_demo"))


@app.route("/demo")
def public_demo():
    """Public entry to the sanitized, transaction-enabled portfolio demo."""
    from database.models import User
    user = User.query.filter_by(username="public_demo_operator").first()
    if not user:
        abort(503, description="Akun demo belum siap. Hubungi pemilik demo.")
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    return redirect(url_for("dashboard.dashboard"))

# ==================================================
# MASTER PART
# ==================================================

@app.route("/master-part")
@role_required("admin", "operator", "pulling", "leader", "viewer", "maris")
def master_part():

    parts = (
        Part.query
        .order_by(
            Part.line,
            Part.model,
            Part.part_name
        )
        .all()
    )

    return render_template(
        "master_part.html",
        parts=parts
    )

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
