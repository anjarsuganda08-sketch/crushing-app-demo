from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    url_for
)

from datetime import datetime
import uuid

from database.db import db

from routes.auth import role_required, get_current_user

from database.models import (
    Part,
    CrushingTransaction,
    CrushingTicket,
    NgClassification,
    NgType
)


production_bp = Blueprint(
    "production",
    __name__
)


# ==========================================================
# OPERATOR PRODUKSI
# ==========================================================

@production_bp.route(
    "/production",
    methods=["GET", "POST"]
)
@role_required("operator", "admin", "leader", "viewer")
def production():

    # ======================================================
    # TEMPORARY TICKET
    # ======================================================

    if "temp_ticket" not in session:

        session["temp_ticket"] = str(
            uuid.uuid4()
        )

    temp_ticket = session["temp_ticket"]


    # ======================================================
    # ERROR MESSAGE
    # ======================================================

    error_message = None


    # ======================================================
    # HELPER RENDER
    #
    # Digunakan supaya ketika terjadi error,
    # halaman tetap berada di production.
    # ======================================================

    def render_production_page(
        error_message=None
    ):

        # ==================================================
        # MASTER LINE
        # ==================================================

        lines = (
            Part.query
            .with_entities(
                Part.line
            )
            .distinct()
            .order_by(
                Part.line
            )
            .all()
        )


        # ==================================================
        # MASTER PART
        # ==================================================

        parts = (
            Part.query
            .order_by(
                Part.line,
                Part.model,
                Part.part_name
            )
            .all()
        )


        # ==================================================
        # TRANSAKSI SEMENTARA
        # ==================================================

        transactions = (
            CrushingTransaction.query
            .filter_by(
                temp_ticket=temp_ticket
            )
            .order_by(
                CrushingTransaction.id.desc()
            )
            .all()
        )


        # ==================================================
        # DATA PART UNTUK JAVASCRIPT
        # ==================================================

        parts_data = []


        for part in parts:

            parts_data.append({

                "line":
                    part.line,

                "model":
                    part.model,

                "part_name":
                    part.part_name,

                "part_number":
                    part.part_number,

                "sku":
                    part.sku or "",

                "qty_child":
                    int(part.qty_child or 1),

                "return_location":
                    part.return_location,

                "price":
                    float(
                        part.price or 0
                    ),

                "photo":
                    part.photo

            })


        # ==================================================
        # MASTER KLASIFIKASI NG
        # ==================================================

        ng_classifications = (
            NgClassification.query
            .order_by(
                NgClassification.name
            )
            .all()
        )


        # ==================================================
        # MASTER JENIS NG
        # ==================================================

        ng_types = (
            NgType.query
            .order_by(
                NgType.name
            )
            .all()
        )


        # ==================================================
        # REMARK AKTIF
        # ==================================================

        current_remarks = (
            session.get(
                "temp_remarks",
                ""
            )
        )


        # ==================================================
        # LINE DAN MODEL AKTIF
        #
        # Jika ticket sudah mempunyai transaksi,
        # gunakan Line dan Model dari transaksi terakhir.
        #
        # Secara normal seluruh part dalam satu ticket
        # menggunakan Line + Model yang sama.
        # ==================================================

        current_line = ""

        current_model = ""

        current_shift = ""


        if transactions:

            latest_transaction = (
                transactions[0]
            )

            current_line = (
                latest_transaction.line or ""
            )

            current_model = (
                latest_transaction.model or ""
            )

            current_shift = (
                latest_transaction.shift or ""
            )


        # ==================================================
        # DEBUG
        # ==================================================

        print("=" * 70)

        print(
            "TOTAL PART DI DATABASE :",
            len(parts)
        )

        print(
            "TOTAL TRANSAKSI SEMENTARA :",
            len(transactions)
        )

        print(
            "TOTAL KLASIFIKASI NG :",
            len(ng_classifications)
        )

        print(
            "TOTAL JENIS NG :",
            len(ng_types)
        )

        print(
            "TEMP TICKET :",
            temp_ticket
        )

        print(
            "REMARK AKTIF :",
            current_remarks
        )

        print(
            "LINE AKTIF :",
            current_line
        )

        print(
            "MODEL AKTIF :",
            current_model
        )

        print(
            "SHIFT AKTIF :",
            current_shift
        )

        print("=" * 70)


        # ==================================================
        # RENDER
        # ==================================================

        return render_template(

            "production.html",

            lines=lines,

            parts=parts,

            parts_data=parts_data,

            transactions=transactions,

            current_remarks=current_remarks,

            current_line=current_line,

            current_model=current_model,

            current_shift=current_shift,

            ng_classifications=ng_classifications,

            ng_types=ng_types,

            error_message=error_message

        )


    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        action = (
            request.form.get(
                "action"
            )
        )


        # ==================================================
        # TAMBAH PART
        # ==================================================

        if action == "save_part":

            # ==================================================
            # AMBIL DATA FORM
            # ==================================================

            selected_line = (
                request.form.get(
                    "line"
                ) or ""
            ).strip()


            selected_model = (
                request.form.get(
                    "model"
                ) or ""
            ).strip()


            selected_part_numbers = [
                str(value).strip()
                for value in request.form.getlist("part_number")
                if str(value).strip()
            ]


            selected_jenis_ng = (
                request.form.get(
                    "jenis_ng"
                ) or ""
            ).strip()


            selected_shift = (
                request.form.get(
                    "shift"
                ) or ""
            ).strip()


            qty_values = [
                str(value).strip()
                for value in request.form.getlist("qty")
            ]

            source_types = [
                str(value).strip().lower()
                for value in request.form.getlist("source_type")
            ]
            try:
                fg_quantity = int(request.form.get("fg_quantity", "1") or "1")
            except (TypeError, ValueError):
                fg_quantity = 0


            # ==================================================
            # REMARK
            #
            # PENTING:
            #
            # Jika Remark sudah terkunci di halaman,
            # HTML menggunakan disabled.
            #
            # Field disabled tidak dikirim oleh browser.
            #
            # Karena itu Remark ticket aktif SELALU
            # diambil dari session.
            # ==================================================

            posted_remarks = (
                request.form.get(
                    "remarks"
                ) or ""
            ).strip()


            existing_remarks = (
                session.get(
                    "temp_remarks",
                    ""
                )
            )


            if existing_remarks:

                selected_remarks = (
                    existing_remarks
                )

            else:

                selected_remarks = (
                    posted_remarks
                )


            # ==================================================
            # VALIDASI LINE
            # ==================================================

            if not selected_line:

                return render_production_page(
                    "Line wajib dipilih."
                ), 400


            # ==================================================
            # VALIDASI MODEL
            # ==================================================

            if not selected_model:

                return render_production_page(
                    "Model wajib dipilih."
                ), 400


            # ==================================================
            # VALIDASI PART
            # ==================================================

            if not selected_part_numbers:

                return render_production_page(
                    "Minimal satu Part wajib dipilih."
                ), 400

            if len(selected_part_numbers) != len(qty_values) or len(selected_part_numbers) != len(source_types):
                return render_production_page(
                    "Data Part, Qty, dan sumber pemilihan tidak sesuai. Silakan pilih ulang part."
                ), 400

            if fg_quantity < 1:
                return render_production_page("Qty FG harus minimal 1."), 400


            # ==================================================
            # VALIDASI REMARK
            # ==================================================

            if not selected_remarks:

                return render_production_page(
                    "Klasifikasi NG / Remark wajib dipilih."
                ), 400


            # ==================================================
            # VALIDASI REMARK DARI DATABASE
            # ==================================================

            valid_remarks = (
                NgClassification.query
                .filter_by(
                    name=selected_remarks
                )
                .first()
            )


            if not valid_remarks:

                return render_production_page(
                    "Klasifikasi NG / Remark tidak terdaftar di Master."
                ), 400


            # ==================================================
            # VALIDASI JENIS NG
            # ==================================================

            if not selected_jenis_ng:

                return render_production_page(
                    "Jenis NG wajib dipilih."
                ), 400


            # ==================================================
            # VALIDASI JENIS NG DARI DATABASE
            # ==================================================

            valid_jenis_ng = (
                NgType.query
                .filter_by(
                    name=selected_jenis_ng
                )
                .first()
            )


            if not valid_jenis_ng:

                return render_production_page(
                    "Jenis NG tidak terdaftar di Master Jenis NG."
                ), 400


            # ==================================================
            # VALIDASI SHIFT
            # ==================================================

            if not selected_shift:

                return render_production_page(
                    "Shift wajib dipilih."
                ), 400


            # ==================================================
            # VALIDASI QTY PER PART
            # ==================================================

            quantities = []

            for raw_qty in qty_values:

                try:
                    quantity = int(raw_qty)
                except (ValueError, TypeError):
                    return render_production_page(
                        "Qty setiap Part harus berupa angka."
                    ), 400

                if quantity <= 0:
                    return render_production_page(
                        "Qty setiap Part harus lebih besar dari 0."
                    ), 400

                quantities.append(quantity)


            # ==================================================
            # SIMPAN / VALIDASI REMARK
            # ==================================================

            if existing_remarks:

                # ==============================================
                # REMARK SUDAH TERKUNCI
                # ==============================================

                if (
                    existing_remarks
                    != selected_remarks
                ):

                    return render_production_page(
                        "Klasifikasi NG tidak boleh berubah selama Ticket masih aktif."
                    ), 400

            else:

                # ==============================================
                # REMARK PERTAMA
                # ==============================================

                session[
                    "temp_remarks"
                ] = selected_remarks

                session.modified = True


            # ==================================================
            # CARI DAN SIMPAN SEMUA PART TERPILIH
            #
            # Menggunakan LINE + MODEL + PART NUMBER karena
            # satu Part Number dapat muncul pada Model berbeda.
            # ==================================================

            for selected_part_number, quantity, source_type in zip(
                selected_part_numbers, quantities, source_types
            ):

                selected_part = (
                    Part.query
                    .filter_by(
                        line=selected_line,
                        model=selected_model,
                        part_number=selected_part_number
                    )
                    .first()
                )

                if not selected_part:
                    db.session.rollback()
                    return render_production_page(
                        f"Part '{selected_part_number}' tidak ditemukan di Master Part untuk Line dan Model yang dipilih."
                    ), 404

                if source_type not in {"bom", "manual"}:
                    db.session.rollback()
                    return render_production_page("Sumber pemilihan part tidak valid."), 400

                if source_type == "bom":
                    expected_qty = max(1, int(selected_part.qty_child or 1)) * fg_quantity
                    if quantity != expected_qty:
                        db.session.rollback()
                        return render_production_page(
                            f"Qty BOM untuk {selected_part.part_number} harus {expected_qty} (Qty Child × Qty FG)."
                        ), 400

                part_price = float(selected_part.price or 0)

                trx = CrushingTransaction(
                    temp_ticket=temp_ticket,
                    line=selected_part.line,
                    model=selected_part.model,
                    part_number=selected_part.part_number,
                    part_name=selected_part.part_name,
                    quantity=quantity,
                    jenis_ng=selected_jenis_ng,
                    price=part_price,
                    shift=selected_shift,
                    source_type=source_type
                )

                db.session.add(trx)

            db.session.commit()


            # ==================================================
            # REDIRECT
            #
            # Redirect membuat halaman membaca ulang:
            #
            # - Remark aktif
            # - Line aktif
            # - Model aktif
            # - Shift aktif
            #
            # JavaScript kemudian otomatis fokus ke Part.
            # ==================================================

            return redirect(
                url_for(
                    "production.production"
                )
            )


        # ==================================================
        # FINISH TICKET
        # ==================================================

        elif action == "finish_ticket":

            # ==================================================
            # CARI TRANSAKSI PERTAMA
            # ==================================================

            first_item = (
                CrushingTransaction.query
                .filter_by(
                    temp_ticket=temp_ticket
                )
                .order_by(
                    CrushingTransaction.id.asc()
                )
                .first()
            )


            # ==================================================
            # BELUM ADA PART
            # ==================================================

            if not first_item:

                return render_production_page(
                    "Belum ada part di dalam ticket."
                ), 400


            # ==================================================
            # REMARK TICKET
            # ==================================================

            ticket_remarks = (
                session.get(
                    "temp_remarks",
                    ""
                )
            )


            # ==================================================
            # VALIDASI REMARK
            # ==================================================

            if not ticket_remarks:

                return render_production_page(
                    "Klasifikasi NG / Remark belum dipilih."
                ), 400


            # ==================================================
            # GENERATE NOMOR TICKET
            # ==================================================

            ticket_number = (
                "CT-"
                +
                datetime.now().strftime(
                    "%Y%m%d-%H%M%S"
                )
            )


            # ==================================================
            # BUAT CRUSHING TICKET
            # ==================================================

            current_user = get_current_user()

            ticket = CrushingTicket(

                ticket_number=ticket_number,

                line=first_item.line,

                shift=first_item.shift,

                status="Pending Pulling",

                remarks=ticket_remarks,

                operator_npk=(current_user.npk if current_user else None),

                operator_name=(current_user.full_name if current_user else None)

            )


            db.session.add(
                ticket
            )

            db.session.commit()


            # ==================================================
            # AMBIL SEMUA TRANSAKSI
            # ==================================================

            items = (
                CrushingTransaction.query
                .filter_by(
                    temp_ticket=temp_ticket
                )
                .all()
            )


            # ==================================================
            # HUBUNGKAN TRANSAKSI DENGAN TICKET
            # ==================================================

            for item in items:

                item.ticket_id = (
                    ticket.id
                )

                item.temp_ticket = None


            db.session.commit()


            # ==================================================
            # BERSIHKAN SESSION
            # ==================================================

            session.pop(
                "temp_ticket",
                None
            )

            session.pop(
                "temp_remarks",
                None
            )

            session.modified = True


            # ==================================================
            # REDIRECT KE DETAIL TICKET
            # ==================================================

            return redirect(
                url_for(
                    "production_detail.production_ticket_detail",
                    ticket_number=ticket_number,
                    created="1"
                )
            )


    # ======================================================
    # GET
    # ======================================================

    return render_production_page()