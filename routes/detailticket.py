from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request
)

from datetime import datetime

from database.db import db

from routes.auth import login_required, role_required

from database.models import (
    CrushingTicket,
    CrushingTransaction,
    Part,
    ActivityLog,
    MarisClosingTicket
)


detailticket_bp = Blueprint(
    "detailticket",
    __name__
)


# =====================================================
# HELPER
# =====================================================

def get_ticket(ticket_number):

    return (
        CrushingTicket.query
        .filter_by(
            ticket_number=ticket_number
        )
        .first()
    )


def get_ticket_items(ticket_id):

    return (
        CrushingTransaction.query
        .filter_by(
            ticket_id=ticket_id
        )
        .order_by(
            CrushingTransaction.id.asc()
        )
        .all()
    )


def attach_part_photo(items):

    for item in items:

        # =====================================
        # CARI PART BERDASARKAN
        # LINE + PART NUMBER
        # =====================================

        part = (

            Part.query

            .filter(
                Part.line == item.line,
                Part.part_number == item.part_number
            )

            .first()

        )


        # =====================================
        # JIKA TIDAK DITEMUKAN,
        # CARI BERDASARKAN PART NUMBER SAJA
        # =====================================

        if not part:

            part = (

                Part.query

                .filter(
                    Part.part_number == item.part_number
                )

                .first()

            )


        # =====================================
        # TENTUKAN NAMA FILE FOTO
        # =====================================

        if part and part.photo:

            item.photo = part.photo

        else:

            # FOTO OTOMATIS:
            # static/part/PARTNUMBER.jpg

            item.photo = (
                f"{item.part_number}.jpg"
            )


# =====================================================
# DETAIL TICKET
# HALAMAN UNTUK PULLING
# =====================================================

@detailticket_bp.route(
    "/ticket/<ticket_number>"
)
@login_required
def detail_ticket(ticket_number):

    ticket = get_ticket(ticket_number)

    if not ticket:

        return "Ticket tidak ditemukan", 404


    items = get_ticket_items(
        ticket.id
    )


    attach_part_photo(items)


    return render_template(
        "ticket_detail.html",
        ticket=ticket,
        items=items
    )


# =====================================================
# DETAIL TICKET
# HALAMAN KHUSUS MONITORING
# =====================================================

@detailticket_bp.route(
    "/monitoring/ticket/<ticket_number>"
)
@login_required
def monitoring_detail(ticket_number):

    ticket = get_ticket(ticket_number)

    if not ticket:

        return (
            "Ticket tidak ditemukan",
            404
        )


    items = get_ticket_items(
        ticket.id
    )


    attach_part_photo(items)


    return render_template(
        "monitoring_detail.html",
        ticket=ticket,
        items=items
    )


# =====================================================
# APPROVE TICKET
# =====================================================

@detailticket_bp.route(
    "/ticket/<ticket_number>/approve"
)
@role_required("pulling", "admin")
def approve_ticket(ticket_number):

    ticket = get_ticket(ticket_number)

    if not ticket:

        return (
            "Ticket tidak ditemukan",
            404
        )


    # =====================================
    # HANYA TICKET PENDING YANG BOLEH
    # DIAPPROVE
    # =====================================

    if ticket.status != "Pending Pulling":

        return (
            "Ticket ini tidak dapat diapprove.",
            400
        )


    try:

        # =================================
        # UBAH STATUS
        # =================================

        ticket.status = "Approved"


        # =================================
        # SIMPAN WAKTU APPROVED
        # =================================

        ticket.approved_at = datetime.now()


        # =================================
        # SIMPAN DATABASE
        # =================================

        db.session.commit()


    except Exception as error:

        db.session.rollback()

        return (
            f"Gagal approve ticket: {str(error)}",
            500
        )


    return redirect(
        url_for(
            "pulling.pulling"
        )
    )


# =====================================================
# NEED LEADER FORM
# =====================================================

@detailticket_bp.route(
    "/need-leader/<ticket_number>",
    methods=["GET", "POST"]
)
@role_required("pulling", "leader", "admin")
def need_leader(ticket_number):

    ticket = get_ticket(ticket_number)

    if not ticket:

        return "Ticket tidak ditemukan", 404


    # =====================================
    # POST
    # =====================================

    if request.method == "POST":

        reason = request.form.get(
            "reason",
            ""
        ).strip()


        # =================================
        # VALIDASI ALASAN
        # =================================

        if not reason:

            return render_template(
                "need_leader.html",
                ticket=ticket,
                error=(
                    "Silakan pilih alasan "
                    "Need Leader."
                )
            )


        try:

            # =================================
            # SIMPAN ALASAN
            # =================================

            ticket.need_leader_reason = reason


            # =================================
            # UBAH STATUS
            # =================================

            ticket.status = (
                "Need Leader Confirmation"
            )


            # =================================
            # PASTIKAN BUKAN STATUS APPROVED
            # =================================

            ticket.approved_at = None


            db.session.commit()


        except Exception as error:

            db.session.rollback()

            return (
                f"Gagal mengubah ticket: "
                f"{str(error)}",
                500
            )


        return redirect(
            url_for(
                "pulling.pulling"
            )
        )


    # =====================================
    # GET
    # =====================================

    return render_template(
        "need_leader.html",
        ticket=ticket
    )


# =====================================================
# LEADER DETAIL TICKET
# =====================================================

@detailticket_bp.route(
    "/leader/<ticket_number>"
)
@role_required("leader", "admin")
def leader_detail(ticket_number):

    ticket = get_ticket(ticket_number)

    if not ticket:

        return "Ticket tidak ditemukan", 404


    if ticket.status != "Need Leader Confirmation":

        return (
            "Ticket ini tidak sedang "
            "membutuhkan konfirmasi Leader.",
            400
        )


    items = get_ticket_items(
        ticket.id
    )


    attach_part_photo(items)


    parts = (
        Part.query
        .order_by(
            Part.part_number.asc()
        )
        .all()
    )


    return render_template(
        "leader_detail.html",
        ticket=ticket,
        items=items,
        parts=parts
    )


# =====================================================
# UPDATE TICKET OLEH LEADER
# =====================================================

@detailticket_bp.route(
    "/leader/<ticket_number>/edit",
    methods=["POST"]
)
@role_required("leader", "admin")
def leader_edit_ticket(ticket_number):

    ticket = get_ticket(ticket_number)

    if not ticket:

        return (
            "Ticket tidak ditemukan",
            404
        )


    # =====================================
    # PASTIKAN STATUS NEED LEADER
    # =====================================

    if ticket.status != "Need Leader Confirmation":

        return (
            "Ticket ini tidak dapat diedit.",
            400
        )


    # Ticket yang sudah masuk periode closing MARIS terkunci.
    if MarisClosingTicket.query.filter_by(ticket_id=ticket.id).first():
        return ("Ticket sudah masuk periode closing MARIS dan terkunci.", 409)

    deleted_ids = {value.strip() for value in (request.form.get("deleted_item_ids") or "").split(",") if value.strip()}

    # =====================================
    # AMBIL SEMUA ITEM
    # =====================================

    items = get_ticket_items(
        ticket.id
    )


    # =====================================
    # UPDATE ITEM
    # =====================================

    for item in items:

        if str(item.id) in deleted_ids:
            continue

        part_number = request.form.get(
            f"part_number_{item.id}"
        )

        quantity = request.form.get(
            f"quantity_{item.id}"
        )


        # =================================
        # VALIDASI PART NUMBER
        # =================================

        if not part_number:

            return (
                f"Part Number untuk item "
                f"{item.part_number} tidak boleh kosong.",
                400
            )


        part_number = part_number.strip()


        # =================================
        # CARI PART DI MASTER
        # =================================

        part = (
            Part.query
            .filter_by(
                part_number=part_number
            )
            .first()
        )


        if not part:

            return (
                f"Part Number {part_number} "
                f"tidak ditemukan di Master Part.",
                400
            )


        # =================================
        # UPDATE PART
        # =================================

        item.part_number = part.part_number

        item.part_name = part.part_name


        # =================================
        # VALIDASI QUANTITY
        # =================================

        try:

            quantity = int(quantity)

        except (TypeError, ValueError):

            return (
                f"Quantity untuk Part "
                f"{part.part_number} tidak valid.",
                400
            )


        if quantity < 1:

            return (
                "Quantity tidak boleh kurang dari 1.",
                400
            )


        item.quantity = quantity


    # Hapus item yang ditandai di browser; baru commit saat Simpan & Selesai.
    for deleted_id in deleted_ids:
        item_to_delete = CrushingTransaction.query.filter_by(id=int(deleted_id), ticket_id=ticket.id).first() if deleted_id.isdigit() else None
        if item_to_delete:
            db.session.add(ActivityLog(ticket_id=ticket.id, actor="leader", activity=f"Menghapus part {item_to_delete.part_number} dari ticket (Leader edit)."))
            db.session.delete(item_to_delete)

    # Tambah part manual oleh Leader tanpa kalkulasi BOM.
    new_part_ids = request.form.getlist("new_part_id")
    new_quantities = request.form.getlist("new_quantity")
    if len(new_part_ids) != len(new_quantities):
        db.session.rollback()
        return ("Data part manual dan quantity tidak sesuai.", 400)
    for raw_part_id, raw_qty in zip(new_part_ids, new_quantities):
        try:
            part_id, quantity = int(raw_part_id), int(raw_qty)
        except (TypeError, ValueError):
            db.session.rollback()
            return ("Part manual atau quantity tidak valid.", 400)
        if quantity < 1:
            db.session.rollback()
            return ("Quantity part manual minimal 1.", 400)
        part = db.session.get(Part, part_id)
        if not part:
            db.session.rollback()
            return ("Part manual tidak ditemukan di Master Part.", 400)
        db.session.add(CrushingTransaction(
            ticket_id=ticket.id, line=part.line, model=part.model,
            part_number=part.part_number, part_name=part.part_name,
            quantity=quantity, shift=ticket.shift, price=float(part.price or 0),
            source_type="leader_manual"
        ))
        db.session.add(ActivityLog(ticket_id=ticket.id, actor="leader", activity=f"Menambahkan part manual {part.part_number} qty {quantity} (Leader edit)."))

    # Jangan sampai ticket kosong setelah perubahan.
    existing_count = CrushingTransaction.query.filter_by(ticket_id=ticket.id).count()
    removed_count = sum(1 for deleted_id in deleted_ids if deleted_id.isdigit() and CrushingTransaction.query.filter_by(id=int(deleted_id), ticket_id=ticket.id).first())
    if existing_count - removed_count + len(new_part_ids) <= 0:
        db.session.rollback()
        return ("Ticket harus memiliki minimal satu part.", 400)

    # =====================================
    # STATUS KEMBALI KE PENDING
    # =====================================

    ticket.status = "Pending Pulling"


    # =====================================
    # HAPUS ALASAN NEED LEADER
    # =====================================

    ticket.need_leader_reason = None


    # =====================================
    # HAPUS WAKTU APPROVED JIKA ADA
    # =====================================

    ticket.approved_at = None


    # =====================================
    # SIMPAN
    # =====================================

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        return (
            f"Gagal menyimpan perubahan: "
            f"{str(error)}",
            500
        )


    return redirect(
        url_for(
            "monitoring.monitoring"
        )
    )


# =====================================================
# HAPUS ITEM TICKET OLEH LEADER
# =====================================================

@detailticket_bp.route(
    "/leader/item/<int:item_id>/delete",
    methods=["POST"]
)
@role_required("leader", "admin")
def leader_delete_item(item_id):

    item = (
        CrushingTransaction.query
        .filter_by(
            id=item_id
        )
        .first()
    )


    if not item:

        return (
            "Item tidak ditemukan.",
            404
        )


    ticket = (
        CrushingTicket.query
        .filter_by(
            id=item.ticket_id
        )
        .first()
    )


    if not ticket:

        return (
            "Ticket tidak ditemukan.",
            404
        )


    if ticket.status != "Need Leader Confirmation":

        return (
            "Item tidak dapat dihapus karena "
            "ticket tidak sedang dalam proses "
            "Need Leader Confirmation.",
            400
        )


    ticket_number = ticket.ticket_number


    try:

        # =================================
        # HAPUS ITEM
        # =================================

        db.session.delete(item)

        db.session.flush()


        # =================================
        # CEK ITEM TERSISA
        # =================================

        remaining_items = (
            CrushingTransaction.query
            .filter_by(
                ticket_id=ticket.id
            )
            .count()
        )


        # =================================
        # JIKA TIDAK ADA ITEM
        # HAPUS TICKET
        # =================================

        if remaining_items == 0:

            db.session.delete(ticket)

            db.session.commit()

            return redirect(
                url_for(
                    "monitoring.monitoring"
                )
            )


        db.session.commit()


    except Exception as error:

        db.session.rollback()

        return (
            f"Gagal menghapus item: "
            f"{str(error)}",
            500
        )


    return redirect(
        url_for(
            "detailticket.leader_detail",
            ticket_number=ticket_number
        )
    )