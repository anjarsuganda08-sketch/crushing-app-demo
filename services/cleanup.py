from datetime import datetime, timedelta

from database.db import db
from database.models import CrushingTicket


def cleanup_old_approved_tickets():

    # =====================================
    # BATAS WAKTU
    # =====================================

    batas_waktu = (
        datetime.now()
        - timedelta(hours=24)
    )


    # =====================================
    # CARI TICKET APPROVED
    # YANG SUDAH LEBIH DARI 24 JAM
    # =====================================

    tickets = (
        CrushingTicket.query
        .filter(
            CrushingTicket.status == "Approved",
            CrushingTicket.approved_at.isnot(None),
            CrushingTicket.approved_at <= batas_waktu
        )
        .all()
    )


    # =====================================
    # JIKA TIDAK ADA DATA
    # =====================================

    if not tickets:

        return 0


    try:

        jumlah_ticket = len(tickets)


        # =================================
        # HAPUS TICKET
        # =================================

        # Relasi transactions dan activities
        # akan ikut terhapus karena cascade

        for ticket in tickets:

            db.session.delete(ticket)


        # =================================
        # SIMPAN PERUBAHAN
        # =================================

        db.session.commit()


        return jumlah_ticket


    except Exception as error:

        db.session.rollback()

        print(
            "ERROR AUTO CLEANUP:",
            str(error)
        )

        return 0