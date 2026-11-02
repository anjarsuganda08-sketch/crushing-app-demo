from flask import (
    Blueprint,
    render_template,
    request,
    session,
    send_file,
    redirect,
    url_for,
    flash
)

from datetime import datetime, date, time, timedelta
from sqlalchemy import func
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side
)

from database.db import db

from routes.auth import role_required

from database.models import (
    CrushingTicket,
    CrushingTransaction,
    ActivityLog,
    User,
    MarisClosingPeriod,
    MarisClosingTicket
)

from werkzeug.security import check_password_hash


# ==========================================================
# BLUEPRINT
# ==========================================================

admin_maris_bp = Blueprint(
    "admin_maris",
    __name__,
    url_prefix="/admin-maris"
)


# ==========================================================
# KONFIGURASI REPORT
# ==========================================================

REPORT_SECTION = "ASSEMBLY"

REPORT_CT = "SFG"


# ==========================================================
# FUNGSI MENENTUKAN SHIFT LAPORAN PERUSAHAAN
# ==========================================================
#
# SHIFT GROUP YANG DIGUNAKAN OPERATOR
# ------------------------------------
# Operator tetap menggunakan:
#
# A
# B
#
#
# SHIFT LAPORAN PERUSAHAAN
# ------------------------
#
# 08:00 - 20:30 = Shift 1
#
# 20:31 - 07:59 = Shift 3
#
#
# Penentuan shift laporan dilakukan
# berdasarkan CrushingTicket.created_at.
#
# Jadi:
#
# Waktu ticket dibuat  : 10:15
# Shift laporan        : 1
#
# Waktu ticket dibuat  : 22:10
# Shift laporan        : 3
#
# Waktu Admin MARIS input tidak digunakan.
# ==========================================================

def get_report_shift(created_at):

    if not created_at:
        return ""


    transaction_time = created_at.time()


    # ======================================================
    # SHIFT 1
    # 08:00 - 20:30
    # ======================================================

    if (
        transaction_time >= time(8, 0)
        and
        transaction_time <= time(20, 30)
    ):

        return "1"


    # ======================================================
    # SHIFT 3
    # 20:31 - 07:59
    # ======================================================

    return "3"


# ==========================================================
# FUNGSI FORMAT TANGGAL
# ==========================================================
#
# Export hanya menampilkan tanggal.
#
# Contoh:
#
# 23-08-2026
#
# Tidak menampilkan:
#
# 23-08-2026 14:35:20
# ==========================================================

def format_report_date(created_at):

    if not created_at:
        return "-"


    return created_at.strftime(
        "%d-%m-%Y"
    )


# ==========================================================
# HALAMAN ADMIN MARIS
# ==========================================================

@admin_maris_bp.route(
    "/",
    methods=["GET", "POST"]
)
@role_required("admin", "maris")
def admin_maris():

    error_message = ""

    success_message = ""


    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        action = request.form.get(
            "action"
        )


        # ==================================================
        # TUTUP PERIODE: HANYA TICKET YANG SELESAI MARIS
        # ==================================================

        if action == "close_period":

            admin_name = (session.get("username") or session.get("user") or "Admin MARIS")

            # Ambil hanya ticket MARIS Completed yang belum pernah ditutup.
            eligible_tickets = (
                CrushingTicket.query
                .filter(
                    CrushingTicket.status == "MARIS Completed",
                    CrushingTicket.maris_transaction_number.isnot(None),
                    CrushingTicket.maris_transaction_number != "",
                    ~CrushingTicket.id.in_(db.session.query(MarisClosingTicket.ticket_id))
                )
                .order_by(CrushingTicket.maris_input_at.asc(), CrushingTicket.id.asc())
                .with_for_update()
                .all()
            )

            if not eligible_tickets:
                error_message = "Tidak ada tiket selesai MARIS yang belum ditutup. Tidak ada periode baru dibuat."
            else:
                now = datetime.now()
                period_number = "MARIS-" + now.strftime("%Y%m%d-%H%M%S-%f")
                total_amount = 0.0
                amounts = {}

                for eligible_ticket in eligible_tickets:
                    amount = (
                        db.session.query(
                            func.coalesce(
                                func.sum(CrushingTransaction.price * CrushingTransaction.quantity), 0
                            )
                        )
                        .filter(CrushingTransaction.ticket_id == eligible_ticket.id)
                        .scalar()
                    ) or 0
                    amounts[eligible_ticket.id] = float(amount)
                    total_amount += float(amount)

                period = MarisClosingPeriod(
                    period_number=period_number,
                    closed_at=now,
                    closed_by=admin_name,
                    ticket_count=len(eligible_tickets),
                    total_amount=total_amount,
                    notes="Penutupan manual oleh Admin MARIS"
                )
                db.session.add(period)
                db.session.flush()

                for eligible_ticket in eligible_tickets:
                    db.session.add(MarisClosingTicket(
                        period_id=period.id,
                        ticket_id=eligible_ticket.id,
                        ticket_number_snapshot=eligible_ticket.ticket_number,
                        maris_number_snapshot=eligible_ticket.maris_transaction_number,
                        amount_snapshot=amounts[eligible_ticket.id]
                    ))
                    db.session.add(ActivityLog(
                        ticket_id=eligible_ticket.id,
                        actor=admin_name,
                        activity=f"Ticket masuk penutupan periode MARIS {period_number}."
                    ))

                try:
                    db.session.commit()
                    success_message = (
                        f"Periode {period_number} berhasil ditutup: "
                        f"{len(eligible_tickets)} tiket, total amount Rp {total_amount:,.0f}."
                    )
                except Exception:
                    db.session.rollback()
                    error_message = "Penutupan gagal disimpan. Tidak ada tiket yang dipindahkan; silakan muat ulang dan coba lagi."


        # ==================================================
        # SIMPAN NOMOR TRANSAKSI MARIS
        # ==================================================

        elif action == "save_maris":

            ticket_id = (
                request.form.get(
                    "ticket_id"
                )
            )


            maris_transaction_number = (
                request.form.get(
                    "maris_transaction_number"
                ) or ""
            ).strip()


            # ==================================================
            # VALIDASI TICKET ID
            # ==================================================

            if not ticket_id:

                error_message = (
                    "Ticket tidak valid."
                )

            else:

                try:

                    ticket_id = int(
                        ticket_id
                    )

                except ValueError:

                    error_message = (
                        "Ticket tidak valid."
                    )


            # ==================================================
            # VALIDASI NOMOR MARIS
            # ==================================================

            if (
                not error_message
                and
                not maris_transaction_number
            ):

                error_message = (
                    "Nomor transaksi MARIS wajib diisi."
                )


            # ==================================================
            # CARI TICKET
            # ==================================================

            ticket = None


            if not error_message:

                ticket = (
                    CrushingTicket.query
                    .filter_by(
                        id=ticket_id
                    )
                    .first()
                )


                if not ticket:

                    error_message = (
                        "Ticket tidak ditemukan."
                    )


            # ==================================================
            # VALIDASI STATUS
            # ==================================================

            if (
                not error_message
                and
                ticket.status != "Approved"
            ):

                error_message = (
                    "Ticket belum berstatus Approved "
                    "sehingga belum dapat diproses Admin MARIS."
                )


            # ==================================================
            # CEGAH INPUT ULANG
            # ==================================================

            if (
                not error_message
                and
                ticket.maris_transaction_number
            ):

                error_message = (
                    "Nomor transaksi MARIS untuk ticket ini "
                    "sudah pernah diinput."
                )


            # ==================================================
            # SIMPAN
            # ==================================================

            if not error_message:

                # ==========================================
                # USER ADMIN SEMENTARA
                # ==========================================

                admin_name = (
                    session.get(
                        "username"
                    )
                    or
                    session.get(
                        "user"
                    )
                    or
                    "Admin MARIS"
                )


                # ==========================================
                # SIMPAN NOMOR TRANSAKSI MARIS
                # ==========================================

                ticket.maris_transaction_number = (
                    maris_transaction_number
                )


                # ==========================================
                # SIMPAN WAKTU INPUT MARIS
                # ==========================================

                ticket.maris_input_at = (
                    datetime.now()
                )


                # ==========================================
                # SIMPAN USER ADMIN MARIS
                # ==========================================

                ticket.maris_input_by = (
                    admin_name
                )


                # ==========================================
                # UPDATE STATUS
                # ==========================================

                ticket.status = (
                    "MARIS Completed"
                )


                # ==========================================
                # ACTIVITY LOG
                # ==========================================

                activity = ActivityLog(

                    ticket_id=ticket.id,

                    actor=admin_name,

                    activity=(
                        "Nomor transaksi MARIS "
                        f"{maris_transaction_number} "
                        "telah diinput oleh Admin MARIS."
                    )

                )


                db.session.add(
                    activity
                )


                # ==========================================
                # COMMIT
                # ==========================================

                db.session.commit()


                success_message = (
                    "Nomor transaksi MARIS berhasil "
                    "disimpan."
                )


    # ======================================================
    # CUTOFF DATA ADMIN MARIS = HARI INI
    # ======================================================
    #
    # Fokus halaman Admin MARIS hanya pada aktivitas hari ini:
    #
    # 1. Menunggu Input MARIS
    #    -> Ticket berstatus Approved
    #    -> approved_at terjadi hari ini
    #
    # 2. Selesai MARIS
    #    -> Ticket berstatus MARIS Completed
    #    -> maris_input_at terjadi hari ini
    #
    # Ticket dari hari sebelumnya tidak ikut ditampilkan pada
    # daftar harian ini.
    # ======================================================

    today = date.today()

    today_start = datetime.combine(
        today,
        time.min
    )

    tomorrow_start = datetime.combine(
        today + timedelta(days=1),
        time.min
    )


    # ======================================================
    # ANTREAN ADMIN MARIS - LINTAS TANGGAL PRODUKSI
    # ======================================================

    approved_tickets = (
        CrushingTicket.query
        .filter(
            CrushingTicket.status == "Approved",
            CrushingTicket.maris_transaction_number.is_(None)
        )
        .order_by(CrushingTicket.approved_at.asc(), CrushingTicket.id.asc())
        .all()
    )

    # Selesai MARIS tetapi belum ditutup masuk ke antrean penutupan.
    completed_tickets = (
        CrushingTicket.query
        .filter(
            CrushingTicket.status == "MARIS Completed",
            CrushingTicket.maris_transaction_number.isnot(None),
            ~CrushingTicket.id.in_(db.session.query(MarisClosingTicket.ticket_id))
        )
        .order_by(CrushingTicket.maris_input_at.asc(), CrushingTicket.id.asc())
        .all()
    )

    closing_periods = (
        MarisClosingPeriod.query
        .order_by(MarisClosingPeriod.closed_at.desc(), MarisClosingPeriod.id.desc())
        .limit(10)
        .all()
    )

    unclosed_total_amount = 0.0
    for pending_close_ticket in completed_tickets:
        unclosed_total_amount += float((
            db.session.query(
                func.coalesce(
                    func.sum(CrushingTransaction.price * CrushingTransaction.quantity), 0
                )
            )
            .filter(CrushingTransaction.ticket_id == pending_close_ticket.id)
            .scalar()
        ) or 0)

    # ======================================================
    # PENCARIAN TICKET LAMA YANG BELUM INPUT MARIS
    # ======================================================
    #
    # Halaman utama tetap CUT-OFF HARI INI.
    #
    # Tetapi Admin MARIS dapat mencari ticket lama yang:
    # - masih berstatus Approved
    # - belum memiliki nomor transaksi MARIS
    #
    # Pencarian menggunakan nomor ticket dan dapat berupa
    # sebagian nomor, sehingga ticket lama tetap dapat
    # ditemukan dan ditransaksikan.
    # ======================================================

    search_ticket = (
        request.args.get("search_ticket") or ""
    ).strip()

    searched_ticket = None
    search_message = None

    if search_ticket:

        searched_ticket = (
            CrushingTicket.query
            .filter(
                CrushingTicket.status == "Approved",
                CrushingTicket.maris_transaction_number.is_(None),
                CrushingTicket.ticket_number.ilike(
                    f"%{search_ticket}%"
                )
            )
            .order_by(
                CrushingTicket.approved_at.asc(),
                CrushingTicket.id.asc()
            )
            .first()
        )

        if not searched_ticket:
            search_message = (
                "Ticket Approved yang belum diinput MARIS "
                f"tidak ditemukan untuk pencarian "
                f"“{search_ticket}”."
            )


    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "admin_maris.html",

        approved_tickets=approved_tickets,

        completed_tickets=completed_tickets,

        closing_periods=closing_periods,

        unclosed_total_amount=unclosed_total_amount,

        searched_ticket=searched_ticket,

        search_ticket=search_ticket,

        search_message=search_message,

        error_message=error_message,

        success_message=success_message

    )


# ==========================================================
# EDIT TICKET OLEH ADMIN MARIS
# Password wajib merupakan password salah satu account ADMIN aplikasi.
# ==========================================================

@admin_maris_bp.route(
    "/ticket/<int:ticket_id>/edit",
    methods=["POST"]
)
@role_required("admin", "maris")
def edit_ticket(ticket_id):

    ticket = CrushingTicket.query.get(ticket_id)
    admin_password = (request.form.get("admin_password") or "").strip()

    if not ticket:
        flash("Ticket tidak ditemukan.", "error")
        return redirect(url_for("admin_maris.admin_maris"))

    if ticket.status not in {"Approved", "MARIS Completed"}:
        flash("Ticket ini tidak dapat diedit pada status saat ini.", "error")
        return redirect(url_for("admin_maris.admin_maris"))

    if MarisClosingTicket.query.filter_by(ticket_id=ticket.id).first():
        flash("Ticket sudah masuk periode MARIS yang ditutup. Perubahan langsung diblokir agar rekap historis tetap konsisten.", "error")
        return redirect(url_for("admin_maris.admin_maris"))

    if not admin_password:
        flash("Password Admin Aplikasi wajib diisi untuk mengedit ticket.", "error")
        return redirect(url_for("admin_maris.admin_maris"))

    admins = User.query.filter_by(role="admin", is_active=True).all()
    password_valid = any(
        check_password_hash(admin.password_hash, admin_password)
        for admin in admins
        if admin.password_hash
    )

    if not password_valid:
        flash("Password Admin Aplikasi salah. Perubahan ticket dibatalkan.", "error")
        return redirect(url_for("admin_maris.admin_maris"))

    items = CrushingTransaction.query.filter_by(ticket_id=ticket.id).order_by(CrushingTransaction.id.asc()).all()
    changed = []
    deleted = []

    try:
        for item in items:
            delete_flag = request.form.get(f"delete_{item.id}") == "1"
            if delete_flag:
                deleted.append(f"{item.part_number} (Qty {item.quantity})")
                db.session.delete(item)
                continue

            raw_qty = (request.form.get(f"quantity_{item.id}") or "").strip()
            try:
                new_qty = int(raw_qty)
            except (TypeError, ValueError):
                raise ValueError(f"Qty {item.part_number} tidak valid.")

            if new_qty < 1:
                raise ValueError(f"Qty {item.part_number} minimal 1. Jika ingin menghapus, gunakan checkbox Hapus.")

            if new_qty != item.quantity:
                changed.append(f"{item.part_number}: {item.quantity} → {new_qty}")
                item.quantity = new_qty

        db.session.flush()
        remaining = CrushingTransaction.query.filter_by(ticket_id=ticket.id).count()

        actor = session.get("username") or session.get("user") or "Admin MARIS"
        activity_parts = []
        if changed:
            activity_parts.append("ubah Qty [" + "; ".join(changed) + "]")
        if deleted:
            activity_parts.append("hapus Part [" + "; ".join(deleted) + "]")

        if remaining == 0:
            ticket_number = ticket.ticket_number
            db.session.delete(ticket)
            activity_message = "Ticket dihapus karena seluruh Part dihapus. " + ("; ".join(activity_parts) if activity_parts else "")
            # Activity log ikut cascade terhapus; perubahan tetap tercatat di server flash.
            db.session.commit()
            flash(f"{ticket_number} berhasil dihapus. {activity_message}", "success")
            return redirect(url_for("admin_maris.admin_maris"))

        if activity_parts:
            db.session.add(ActivityLog(
                ticket_id=ticket.id,
                actor=actor,
                activity="Edit ticket oleh Admin MARIS setelah verifikasi password Admin Aplikasi: " + "; ".join(activity_parts)
            ))
        else:
            db.session.add(ActivityLog(
                ticket_id=ticket.id,
                actor=actor,
                activity="Edit ticket dibuka oleh Admin MARIS, tetapi tidak ada perubahan data setelah verifikasi password Admin Aplikasi."
            ))

        db.session.commit()
        flash(f"Ticket {ticket.ticket_number} berhasil diperbarui.", "success")

    except Exception as error:
        db.session.rollback()
        flash(f"Perubahan ticket dibatalkan: {error}", "error")

    return redirect(url_for("admin_maris.admin_maris"))


# ==========================================================
# EXPORT EXCEL HARIAN
# ==========================================================

@admin_maris_bp.route(
    "/export",
    methods=["GET"]
)
@role_required("admin", "maris")
def export_excel():

    print("========== EXPORT BARU DIPANGGIL ==========")
    print("ADMIN MARIS EXPORT VERSI TERBARU")
    # ======================================================
    # AMBIL PARAMETER TANGGAL
    # ======================================================

    date_string = (
        request.args.get(
            "date"
        ) or ""
    ).strip()


    # ======================================================
    # JIKA TANGGAL TIDAK DIISI
    # GUNAKAN HARI INI
    # ======================================================

    if not date_string:

        export_date = date.today()


    else:

        try:

            export_date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return (
                "Format tanggal tidak valid. "
                "Gunakan format YYYY-MM-DD.",
                400
            )


    # ======================================================
    # BATAS AWAL TANGGAL
    # ======================================================

    start_datetime = datetime.combine(
        export_date,
        time.min
    )


    # ======================================================
    # BATAS AKHIR TANGGAL
    # ======================================================

    end_datetime = datetime.combine(
        export_date,
        time.max
    )


    # ======================================================
    # AMBIL TICKET
    #
    # HANYA:
    #
    # 1. MARIS Completed
    # 2. created_at sesuai tanggal export
    #
    # ======================================================

    tickets = (
        CrushingTicket.query
        .filter(
            CrushingTicket.status == "MARIS Completed",

            CrushingTicket.created_at >=
                start_datetime,

            CrushingTicket.created_at <=
                end_datetime
        )
        .order_by(
            CrushingTicket.created_at.asc(),
            CrushingTicket.id.asc()
        )
        .all()
    )


    # ======================================================
    # BUAT WORKBOOK
    # ======================================================

    workbook = Workbook()


    worksheet = (
        workbook.active
    )


    worksheet.title = (
        "Daily Report"
    )


    # ======================================================
    # JUDUL REPORT
    # ======================================================

    worksheet.merge_cells(
        "A1:N1"
    )


    worksheet["A1"] = (
        "CRUSHING APP - DAILY REPORT"
    )


    worksheet["A1"].font = Font(
        bold=True,
        size=16
    )


    worksheet["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


    worksheet.row_dimensions[1].height = 25


    # ======================================================
    # INFORMASI REPORT
    # ======================================================

    worksheet["A2"] = (
        "Tanggal Report"
    )


    worksheet["B2"] = (
        export_date.strftime(
            "%d-%m-%Y"
        )
    )


    worksheet["A3"] = (
        "Section"
    )


    worksheet["B3"] = (
        REPORT_SECTION
    )


    worksheet["A4"] = (
        "CT"
    )


    worksheet["B4"] = (
        REPORT_CT
    )


    worksheet["A5"] = (
        "Total Ticket"
    )


    worksheet["B5"] = (
        len(tickets)
    )


    for cell in (
        "A2",
        "A3",
        "A4",
        "A5"
    ):

        worksheet[cell].font = Font(
            bold=True
        )


    # ======================================================
    # HEADER TABLE
    # ======================================================
    #
    # A  No
    # B  Tanggal Transaksi
    # C  Shift
    # D  Section
    # E  CT
    # F  No Ticket
    # G  Remark
    # H  Part Number
    # I  Part Name
    # J  Jenis NG
    # K  Qty
    # L  Harga/PCS
    # M  Total Harga
    # N  Nomor Transaksi MARIS
    #
    # ======================================================

    header_row = 7


    headers = [

        "No",

        "Tanggal Transaksi",

        "Shift",

        "Section",

        "CT",

        "No Ticket",

        "Remark",

        "Part Number",

        "Part Name",

        "Jenis NG",

        "Qty",

        "Harga/PCS",

        "Total Harga",

        "Nomor Transaksi MARIS"

    ]


    for column_index, header in enumerate(
        headers,
        start=1
    ):

        cell = worksheet.cell(

            row=header_row,

            column=column_index,

            value=header

        )


        # ==============================================
        # FONT
        # ==============================================

        cell.font = Font(
            bold=True
        )


        # ==============================================
        # ALIGNMENT
        # ==============================================

        cell.alignment = Alignment(

            horizontal="center",

            vertical="center",

            wrap_text=True

        )


        # ==============================================
        # HEADER FILL
        # ==============================================

        cell.fill = PatternFill(

            fill_type="solid",

            fgColor="D9EAF7"

        )


    # ======================================================
    # BORDER
    # ======================================================

    thin_border = Border(

        left=Side(
            style="thin"
        ),

        right=Side(
            style="thin"
        ),

        top=Side(
            style="thin"
        ),

        bottom=Side(
            style="thin"
        )

    )


    # ======================================================
    # DATA ROW
    # ======================================================

    current_row = (
        header_row + 1
    )


    nomor = 1


    # ======================================================
    # LOOP TICKET
    # ======================================================

    for ticket in tickets:


        # ==================================================
        # SHIFT LAPORAN
        #
        # DITENTUKAN DARI WAKTU PEMBUATAN TICKET
        #
        # BUKAN SHIFT A/B
        # ==================================================

        report_shift = (
            get_report_shift(
                ticket.created_at
            )
        )


        # ==================================================
        # TANGGAL TRANSAKSI
        #
        # HANYA TANGGAL
        # ==================================================

        transaction_date = (
            format_report_date(
                ticket.created_at
            )
        )


        # ==================================================
        # AMBIL DETAIL PART
        # ==================================================

        transactions = (
            CrushingTransaction.query
            .filter_by(
                ticket_id=ticket.id
            )
            .order_by(
                CrushingTransaction.id.asc()
            )
            .all()
        )


        # ==================================================
        # JIKA TICKET TIDAK MEMILIKI TRANSAKSI
        # ==================================================

        if not transactions:

            values = [

                nomor,

                transaction_date,

                report_shift,

                REPORT_SECTION,

                REPORT_CT,

                ticket.ticket_number,

                ticket.remarks or "-",

                "-",

                "-",

                "-",

                0,

                0,

                0,

                ticket.maris_transaction_number or "-"

            ]


            for column_index, value in enumerate(
                values,
                start=1
            ):

                cell = worksheet.cell(

                    row=current_row,

                    column=column_index,

                    value=value

                )


                cell.border = thin_border


                cell.alignment = Alignment(

                    vertical="center",

                    wrap_text=True

                )


            # ==========================================
            # FORMAT HARGA/PCS
            # ==========================================

            worksheet.cell(
                row=current_row,
                column=12
            ).number_format = (
                '#,##0'
            )


            # ==========================================
            # FORMAT TOTAL HARGA
            # ==========================================

            worksheet.cell(
                row=current_row,
                column=13
            ).number_format = (
                '#,##0'
            )


            current_row += 1

            nomor += 1

            continue


        # ==================================================
        # LOOP SETIAP PART
        # ==================================================

        for transaction in transactions:


            # ==============================================
            # HARGA PER PCS
            #
            # Harga yang tersimpan pada transaction.price
            # adalah harga satuan.
            # ==============================================

            price_per_pcs = float(
                transaction.price or 0
            )


            # ==============================================
            # QUANTITY
            # ==============================================

            quantity = int(
                transaction.quantity or 0
            )


            # ==============================================
            # TOTAL HARGA
            #
            # Harga/PCS × Qty
            #
            # Contoh:
            #
            # Harga = 500
            # Qty   = 5
            #
            # Total = 2.500
            # ==============================================

            total_price = (
                price_per_pcs *
                quantity
            )


            # ==============================================
            # DATA ROW
            # ==============================================

            values = [

                nomor,

                transaction_date,

                report_shift,

                REPORT_SECTION,

                REPORT_CT,

                ticket.ticket_number,

                ticket.remarks or "-",

                transaction.part_number,

                transaction.part_name,

                transaction.jenis_ng or "-",

                quantity,

                price_per_pcs,

                total_price,

                ticket.maris_transaction_number or "-"

            ]


            # ==============================================
            # TULIS KE EXCEL
            # ==============================================

            for column_index, value in enumerate(
                values,
                start=1
            ):

                cell = worksheet.cell(

                    row=current_row,

                    column=column_index,

                    value=value

                )


                # ==========================================
                # BORDER
                # ==========================================

                cell.border = thin_border


                # ==========================================
                # ALIGNMENT
                # ==========================================

                cell.alignment = Alignment(

                    vertical="center",

                    wrap_text=True

                )


            # ==============================================
            # FORMAT HARGA/PCS
            #
            # Kolom L
            # ==============================================

            worksheet.cell(
                row=current_row,
                column=12
            ).number_format = (
                '#,##0'
            )


            # ==============================================
            # FORMAT TOTAL HARGA
            #
            # Kolom M
            # ==============================================

            worksheet.cell(
                row=current_row,
                column=13
            ).number_format = (
                '#,##0'
            )


            # ==============================================
            # NEXT ROW
            # ==============================================

            current_row += 1

            nomor += 1


    # ======================================================
    # JIKA TIDAK ADA DATA
    # ======================================================

    if not tickets:

        worksheet.cell(

            row=current_row,

            column=1,

            value=(
                "Tidak ada ticket MARIS Completed "
                "pada tanggal tersebut."
            )

        )


        worksheet.merge_cells(

            start_row=current_row,

            start_column=1,

            end_row=current_row,

            end_column=len(headers)

        )


        worksheet.cell(

            row=current_row,

            column=1

        ).alignment = Alignment(

            horizontal="center",

            vertical="center"

        )


    # ======================================================
    # FREEZE HEADER
    # ======================================================

    worksheet.freeze_panes = (
        "A8"
    )


    # ======================================================
    # AUTO FILTER
    # ======================================================

    if tickets:

        last_row = (
            current_row - 1
        )


        worksheet.auto_filter.ref = (
            f"A{header_row}:"
            f"N{last_row}"
        )


    # ======================================================
    # LEBAR KOLOM
    # ======================================================

    column_widths = {

        "A": 7,

        "B": 18,

        "C": 10,

        "D": 14,

        "E": 10,

        "F": 24,

        "G": 20,

        "H": 25,

        "I": 35,

        "J": 25,

        "K": 10,

        "L": 15,

        "M": 18,

        "N": 28

    }


    for column, width in (
        column_widths.items()
    ):

        worksheet.column_dimensions[
            column
        ].width = width


    # ======================================================
    # TINGGI HEADER
    # ======================================================

    worksheet.row_dimensions[
        header_row
    ].height = 35


    # ======================================================
    # SIMPAN WORKBOOK KE MEMORY
    # ======================================================

    output = BytesIO()


    workbook.save(
        output
    )


    output.seek(0)


    # ======================================================
    # NAMA FILE
    # ======================================================

    filename = (

        "Crushing_Report_"

        +

        export_date.strftime(
            "%Y%m%d"
        )

        +

        ".xlsx"

    )


    # ======================================================
    # DOWNLOAD FILE
    # ======================================================

    return send_file(

        output,

        as_attachment=True,

        download_name=filename,

        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )

    )