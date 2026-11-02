from .db import db
from datetime import datetime


# =====================================================
# MASTER PART
# =====================================================

class Part(db.Model):

    __tablename__ = "part"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    line = db.Column(
        db.String(50),
        nullable=False
    )

    model = db.Column(
        db.String(50),
        nullable=False
    )

    part_number = db.Column(
        db.String(50),
        nullable=False
    )

    # SKU komponen/BOM; boleh kosong untuk data lama.
    sku = db.Column(db.String(100), nullable=True, index=True)

    # Kebutuhan part ini untuk satu unit FG (BOM).
    qty_child = db.Column(db.Integer, nullable=False, default=1)

    part_name = db.Column(
        db.String(150),
        nullable=False
    )

    return_location = db.Column(
        db.String(100),
        nullable=True
    )

    # =================================================
    # HARGA PART
    # =================================================

    price = db.Column(
        db.Numeric(15, 2),
        nullable=True,
        default=0
    )

    # =================================================
    # FOTO PART
    # =================================================

    photo = db.Column(
        db.String(255),
        nullable=True
    )

    # =================================================
    # UNIQUE PART
    #
    # Part number boleh sama jika:
    # line/model berbeda.
    # =================================================

    __table_args__ = (
        db.UniqueConstraint(
            "line",
            "model",
            "part_number",
            name="uq_part_line_model_number"
        ),
    )


# =====================================================
# MASTER KLASIFIKASI NG / REMARK
# =====================================================

class NgClassification(db.Model):

    __tablename__ = "ng_classification"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )


# =====================================================
# MASTER JENIS NG
# =====================================================

class NgType(db.Model):

    __tablename__ = "ng_type"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )


# =====================================================
# USER / ACCOUNT
# F-6
# =====================================================

class User(db.Model):

    __tablename__ = "user"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    npk = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    nickname = db.Column(
        db.String(50),
        nullable=True
    )

    full_name = db.Column(
        db.String(100),
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        nullable=False,
        default="operator",
        index=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )

    last_login_at = db.Column(
        db.DateTime,
        nullable=True
    )

    devices = db.relationship(
        "UserDevice",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


# =====================================================
# USER DEVICE
# =====================================================

class UserDevice(db.Model):

    __tablename__ = "user_device"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =================================================
    # USER
    # =================================================

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    # =================================================
    # DEVICE TOKEN
    # =================================================

    device_token = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # =================================================
    # DEVICE NAME
    # =================================================

    device_name = db.Column(
        db.String(255),
        nullable=True
    )

    # =================================================
    # USER AGENT
    # =================================================

    user_agent = db.Column(
        db.Text,
        nullable=True
    )

    # =================================================
    # STATUS
    # =================================================

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    # =================================================
    # WAKTU
    # =================================================

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )

    last_seen_at = db.Column(
        db.DateTime,
        default=datetime.now
    )

    # =================================================
    # INDEX
    # =================================================

    __table_args__ = (
        db.Index(
            "ix_user_device_user_active",
            "user_id",
            "is_active"
        ),
    )


# =====================================================
# HEADER CRUSHING TICKET
# =====================================================

class CrushingTicket(db.Model):

    __tablename__ = "crushing_ticket"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =================================================
    # NOMOR TICKET
    # =================================================

    ticket_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    # =================================================
    # INFORMASI PRODUKSI
    # =================================================

    line = db.Column(
        db.String(50),
        nullable=False
    )

    shift = db.Column(
        db.String(10),
        nullable=False
    )

    # =================================================
    # STATUS
    # =================================================

    status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending Pulling",
        index=True
    )

    # =================================================
    # LEADER
    # =================================================

    need_leader_reason = db.Column(
        db.String(255),
        nullable=True
    )

    # =================================================
    # WAKTU
    # =================================================

    created_at = db.Column(
        db.DateTime,
        default=datetime.now,
        index=True
    )

    # =================================================
    # OPERATOR / PEMBUAT TICKET
    # Snapshot identitas account saat ticket dibuat.
    # =================================================

    operator_npk = db.Column(
        db.String(50),
        nullable=True,
        index=True
    )

    operator_name = db.Column(
        db.String(100),
        nullable=True
    )

    # =================================================
    # APPROVAL
    # =================================================

    approved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    approved_by = db.Column(
        db.String(100),
        nullable=True
    )

    # =================================================
    # REMARK / KLASIFIKASI NG
    # =================================================

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    # =================================================
    # MARIS
    # =================================================

    maris_transaction_number = db.Column(
        db.String(100),
        nullable=True
    )

    maris_input_at = db.Column(
        db.DateTime,
        nullable=True
    )

    maris_input_by = db.Column(
        db.String(100),
        nullable=True
    )

    # =================================================
    # RELATIONSHIP TRANSACTION
    # =================================================

    transactions = db.relationship(
        "CrushingTransaction",
        backref="ticket",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # =================================================
    # RELATIONSHIP ACTIVITY
    # =================================================

    activities = db.relationship(
        "ActivityLog",
        backref="ticket",
        lazy=True,
        cascade="all, delete-orphan"
    )


# =====================================================
# DETAIL PART PADA TICKET
# =====================================================

class CrushingTransaction(db.Model):

    __tablename__ = "crushing_transaction"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =================================================
    # TEMP TICKET
    # =================================================

    temp_ticket = db.Column(
        db.String(100),
        nullable=True,
        index=True
    )

    # =================================================
    # TICKET ID
    # =================================================

    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("crushing_ticket.id"),
        nullable=True,
        index=True
    )

    # =================================================
    # INFORMASI PART
    # =================================================

    line = db.Column(
        db.String(50),
        nullable=False
    )

    model = db.Column(
        db.String(100),
        nullable=False
    )

    part_number = db.Column(
        db.String(50),
        nullable=False
    )

    part_name = db.Column(
        db.String(150),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    # =================================================
    # JENIS NG
    # =================================================

    jenis_ng = db.Column(
        db.String(150),
        nullable=True
    )

    # Sumber pemilihan part: bom, manual, atau leader_manual.
    source_type = db.Column(db.String(30), nullable=False, default="manual")

    # =================================================
    # HARGA
    # =================================================

    price = db.Column(
        db.Float,
        nullable=True,
        default=0
    )

    # =================================================
    # SHIFT
    # =================================================

    shift = db.Column(
        db.String(10),
        nullable=False
    )

    # =================================================
    # VALIDASI
    # =================================================

    validation_status = db.Column(
        db.String(20),
        nullable=False,
        default="Waiting"
    )

    validated_at = db.Column(
        db.DateTime,
        nullable=True
    )

    validated_by = db.Column(
        db.String(100),
        nullable=True
    )

    # =================================================
    # WAKTU
    # =================================================

    created_at = db.Column(
        db.DateTime,
        default=datetime.now,
        index=True
    )


# =====================================================
# ACTIVITY LOG
# =====================================================

class ActivityLog(db.Model):

    __tablename__ = "activity_log"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =================================================
    # TICKET
    # =================================================

    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("crushing_ticket.id"),
        nullable=False,
        index=True
    )

    # =================================================
    # ACTOR
    # =================================================

    actor = db.Column(
        db.String(100),
        nullable=False
    )

    # =================================================
    # ACTIVITY
    # =================================================

    activity = db.Column(
        db.Text,
        nullable=False
    )

    # =================================================
    # WAKTU
    # =================================================

    created_at = db.Column(
        db.DateTime,
        default=datetime.now,
        index=True
    )

# =====================================================
# PENUTUPAN PERIODE MARIS (tanpa mengubah tabel lama)
# =====================================================

class MarisClosingPeriod(db.Model):
    __tablename__ = "maris_closing_period"

    id = db.Column(db.Integer, primary_key=True)
    period_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    closed_at = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    closed_by = db.Column(db.String(100), nullable=False)
    ticket_count = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.String(255), nullable=True)


class MarisClosingTicket(db.Model):
    __tablename__ = "maris_closing_ticket"

    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(
        db.Integer, db.ForeignKey("maris_closing_period.id"),
        nullable=False, index=True
    )
    ticket_id = db.Column(
        db.Integer, db.ForeignKey("crushing_ticket.id"),
        nullable=False, unique=True, index=True
    )
    ticket_number_snapshot = db.Column(db.String(50), nullable=False)
    maris_number_snapshot = db.Column(db.String(100), nullable=False)
    amount_snapshot = db.Column(db.Float, nullable=False, default=0)

    period = db.relationship(
        "MarisClosingPeriod", backref=db.backref("closing_tickets", lazy=True)
    )
    ticket = db.relationship("CrushingTicket")
