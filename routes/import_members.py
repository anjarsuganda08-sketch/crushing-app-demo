# ============================================================
# IMPORT MEMBER
# CRUSHING APP
# ============================================================

import os
import uuid
from io import BytesIO

import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session,
    send_file
)

from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from database.db import db
from database.models import User

from routes.auth import role_required


# ============================================================
# BLUEPRINT
# ============================================================

import_members_bp = Blueprint(
    "import_members",
    __name__,
    url_prefix="/import-members"
)


# ============================================================
# KONFIGURASI
# ============================================================

SHEET_NAME = "Data Member"

ALLOWED_EXTENSIONS = {
    ".xlsx",
    ".xls"
}


# ============================================================
# MAPPING ROLE
# ============================================================

ROLE_MAPPING = {
    "Admin": "admin",
    "Leader": "leader",
    "Maris": "maris",
    "Produksi": "operator",
    "Pulling": "pulling",
    "Viewer": "viewer"
}


# ============================================================
# NORMALISASI ROLE
# ============================================================

def normalize_excel_role(role):

    if pd.isna(role):
        return ""

    role = str(role).strip()

    for excel_role, db_role in ROLE_MAPPING.items():

        if role.lower() == excel_role.lower():

            return db_role

    return ""


# ============================================================
# NORMALISASI NPK
# ============================================================

def normalize_npk(value):

    if pd.isna(value):
        return ""

    # Excel membaca angka sebagai float
    # Contoh:
    # 20.0 → 20

    if isinstance(value, float):

        if value.is_integer():

            return str(
                int(value)
            )

    return str(value).strip()


# ============================================================
# CEK EXTENSION
# ============================================================

def allowed_file(filename):

    if not filename:
        return False

    filename = filename.lower()

    return any(
        filename.endswith(ext)
        for ext in ALLOWED_EXTENSIONS
    )


# ============================================================
# FOLDER UPLOAD
# ============================================================

def get_upload_folder():

    upload_folder = os.path.join(
        current_app.root_path,
        "instance",
        "uploads"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    return upload_folder


# ============================================================
# BACA DAN VALIDASI EXCEL
# ============================================================

def read_excel_file(filepath):

    try:

        df = pd.read_excel(
            filepath,
            sheet_name=SHEET_NAME
        )

    except Exception as error:

        raise ValueError(
            f"Gagal membaca Excel: {error}"
        )


    # ========================================================
    # NORMALISASI KOLOM
    # ========================================================

    df.columns = [
        str(column)
        .strip()
        .upper()
        for column in df.columns
    ]


    # ========================================================
    # KOLOM WAJIB
    # ========================================================

    required_columns = {
        "NICKNAME",
        "NPK",
        "NAMA",
        "ROLE"
    }

    actual_columns = set(
        df.columns
    )

    missing_columns = (
        required_columns
        - actual_columns
    )

    if missing_columns:

        raise ValueError(
            "Kolom Excel tidak lengkap. "
            f"Kolom yang kurang: "
            f"{', '.join(sorted(missing_columns))}"
        )


    return df


# ============================================================
# MEMBUAT DATA PREVIEW
# ============================================================

def build_preview(df):

    rows = []

    valid_count = 0
    duplicate_count = 0
    update_count = 0
    error_count = 0

    seen_usernames = set()


    # ========================================================
    # LOOP DATA
    # ========================================================

    for index, row in df.iterrows():

        excel_row = index + 2

        nickname = ""
        npk = ""
        nama = ""
        role_excel = ""
        role = ""

        status = "valid"
        status_label = "✓ Siap Import"
        keterangan = "Siap dimasukkan."


        try:

            # =================================================
            # AMBIL DATA
            # =================================================

            nickname = str(
                row["NICKNAME"]
            ).strip()

            npk = normalize_npk(
                row["NPK"]
            )

            nama = str(
                row["NAMA"]
            ).strip()

            role_excel = str(
                row["ROLE"]
            ).strip()


            # =================================================
            # VALIDASI
            # =================================================

            if not nickname:

                raise ValueError(
                    "NICKNAME kosong"
                )


            if not npk:

                raise ValueError(
                    "NPK kosong"
                )


            if not nama:

                raise ValueError(
                    "NAMA kosong"
                )


            if not role_excel:

                raise ValueError(
                    "ROLE kosong"
                )


            # =================================================
            # MAPPING ROLE
            # =================================================

            role = normalize_excel_role(
                role_excel
            )

            if not role:

                raise ValueError(
                    f"ROLE tidak dikenali: {role_excel}"
                )


            # =================================================
            # USERNAME
            # =================================================

            username = nickname


            # =================================================
            # DUPLICATE DALAM EXCEL
            # =================================================

            username_key = username.lower()

            if username_key in seen_usernames:

                status = "duplicate"

                status_label = "⚠ Duplicate"

                keterangan = (
                    "Username duplicate "
                    "di dalam file Excel."
                )

                duplicate_count += 1

                rows.append({

                    "row": excel_row,

                    "npk": npk,

                    "username": username,

                    "full_name": nama,

                    "role_excel": role_excel,

                    "role": role,

                    "status": status,

                    "status_label": status_label,

                    "keterangan": keterangan

                })

                continue


            seen_usernames.add(
                username_key
            )


            # =================================================
            # CEK DATABASE
            # =================================================

            existing_user = (
                User.query
                .filter_by(
                    username=username
                )
                .first()
            )


            if existing_user:

                same_data = (
                    str(existing_user.npk or "").strip() == npk
                    and str(existing_user.full_name or "").strip() == nama
                    and str(existing_user.role or "").strip().lower() == role
                )

                if same_data:
                    status = "duplicate"
                    status_label = "⚠ Sudah Ada"
                    keterangan = "Username sudah ada dan datanya tidak berubah."
                    duplicate_count += 1
                else:
                    status = "update"
                    status_label = "↻ Akan Diupdate"
                    keterangan = "Username sudah ada. NPK, Nama, atau Role akan diperbarui sesuai Excel."
                    update_count += 1

            else:

                status = "valid"

                status_label = "✓ Siap Import"

                keterangan = (
                    "Siap dimasukkan."
                )

                valid_count += 1


        except Exception as error:

            status = "error"

            status_label = "✕ Error"

            keterangan = str(error)

            error_count += 1


        # =====================================================
        # TAMBAHKAN BARIS
        # =====================================================

        rows.append({

            "row": excel_row,

            "npk": npk,

            "username": nickname,

            "full_name": nama,

            "role_excel": role_excel,

            "role": role,

            "status": status,

            "status_label": status_label,

            "keterangan": keterangan

        })


    # ========================================================
    # HASIL
    # ========================================================

    return {

        "rows": rows,

        "total": len(df),

        "valid": valid_count,

        "duplicate": duplicate_count,

        "update": update_count,

        "error": error_count

    }


# ============================================================
# HALAMAN IMPORT MEMBER
# ============================================================

@import_members_bp.route(
    "/",
    methods=["GET"]
)
@role_required("admin", "maris")
def import_members():

    members = (
        User.query
        .order_by(User.role.asc(), User.nickname.asc())
        .all()
    )

    return render_template(
        "import_members.html",
        members=members
    )


# ============================================================
# UPDATE ROLE MEMBER
# ============================================================

@import_members_bp.route(
    "/member/<int:user_id>/role",
    methods=["POST"]
)
@role_required("admin")
def update_member_role(user_id):

    member = User.query.get(user_id)
    role = (request.form.get("role") or "").strip().lower()

    if not member:
        flash("Member tidak ditemukan.", "error")
        return redirect(url_for("import_members.import_members"))

    if role not in set(ROLE_MAPPING.values()):
        flash("Role tidak valid.", "error")
        return redirect(url_for("import_members.import_members"))

    current_user = User.query.get(session.get("user_id"))
    if current_user and current_user.id == member.id and role != "admin":
        flash("Account admin yang sedang digunakan tidak boleh menurunkan role dirinya sendiri.", "error")
        return redirect(url_for("import_members.import_members"))

    old_role = member.role
    member.role = role

    try:
        db.session.commit()
        flash(f"Role {member.username} berhasil diubah dari {old_role.upper()} menjadi {role.upper()}.", "success")
    except Exception as error:
        db.session.rollback()
        flash(f"Gagal mengubah role: {error}", "error")

    return redirect(url_for("import_members.import_members"))


# ============================================================
# DELETE MEMBER
# ============================================================

@import_members_bp.route(
    "/member/<int:user_id>/delete",
    methods=["POST"]
)
@role_required("admin")
def delete_member(user_id):

    member = User.query.get(user_id)

    if not member:
        flash("Member tidak ditemukan.", "error")
        return redirect(url_for("import_members.import_members"))

    current_user = User.query.get(session.get("user_id"))
    if current_user and current_user.id == member.id:
        flash("Account yang sedang login tidak dapat dihapus.", "error")
        return redirect(url_for("import_members.import_members"))

    username = member.username

    try:
        db.session.delete(member)
        db.session.commit()
        flash(f"Member {username} berhasil dihapus dari database.", "success")
    except Exception as error:
        db.session.rollback()
        flash(f"Gagal menghapus member: {error}", "error")

    return redirect(url_for("import_members.import_members"))




# ============================================================
# DOWNLOAD DATA MEMBER (ADMIN APLIKASI ONLY)
# ============================================================

@import_members_bp.route("/download", methods=["GET"])
@role_required("admin")
def download_members():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    members = User.query.order_by(User.role.asc(), User.full_name.asc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Member"

    headers = ["No", "NPK", "Username", "Nickname", "Nama Lengkap", "Role", "Status", "Created At", "Last Login"]
    ws.append(headers)
    header_fill = PatternFill("solid", fgColor="1E4F7B")
    thin = Side(style="thin", color="D7E0EA")
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(bottom=thin)

    for no, member in enumerate(members, 1):
        ws.append([
            no, member.npk, member.username, member.nickname or "", member.full_name,
            member.role, "Aktif" if member.is_active else "Nonaktif",
            member.created_at.strftime("%d-%m-%Y %H:%M") if member.created_at else "",
            member.last_login_at.strftime("%d-%m-%Y %H:%M") if member.last_login_at else ""
        ])

    widths = [7, 14, 20, 20, 30, 14, 12, 20, 20]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64+i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Data_Member_Crushing_App.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ============================================================
# PREVIEW EXCEL
# ============================================================

@import_members_bp.route(
    "/preview",
    methods=["POST"]
)
@role_required("admin", "maris")
def import_members_preview():

    # ========================================================
    # CEK FILE
    # ========================================================

    file = request.files.get(
        "file"
    )


    if not file:

        flash(
            "File Excel belum dipilih.",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    if not file.filename:

        flash(
            "Nama file tidak ditemukan.",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # CEK EXTENSION
    # ========================================================

    if not allowed_file(
        file.filename
    ):

        flash(
            "File harus berupa Excel "
            "(.xlsx atau .xls).",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # SIMPAN FILE
    # ========================================================

    upload_folder = (
        get_upload_folder()
    )


    original_filename = secure_filename(
        file.filename
    )


    unique_filename = (
        f"{uuid.uuid4().hex}_"
        f"{original_filename}"
    )


    filepath = os.path.join(
        upload_folder,
        unique_filename
    )


    try:

        file.save(
            filepath
        )

    except Exception as error:

        flash(
            f"Gagal menyimpan file: {error}",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # BACA EXCEL
    # ========================================================

    try:

        df = read_excel_file(
            filepath
        )

    except Exception as error:

        try:

            if os.path.exists(filepath):
                os.remove(filepath)

        except Exception:
            pass


        flash(
            str(error),
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # BUAT PREVIEW
    # ========================================================

    try:

        preview = build_preview(
            df
        )

    except Exception as error:

        try:

            if os.path.exists(filepath):
                os.remove(filepath)

        except Exception:
            pass


        flash(
            f"Gagal membuat preview: {error}",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # SIMPAN PATH FILE KE SESSION
    #
    # File BELUM masuk database.
    # Hanya disimpan sebagai file temporary.
    # ========================================================

    session[
        "import_members_file"
    ] = unique_filename


    session[
        "import_members_original_name"
    ] = original_filename


    # ========================================================
    # TAMPILKAN PREVIEW
    # ========================================================

    return render_template(

        "import_members.html",

        previewed=True,

        filename=original_filename,

        rows=preview["rows"],

        total=preview["total"],

        valid=preview["valid"],

        duplicate=preview["duplicate"],

        error=preview["error"],

        members=(User.query.order_by(User.role.asc(), User.nickname.asc()).all())

    )


# ============================================================
# IMPORT KE DATABASE
# ============================================================

@import_members_bp.route(
    "/import",
    methods=["POST"]
)
@role_required("admin", "maris")
def import_members_process():

    # ========================================================
    # AMBIL FILE DARI SESSION
    # ========================================================

    stored_filename = session.get(
        "import_members_file"
    )


    original_filename = session.get(
        "import_members_original_name",
        "Excel Member"
    )


    if not stored_filename:

        flash(
            "Session import sudah berakhir. "
            "Silakan upload Excel kembali.",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # PATH FILE
    # ========================================================

    upload_folder = (
        get_upload_folder()
    )


    filepath = os.path.join(
        upload_folder,
        stored_filename
    )


    # ========================================================
    # CEK FILE
    # ========================================================

    if not os.path.exists(filepath):

        session.pop(
            "import_members_file",
            None
        )

        session.pop(
            "import_members_original_name",
            None
        )


        flash(
            "File temporary tidak ditemukan. "
            "Silakan upload Excel kembali.",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # BACA ULANG EXCEL
    # ========================================================

    try:

        df = read_excel_file(
            filepath
        )

    except Exception as error:

        flash(
            str(error),
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # COUNTER
    # ========================================================

    inserted = 0
    updated = 0
    skipped = 0
    failed = 0

    errors = []

    seen_usernames = set()


    # ========================================================
    # IMPORT DATABASE
    # ========================================================

    try:

        for index, row in df.iterrows():

            excel_row = index + 2

            nickname = ""
            npk = ""
            nama = ""
            role_excel = ""

            try:

                # =================================================
                # AMBIL DATA
                # =================================================

                nickname = str(
                    row["NICKNAME"]
                ).strip()

                npk = normalize_npk(
                    row["NPK"]
                )

                nama = str(
                    row["NAMA"]
                ).strip()

                role_excel = str(
                    row["ROLE"]
                ).strip()


                # =================================================
                # VALIDASI
                # =================================================

                if not nickname:

                    raise ValueError(
                        "NICKNAME kosong"
                    )


                if not npk:

                    raise ValueError(
                        "NPK kosong"
                    )


                if not nama:

                    raise ValueError(
                        "NAMA kosong"
                    )


                if not role_excel:

                    raise ValueError(
                        "ROLE kosong"
                    )


                # =================================================
                # ROLE
                # =================================================

                role = normalize_excel_role(
                    role_excel
                )


                if not role:

                    raise ValueError(
                        f"ROLE tidak dikenali: "
                        f"{role_excel}"
                    )


                # =================================================
                # USERNAME
                # =================================================

                username = nickname

                username_key = (
                    username.lower()
                )


                # =================================================
                # DUPLICATE DALAM EXCEL
                # =================================================

                if username_key in seen_usernames:

                    skipped += 1

                    continue


                seen_usernames.add(
                    username_key
                )


                # =================================================
                # CEK DATABASE
                # =================================================

                existing_user = (
                    User.query
                    .filter_by(
                        username=username
                    )
                    .first()
                )


                if existing_user:

                    same_data = (
                        str(existing_user.npk or "").strip() == npk
                        and str(existing_user.full_name or "").strip() == nama
                        and str(existing_user.role or "").strip().lower() == role
                    )

                    if same_data:
                        skipped += 1
                        continue

                    # Update account yang sudah ada. Password existing
                    # dipertahankan agar perubahan master member tidak
                    # diam-diam mereset password pengguna.
                    existing_user.npk = npk
                    existing_user.full_name = nama
                    existing_user.role = role
                    existing_user.is_active = True
                    updated += 1
                    continue


                # =================================================
                # BUAT USER BARU
                # =================================================

                user = User(
                    username=username,
                    full_name=nama,
                    password_hash=generate_password_hash(npk),
                    role=role,
                    is_active=True
                )
                user.npk = npk

                if hasattr(User, "created_at"):
                    from datetime import datetime
                    user.created_at = datetime.now()

                db.session.add(user)
                inserted += 1


            except Exception as error:

                failed += 1

                errors.append({

                    "row": excel_row,

                    "nickname": nickname,

                    "error": str(error)

                })


        # ========================================================
        # COMMIT
        # ========================================================

        db.session.commit()


    except Exception as error:

        db.session.rollback()

        flash(
            f"Import gagal dan database "
            f"tidak diubah: {error}",
            "error"
        )

        return redirect(
            url_for(
                "import_members.import_members"
            )
        )


    # ========================================================
    # HAPUS SESSION
    # ========================================================

    session.pop(
        "import_members_file",
        None
    )

    session.pop(
        "import_members_original_name",
        None
    )


    # ========================================================
    # HAPUS FILE TEMPORARY
    # ========================================================

    try:

        if os.path.exists(filepath):

            os.remove(
                filepath
            )

    except Exception:

        pass


    # ========================================================
    # TAMPILKAN HASIL
    # ========================================================

    return render_template(

        "import_members.html",

        imported=True,

        filename=original_filename,

        total=len(df),

        inserted=inserted,

        updated=updated,

        skipped=skipped,

        failed=failed,

        errors=errors,

        members=(User.query.order_by(User.role.asc(), User.nickname.asc()).all())

    )