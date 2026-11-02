# ============================================================
# DASHBOARD
# CRUSHING APP
# ============================================================

from flask import Blueprint, render_template
from sqlalchemy import func
from datetime import datetime, timedelta

from database.db import db
from database.models import (
    CrushingTicket,
    CrushingTransaction,
    MarisClosingPeriod,
    MarisClosingTicket
)

from routes.auth import login_required


# ============================================================
# BLUEPRINT
# ============================================================

dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


# ============================================================
# DASHBOARD
# ============================================================

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():

    # ========================================================
    # SNAPSHOT ANTREAN PENUTUPAN MARIS (LINTAS TANGGAL)
    # ========================================================
    unclosed_maris_tickets = (
        CrushingTicket.query
        .filter(
            CrushingTicket.status == "MARIS Completed",
            CrushingTicket.maris_transaction_number.isnot(None),
            ~CrushingTicket.id.in_(db.session.query(MarisClosingTicket.ticket_id))
        )
        .count()
    )

    unclosed_maris_amount = (
        db.session.query(
            func.coalesce(func.sum(CrushingTransaction.price * CrushingTransaction.quantity), 0)
        )
        .join(CrushingTicket, CrushingTransaction.ticket_id == CrushingTicket.id)
        .filter(
            CrushingTicket.status == "MARIS Completed",
            CrushingTicket.maris_transaction_number.isnot(None),
            ~CrushingTicket.id.in_(db.session.query(MarisClosingTicket.ticket_id))
        )
        .scalar()
        or 0
    )

    latest_closing_period = (
        MarisClosingPeriod.query
        .order_by(MarisClosingPeriod.closed_at.desc(), MarisClosingPeriod.id.desc())
        .first()
    )
    latest_closed_amount = float(latest_closing_period.total_amount or 0) if latest_closing_period else 0
    latest_closed_count = int(latest_closing_period.ticket_count or 0) if latest_closing_period else 0

    # ========================================================
    # CUTOFF DATA HARI INI (KPI OPERASIONAL LAMA DIPERTAHANKAN)
    # ========================================================
    today = datetime.now().date()
    start_today = datetime.combine(today, datetime.min.time())
    tomorrow = start_today + timedelta(days=1)

    today_filter = (
        CrushingTicket.created_at >= start_today,
        CrushingTicket.created_at < tomorrow
    )

    # ========================================================
    # TOTAL TICKET
    # ========================================================

    total_ticket = (
        CrushingTicket.query.filter(*today_filter).count()
    )


    # ========================================================
    # STATUS COUNT
    # ========================================================

    pending_count = (
        CrushingTicket.query
        .filter(*today_filter)
        .filter(
            CrushingTicket.status
            == "Pending Pulling"
        )
        .count()
    )


    leader_count = (
        CrushingTicket.query
        .filter(*today_filter)
        .filter(
            CrushingTicket.status
            == "Need Leader Confirmation"
        )
        .count()
    )


    approved_count = (
        CrushingTicket.query
        .filter(*today_filter)
        .filter(
            CrushingTicket.status
            == "Approved"
        )
        .count()
    )


    maris_completed_count = (
        CrushingTicket.query
        .filter(*today_filter)
        .filter(
            CrushingTicket.status
            == "MARIS Completed"
        )
        .count()
    )


    # ========================================================
    # ACTIVE TICKET
    # ========================================================

    active_tickets = (
        CrushingTicket.query
        .filter(*today_filter)
        .filter(
            CrushingTicket.status
            != "MARIS Completed"
        )
        .order_by(
            CrushingTicket.created_at.asc()
        )
        .limit(8)
        .all()
    )


    active_ticket_count = (
        CrushingTicket.query
        .filter(*today_filter)
        .filter(
            CrushingTicket.status
            != "MARIS Completed"
        )
        .count()
    )


    # ========================================================
    # RECENT TICKETS
    # ========================================================

    recent_tickets = (
        CrushingTicket.query
        .filter(*today_filter)
        .order_by(
            CrushingTicket.created_at.desc()
        )
        .limit(8)
        .all()
    )


    # ========================================================
    # TOTAL QTY
    # ========================================================

    total_qty = (
        db.session.query(
            func.sum(
                CrushingTransaction.quantity
            )
        )
        .join(
            CrushingTicket,
            CrushingTransaction.ticket_id == CrushingTicket.id
        )
        .filter(*today_filter)
        .scalar()
        or 0
    )


    # ========================================================
    # TOTAL VALUE
    # ========================================================

    total_value = (
        db.session.query(
            func.sum(
                CrushingTransaction.price
                *
                CrushingTransaction.quantity
            )
        )
        .join(
            CrushingTicket,
            CrushingTransaction.ticket_id == CrushingTicket.id
        )
        .filter(*today_filter)
        .scalar()
        or 0
    )


    # ========================================================
    # COMPLETION PERCENTAGE
    # ========================================================

    if total_ticket > 0:

        completion_percentage = (
            maris_completed_count
            /
            total_ticket
            *
            100
        )

    else:

        completion_percentage = 0


    # ========================================================
    # GRAFIK TICKET PER LINE
    # ========================================================

    line_data = (
        db.session.query(
            CrushingTicket.line,
            func.count(
                CrushingTicket.id
            ).label(
                "total_ticket"
            )
        )
        .filter(*today_filter)
        .filter(
            CrushingTicket.line.isnot(None)
        )
        .group_by(
            CrushingTicket.line
        )
        .order_by(
            func.count(
                CrushingTicket.id
            ).desc()
        )
        .all()
    )


    line_chart_labels = [
        row.line
        for row in line_data
    ]


    line_chart_values = [
        int(
            row.total_ticket
            or 0
        )
        for row in line_data
    ]


    # ========================================================
    # GRAFIK DISTRIBUSI STATUS
    # ========================================================

    status_chart_labels = [

        "Pending Pulling",

        "Need Leader Confirmation",

        "Approved",

        "MARIS Completed"

    ]


    status_chart_values = [

        pending_count,

        leader_count,

        approved_count,

        maris_completed_count

    ]


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(

        "dashboard.html",

        total_ticket=total_ticket,

        pending_count=pending_count,

        leader_count=leader_count,

        approved_count=approved_count,

        maris_completed_count=
            maris_completed_count,

        total_qty=int(
            total_qty
        ),

        total_value=float(
            total_value
        ),

        active_ticket_count=
            active_ticket_count,

        completion_percentage=
            completion_percentage,

        active_tickets=
            active_tickets,

        recent_tickets=
            recent_tickets,

        line_chart_labels=
            line_chart_labels,

        line_chart_values=
            line_chart_values,

        status_chart_labels=
            status_chart_labels,

        status_chart_values=
            status_chart_values,

        unclosed_maris_tickets=int(unclosed_maris_tickets),
        unclosed_maris_amount=float(unclosed_maris_amount),
        latest_closing_period=latest_closing_period,
        latest_closed_amount=latest_closed_amount,
        latest_closed_count=latest_closed_count

    )