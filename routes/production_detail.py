from flask import (
    Blueprint,
    render_template
)

from routes.auth import login_required

from database.models import (
    CrushingTicket,
    CrushingTransaction
)


# ==========================================================
# BLUEPRINT
# ==========================================================

production_detail_bp = Blueprint(
    "production_detail",
    __name__
)


# ==========================================================
# DETAIL CRUSHING TICKET
# ==========================================================

@production_detail_bp.route(
    "/production-ticket/<ticket_number>"
)
@login_required
def production_ticket_detail(ticket_number):

    # ======================================================
    # CARI TICKET
    # ======================================================

    ticket = (
        CrushingTicket.query
        .filter_by(
            ticket_number=ticket_number
        )
        .first()
    )


    # ======================================================
    # TICKET TIDAK DITEMUKAN
    # ======================================================

    if not ticket:

        return (
            "Ticket tidak ditemukan.",
            404
        )


    # ======================================================
    # AMBIL DETAIL TRANSAKSI
    # ======================================================

    items = (
        CrushingTransaction.query
        .filter_by(
            ticket_id=ticket.id
        )
        .order_by(
            CrushingTransaction.id
        )
        .all()
    )


    # ======================================================
    # HISTORI TICKET LINE
    # ======================================================

    histories = (
        CrushingTicket.query
        .filter(
            CrushingTicket.line == ticket.line,
            CrushingTicket.id != ticket.id
        )
        .order_by(
            CrushingTicket.created_at.desc()
        )
        .limit(10)
        .all()
    )


    # ======================================================
    # HITUNG TOTAL QTY
    # ======================================================

    total_quantity = sum(
        item.quantity or 0
        for item in items
    )


    # ======================================================
    # HITUNG TOTAL NILAI
    # ======================================================

    total_value = sum(
        (
            float(item.price or 0)
            *
            int(item.quantity or 0)
        )
        for item in items
    )


    # ======================================================
    # STATUS MARIS
    # ======================================================

    if ticket.maris_transaction_number:

        maris_status = (
            "MARIS Completed"
        )

    else:

        maris_status = (
            "Menunggu Input MARIS"
        )


    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "production_ticket_detail.html",

        ticket=ticket,

        items=items,

        histories=histories,

        total_quantity=total_quantity,

        total_value=total_value,

        maris_status=maris_status

    )