import io
import os
import shutil

import pandas as pd

from openpyxl import Workbook

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    url_for,
    session,
    send_file
)

from werkzeug.utils import secure_filename

from database.db import db
from database.models import Part
from routes.auth import role_required


import_master_bp = Blueprint(
    "import_master",
    __name__
)


# =====================================================
# KOLOM WAJIB EXCEL
# =====================================================

REQUIRED_COLUMNS = [

    "Line",
    "Model",
    "Part Name",
    "Part Number",
    "Return Location",
    "Price"

]


# =====================================================
# HELPER
# BERSIHKAN NILAI TEXT
# =====================================================

def clean_text(value):

    if pd.isna(value):

        return ""

    return str(value).strip()


# =====================================================
# HELPER
# KONVERSI HARGA
# =====================================================

def clean_price(value):
    if pd.isna(value):
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clean_qty(value):
    if pd.isna(value) or str(value).strip() == "":
        return 1
    try:
        quantity = int(float(value))
        return quantity if quantity > 0 else 1
    except (TypeError, ValueError):
        return 1


# =====================================================
# HALAMAN IMPORT MASTER
# =====================================================

@import_master_bp.route(
    "/import-master",
    methods=["GET", "POST"]
)
@role_required("admin", "maris")
def import_master():

    preview = session.get(
        "import_preview"
    )

    # =================================================
    # POST
    # =================================================

    if request.method == "POST":

        file = request.files.get(
            "excel"
        )

        # ---------------------------------------------
        # VALIDASI FILE
        # ---------------------------------------------

        if not file:

            flash(
                "Silakan pilih file Excel."
            )

            return redirect(
                request.url
            )

        try:

            # -----------------------------------------
            # BACA FILE
            # -----------------------------------------

            file_bytes = file.read()

            df = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name="Master Part"
            )

        except Exception as error:

            flash(
                "File Excel tidak dapat dibaca. "
                "Pastikan terdapat sheet bernama "
                "'Master Part'. "
                f"Detail: {str(error)}"
            )

            return redirect(
                request.url
            )

        # ---------------------------------------------
        # BERSIHKAN NAMA KOLOM
        # ---------------------------------------------

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # ---------------------------------------------
        # VALIDASI HEADER
        # ---------------------------------------------

        missing = []

        for col in REQUIRED_COLUMNS:

            if col not in df.columns:

                missing.append(col)

        if missing:

            flash(

                "Kolom berikut tidak ditemukan: " +
                ", ".join(missing)

            )

            return redirect(
                request.url
            )

        # =============================================
        # PREVIEW
        # =============================================

        total_excel = len(df)

        new_count = 0

        update_count = 0

        error_count = 0

        for _, row in df.iterrows():

            try:

                line = clean_text(
                    row["Line"]
                )

                model = clean_text(
                    row["Model"]
                )

                part_number = clean_text(
                    row["Part Number"]
                )

                # -------------------------------------
                # VALIDASI PART NUMBER
                # -------------------------------------

                if not part_number:

                    error_count += 1

                    continue

                # -------------------------------------
                # CEK DATA DI DATABASE
                # -------------------------------------

                exist = Part.query.filter_by(
                    line=line,
                    model=model,
                    part_number=part_number
                ).first()

                if exist:

                    update_count += 1

                else:

                    new_count += 1

            except Exception:

                error_count += 1

        # =============================================
        # SIMPAN FILE SEMENTARA
        # =============================================

        temp_folder = os.path.join(
            "uploads",
            "temp"
        )

        os.makedirs(
            temp_folder,
            exist_ok=True
        )

        temp_filename = secure_filename(
            "temp_import.xlsx"
        )

        temp_path = os.path.join(
            temp_folder,
            temp_filename
        )

        with open(
            temp_path,
            "wb"
        ) as f:

            f.write(
                file_bytes
            )

        # =============================================
        # SIMPAN PREVIEW KE SESSION
        # =============================================

        session["import_preview"] = {

            "filename": file.filename,

            "total": total_excel,

            "new": new_count,

            "update": update_count,

            "error": error_count,

            "temp_file": temp_path

        }

        return redirect(

            url_for(
                "import_master.import_master"
            )

        )

    # =================================================
    # GET
    # =================================================

    return render_template(

        "import_master.html",

        preview=preview

    )


# =====================================================
# IMPORT KE DATABASE
# =====================================================

@import_master_bp.route(
    "/import-master/import",
    methods=["POST"]
)
@role_required("admin", "maris")
def import_database():

    preview = session.get(
        "import_preview"
    )

    # =================================================
    # CEK PREVIEW
    # =================================================

    if not preview:

        flash(
            "Silakan lakukan Analisa File terlebih dahulu."
        )

        return redirect(
            url_for(
                "import_master.import_master"
            )
        )

    try:

        # =============================================
        # BACKUP DATABASE
        # =============================================

        db_path = os.path.join(
            "instance",
            "database.db"
        )

        if not os.path.exists(db_path):

            raise Exception(
                "database.db tidak ditemukan."
            )

        backup_folder = "backup"

        os.makedirs(
            backup_folder,
            exist_ok=True
        )

        backup_name = (

            "database_backup_" +

            pd.Timestamp.now().strftime(
                "%Y%m%d_%H%M%S"
            ) +

            ".db"

        )

        backup_path = os.path.join(
            backup_folder,
            backup_name
        )

        shutil.copy2(
            db_path,
            backup_path
        )

        # =============================================
        # BACA FILE EXCEL
        # =============================================

        temp_file = preview[
            "temp_file"
        ]

        df = pd.read_excel(
            temp_file,
            sheet_name="Master Part"
        )

        # ---------------------------------------------
        # BERSIHKAN HEADER
        # ---------------------------------------------

        df.columns = [

            str(column).strip()

            for column in df.columns

        ]

        # =============================================
        # COUNTER
        # =============================================

        insert_count = 0

        update_count = 0

        error_count = 0

        # =============================================
        # IMPORT DATA
        # =============================================

        for _, row in df.iterrows():

            try:

                # -------------------------------------
                # AMBIL DATA
                # -------------------------------------

                line = clean_text(
                    row["Line"]
                )

                model = clean_text(
                    row["Model"]
                )

                part_name = clean_text(
                    row["Part Name"]
                )

                part_number = clean_text(
                    row["Part Number"]
                )

                return_location = clean_text(
                    row["Return Location"]
                )

                price = clean_price(
                    row["Price"]
                )

                # SKU (Child) dan Qty (Child) opsional untuk kompatibilitas
                # dengan file Master Part versi lama.
                sku = clean_text(row.get("SKU (Child)", ""))
                qty_child = clean_qty(row.get("Qty (Child)", 1))

                # -------------------------------------
                # VALIDASI PART NUMBER
                # -------------------------------------

                if not part_number:

                    error_count += 1

                    continue

                # -------------------------------------
                # CARI PART
                # -------------------------------------

                part = Part.query.filter_by(

                    line=line,

                    model=model,

                    part_number=part_number

                ).first()

                # =====================================
                # UPDATE
                # =====================================

                if part:

                    part.line = line

                    part.model = model

                    part.part_name = part_name

                    part.return_location = (
                        return_location
                    )

                    # UPDATE DATA MASTER; foto lama dipertahankan.
                    part.price = price
                    if "SKU (Child)" in df.columns:
                        part.sku = sku or part.sku
                    if "Qty (Child)" in df.columns:
                        part.qty_child = qty_child

                    # FOTO TIDAK DIUBAH meskipun kolom Photo kosong/tidak ada.

                    update_count += 1

                # =====================================
                # INSERT
                # =====================================

                else:

                    new_part = Part(

                        line=line,

                        model=model,

                        part_name=part_name,

                        part_number=part_number,

                        return_location=return_location,

                        price=price,

                        sku=sku or None,

                        qty_child=qty_child,

                        photo=None

                    )

                    db.session.add(
                        new_part
                    )

                    insert_count += 1

            except Exception:

                error_count += 1

        # =============================================
        # COMMIT
        # =============================================

        db.session.commit()

        # =============================================
        # HAPUS FILE TEMPORARY
        # =============================================

        if os.path.exists(temp_file):

            os.remove(
                temp_file
            )

        # =============================================
        # HAPUS SESSION
        # =============================================

        session.pop(
            "import_preview",
            None
        )

        # =============================================
        # NOTIFIKASI
        # =============================================

        flash(

            "Import berhasil. "

            f"{insert_count} Part baru, "

            f"{update_count} Part diupdate, "

            f"{error_count} Baris dilewati. "

            f"Backup database: {backup_name}"

        )

    except Exception as error:

        db.session.rollback()

        flash(

            "Import gagal: " +
            str(error)

        )

    return redirect(

        url_for(
            "import_master.import_master"
        )

    )


# =====================================================
# DOWNLOAD MASTER PART
# =====================================================

@import_master_bp.route(
    "/download-master"
)
@role_required("admin", "maris")
def download_master():

    wb = Workbook()

    ws = wb.active

    ws.title = "Master Part"

    # =================================================
    # HEADER
    # =================================================

    ws.append([

        "Line",

        "Model",

        "Part Name",

        "Part Number",

        "Return Location",

        "Price",

        "Photo"

    ])

    # =================================================
    # AMBIL DATA
    # =================================================

    parts = (

        Part.query

        .order_by(

            Part.line,

            Part.model,

            Part.part_name

        )

        .all()

    )

    # =================================================
    # MASUKKAN KE EXCEL
    # =================================================

    for part in parts:

        ws.append([

            part.line,

            part.model,

            part.part_name,

            part.part_number,

            part.return_location,

            float(part.price or 0),

            part.photo

        ])

    # =================================================
    # SIMPAN KE MEMORY
    # =================================================

    output = io.BytesIO()

    wb.save(
        output
    )

    output.seek(0)

    return send_file(

        output,

        as_attachment=True,

        download_name="Master_Part.xlsx",

        mimetype=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    )