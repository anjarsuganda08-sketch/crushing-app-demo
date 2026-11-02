from datetime import datetime

from database.db import db
from database.models import (
    CrushingTicket,
    CrushingTransaction,
    ActivityLog
)


# =====================================================
# ACTIVITY LOG
# =====================================================

def add_activity(ticket_id, actor, activity):
    """
    Menambahkan aktivitas ke Activity Log.
    """

    log = ActivityLog(
        ticket_id=ticket_id,
        actor=actor,
        activity=activity,
        created_at=datetime.now()
    )

    db.session.add(log)
    db.session.commit()


# =====================================================
# GET TICKET
# =====================================================

def get_ticket(ticket_number):

    return (
        CrushingTicket.query
        .filter_by(
            ticket_number=ticket_number
        )
        .first()
    )


# =====================================================
# GET DETAIL TICKET
# =====================================================

def get_ticket_items(ticket_id):

    return (
        CrushingTransaction.query
        .filter_by(
            ticket_id=ticket_id
        )
        .all()
    )


# =====================================================
# GET ACTIVITY
# =====================================================

def get_ticket_activity(ticket_id):

    return (
        ActivityLog.query
        .filter_by(
            ticket_id=ticket_id
        )
        .order_by(
            ActivityLog.created_at.asc()
        )
        .all()
    )


# =====================================================
# UPDATE STATUS
# =====================================================

def update_ticket_status(
    ticket,
    status,
    actor
):

    ticket.status = status

    if status == "Approved":
        ticket.approved_at = datetime.now()
        ticket.approved_by = actor

    db.session.commit()

    add_activity(
        ticket.id,
        actor,
        f"Status ticket diubah menjadi '{status}'"
    )


# =====================================================
# EDIT QTY
# =====================================================

def update_qty(
    transaction,
    new_qty,
    actor
):

    old_qty = transaction.quantity

    transaction.quantity = new_qty

    db.session.commit()

    add_activity(
        transaction.ticket_id,
        actor,
        f"Mengubah Qty Part {transaction.part_number} : {old_qty} → {new_qty}"
    )


# =====================================================
# EDIT PART NUMBER
# =====================================================

def update_part_number(
    transaction,
    new_part_number,
    new_part_name,
    actor
):

    old_number = transaction.part_number

    transaction.part_number = new_part_number
    transaction.part_name = new_part_name

    db.session.commit()

    add_activity(
        transaction.ticket_id,
        actor,
        f"Mengubah Part Number {old_number} → {new_part_number}"
    )


# =====================================================
# HAPUS PART
# =====================================================

def delete_transaction(
    transaction,
    actor
):

    ticket_id = transaction.ticket_id

    part = transaction.part_number

    db.session.delete(transaction)
    db.session.commit()

    add_activity(
        ticket_id,
        actor,
        f"Menghapus Part {part}"
    )