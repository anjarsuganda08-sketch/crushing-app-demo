from flask import (
    Blueprint,
    render_template,
    request,
    send_file
)

from routes.auth import role_required

from database.models import (
    CrushingTicket,
    CrushingTransaction
)

from datetime import (
    datetime,
    time
)

from io import BytesIO

from openpyxl import Workbook

from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side
)


# ==========================================================
# BLUEPRINT
# ==========================================================

export_crushing_bp = Blueprint(
    "export_crushing",
    __name__,
    url_prefix="/export-crushing"
)


# ==========================================================
# KONSTANTA REPORT
# ==========================================================

SECTION_NAME = "ASSEMBLY"

SUB_SECTION_NAME = "SFG"



# ==========================================================
# FUNGSI MENENTUKAN SHIFT LAPORAN PERUSAHAAN
# ==========================================================
#
# Shift Group operator:
#
# A / B
#
# Tetap digunakan untuk filter pada halaman Export.
#
#
# Shift laporan perusahaan:
#
# 08:00 - 20:30 = Shift 1
# 20:31 - 07:59 = Shift 3
#
#
# Penentuan Shift laporan dilakukan berdasarkan:
#
# CrushingTicket.created_at
#
# BUKAN berdasarkan:
#
# ticket.shift
#
# dan BUKAN berdasarkan waktu Admin MARIS.
# ==========================================================

def get_report_shift(created_at):

    if not created_at:

        return ""


    transaction_time = (
        created_at.time()
    )


    # ======================================================
    # SHIFT 1
    #
    # 08:00 sampai 20:30
    # ======================================================

    if (
        transaction_time >= time(8, 0)
        and
        transaction_time <= time(20, 30)
    ):

        return "1"


    # ======================================================
    # SHIFT 3
    #
    # 20:31 sampai 07:59
    #
    # Termasuk:
    #
    # 20:31 - 23:59
    # 00:00 - 07:59
    # ======================================================

    return "3"


# ==========================================================
# FUNGSI FORMAT TANGGAL
# ==========================================================
#
# Export perusahaan hanya membutuhkan tanggal.
#
# Contoh:
#
# 23-08-2026
#
# Bukan:
#
# 23-08-2026 15:30
#
# ==========================================================

def format_report_date(created_at):

    if not created_at:

        return ""


    return created_at.strftime(
        "%d-%m-%Y"
    )


# ==========================================================
# FUNGSI AMBIL DATA EXPORT
# ==========================================================

def get_export_data(
    start_date=None,
    end_date=None,
    selected_line="",
    selected_shift=""
):

    # ======================================================
    # QUERY UTAMA
    # ======================================================

    query = (
        CrushingTransaction.query
        .join(
            CrushingTicket,
            CrushingTransaction.ticket_id ==
            CrushingTicket.id
        )
        .filter(
            CrushingTicket.status ==
            "MARIS Completed"
        )
    )


    # ======================================================
    # FILTER TANGGAL AWAL
    #
    # Berdasarkan:
    #
    # CrushingTicket.created_at
    # ======================================================

    if start_date:

        start_datetime = datetime.combine(
            start_date,
            time.min
        )


        query = query.filter(

            CrushingTicket.created_at >=
            start_datetime

        )


    # ======================================================
    # FILTER TANGGAL AKHIR
    # ======================================================

    if end_date:

        end_datetime = datetime.combine(
            end_date,
            time.max
        )


        query = query.filter(

            CrushingTicket.created_at <=
            end_datetime

        )


    # ======================================================
    # FILTER LINE
    # ======================================================

    if selected_line:

        query = query.filter(

            CrushingTicket.line ==
            selected_line

        )


    # ======================================================
    # FILTER SHIFT GROUP OPERATOR
    #
    # PENTING:
    #
    # Filter ini tetap menggunakan:
    #
    # A / B
    #
    # karena Shift Group tetap digunakan
    # dalam aplikasi operator.
    #
    # Yang diubah menjadi Shift 1/3
    # hanya kolom Shift pada hasil Excel.
    # ======================================================

    if selected_shift:

        query = query.filter(

            CrushingTicket.shift ==
            selected_shift

        )


    # ======================================================
    # URUTKAN DATA
    # ======================================================

    transactions = (

        query

        .order_by(

            CrushingTicket.created_at.asc(),

            CrushingTicket.id.asc(),

            CrushingTransaction.id.asc()

        )

        .all()

    )


    return transactions


# ==========================================================
# HALAMAN EXPORT
# ==========================================================

@export_crushing_bp.route(
    "/",
    methods=["GET", "POST"]
)
@role_required("admin", "maris")
def export_crushing():

    error_message = ""

    preview_data = []


    # ======================================================
    # DEFAULT TANGGAL
    # ======================================================

    today = datetime.now().date()


    start_date_value = (
        today.strftime(
            "%Y-%m-%d"
        )
    )


    end_date_value = (
        today.strftime(
            "%Y-%m-%d"
        )
    )


    selected_line = ""

    selected_shift = ""


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
        # AMBIL INPUT TANGGAL AWAL
        # ==================================================

        start_date_value = (

            request.form.get(
                "start_date"
            )
            or
            ""

        ).strip()


        # ==================================================
        # AMBIL INPUT TANGGAL AKHIR
        # ==================================================

        end_date_value = (

            request.form.get(
                "end_date"
            )
            or
            ""

        ).strip()


        # ==================================================
        # AMBIL INPUT LINE
        # ==================================================

        selected_line = (

            request.form.get(
                "line"
            )
            or
            ""

        ).strip()


        # ==================================================
        # AMBIL INPUT SHIFT GROUP
        # ==================================================

        selected_shift = (

            request.form.get(
                "shift"
            )
            or
            ""

        ).strip()


        # ==================================================
        # VALIDASI TANGGAL
        # ==================================================

        start_date = None

        end_date = None


        # ==================================================
        # VALIDASI TANGGAL AWAL
        # ==================================================

        if start_date_value:

            try:

                start_date = datetime.strptime(

                    start_date_value,

                    "%Y-%m-%d"

                ).date()


            except ValueError:

                error_message = (
                    "Format tanggal awal "
                    "tidak valid."
                )


        # ==================================================
        # VALIDASI TANGGAL AKHIR
        # ==================================================

        if (
            not error_message
            and
            end_date_value
        ):

            try:

                end_date = datetime.strptime(

                    end_date_value,

                    "%Y-%m-%d"

                ).date()


            except ValueError:

                error_message = (
                    "Format tanggal akhir "
                    "tidak valid."
                )


        # ==================================================
        # VALIDASI RANGE TANGGAL
        # ==================================================

        if (

            not error_message

            and

            start_date

            and

            end_date

            and

            start_date > end_date

        ):

            error_message = (

                "Tanggal awal tidak boleh "
                "lebih besar dari tanggal akhir."

            )


        # ==================================================
        # AMBIL DATA
        # ==================================================

        if not error_message:

            transactions = get_export_data(

                start_date=start_date,

                end_date=end_date,

                selected_line=selected_line,

                selected_shift=selected_shift

            )


            # ==================================================
            # PREVIEW
            # ==================================================

            for trx in transactions:

                ticket = trx.ticket


                # ==============================================
                # SHIFT LAPORAN
                # ==============================================

                report_shift = (
                    get_report_shift(
                        ticket.created_at
                    )
                )


                # ==============================================
                # TANGGAL LAPORAN
                # ==============================================

                transaction_date = (
                    format_report_date(
                        ticket.created_at
                    )
                )


                # ==============================================
                # HARGA PER PCS
                # ==============================================

                price_per_pcs = float(
                    trx.price or 0
                )


                # ==============================================
                # QUANTITY
                # ==============================================

                quantity = int(
                    trx.quantity or 0
                )


                # ==============================================
                # TOTAL PRICE
                #
                # Harga PCS × Quantity
                #
                # Contoh:
                #
                # 500 × 5 = 2500
                # ==============================================

                total_price = (

                    price_per_pcs
                    *
                    quantity

                )


                preview_data.append({

                    "ticket_number":
                        ticket.ticket_number,

                    "operator_npk":
                        ticket.operator_npk or "",

                    "operator_name":
                        ticket.operator_name or "",

                    "line":
                        ticket.line,

                    # Shift Group A/B
                    "shift":
                        ticket.shift,

                    # Shift laporan 1/3
                    "report_shift":
                        report_shift,

                    "remark":
                        ticket.remarks or "",

                    "part_number":
                        trx.part_number,

                    "part_name":
                        trx.part_name,

                    "quantity":
                        quantity,

                    "maris_transaction_number":
                        ticket.maris_transaction_number or "",

                    "jenis_ng":
                        trx.jenis_ng or "",

                    "created_at":
                        ticket.created_at,

                    "transaction_date":
                        transaction_date,

                    "price":
                        price_per_pcs,

                    "total_price":
                        total_price

                })


            # ==================================================
            # EXPORT EXCEL
            # ==================================================

            if action == "export_excel":

                return generate_excel(

                    transactions=transactions,

                    start_date=start_date,

                    end_date=end_date

                )


    # ======================================================
    # MASTER LINE
    # ======================================================

    line_rows = (

        CrushingTicket.query

        .with_entities(
            CrushingTicket.line
        )

        .filter(
            CrushingTicket.line.isnot(None)
        )

        .distinct()

        .order_by(
            CrushingTicket.line
        )

        .all()

    )


    lines = [

        row.line

        for row in line_rows

    ]


    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "export_crushing.html",

        preview_data=preview_data,

        lines=lines,

        selected_line=selected_line,

        selected_shift=selected_shift,

        start_date=start_date_value,

        end_date=end_date_value,

        section_name=SECTION_NAME,

        sub_section_name=SUB_SECTION_NAME,

        error_message=error_message

    )


# ==========================================================
# GENERATE EXCEL
# ==========================================================

def generate_excel(
    transactions,
    start_date=None,
    end_date=None
):

    # ======================================================
    # BUAT WORKBOOK
    # ======================================================

    workbook = Workbook()


    worksheet = (
        workbook.active
    )


    worksheet.title = (
        "Download"
    )


    # ======================================================
    # HEADER SESUAI FORMAT PERUSAHAAN
    # ======================================================

    headers = [

        "NIK",

        "OPERATOR NAME",

        "TGL TRANSAKSI",

        "Shift",

        "NO CRUSHING TICKET",

        "MESIN / LINE",

        "REMARK",

        "PART NO",

        "PART NAME",

        "QTY PER JENIS",

        "NO TRANSAKSI",

        "KLASIFIKASI NG",

        "JENIS NG",

        "SECTION",

        "SUB SECTION",

        "PERIODE",

        "PRICE"

    ]


    worksheet.append(
        headers
    )


    # ======================================================
    # STYLE HEADER
    # ======================================================

    header_fill = PatternFill(

        fill_type="solid",

        fgColor="1F4E78"

    )


    header_font = Font(

        color="FFFFFF",

        bold=True

    )


    thin_border = Border(

        left=Side(

            style="thin",

            color="D9E1F2"

        ),

        right=Side(

            style="thin",

            color="D9E1F2"

        ),

        top=Side(

            style="thin",

            color="D9E1F2"

        ),

        bottom=Side(

            style="thin",

            color="D9E1F2"

        )

    )


    for cell in worksheet[1]:

        cell.fill = (
            header_fill
        )


        cell.font = (
            header_font
        )


        cell.alignment = Alignment(

            horizontal="center",

            vertical="center",

            wrap_text=True

        )


        cell.border = (
            thin_border
        )


    # ======================================================
    # DATA
    # ======================================================

    for trx in transactions:

        ticket = trx.ticket


        # ==================================================
        # WAKTU TRANSAKSI
        #
        # Sumber:
        #
        # CrushingTicket.created_at
        # ==================================================

        transaction_datetime = (
            ticket.created_at
        )


        # ==================================================
        # TANGGAL TRANSAKSI
        #
        # HANYA TANGGAL
        # ==================================================

        if transaction_datetime:

            transaction_date = (
                transaction_datetime.strftime(
                    "%d-%m-%Y"
                )
            )

        else:

            transaction_date = ""


        # ==================================================
        # SHIFT LAPORAN
        #
        # OTOMATIS:
        #
        # 08:00 - 20:30 = 1
        # 20:31 - 07:59 = 3
        # ==================================================

        report_shift = (
            get_report_shift(
                transaction_datetime
            )
        )


        # ==================================================
        # PERIODE
        # ==================================================

        if transaction_datetime:

            periode = (
                transaction_datetime.strftime(
                    "%Y-%m"
                )
            )

        else:

            periode = ""


        # ==================================================
        # QUANTITY
        # ==================================================

        quantity = int(
            trx.quantity or 0
        )


        # ==================================================
        # HARGA PER PCS
        #
        # Data pada trx.price merupakan
        # harga satuan.
        # ==================================================

        price_per_pcs = float(
            trx.price or 0
        )


        # ==================================================
        # TOTAL PRICE
        #
        # Harga/PCS × Qty
        #
        # Contoh:
        #
        # Harga = 500
        # Qty   = 5
        #
        # PRICE = 2.500
        # ==================================================

        total_price = (

            price_per_pcs
            *
            quantity

        )


        # ==================================================
        # ROW
        # ==================================================

        row = [

            # ==============================================
            # A - NIK
            # ==============================================
            # Identitas operator disimpan sebagai snapshot
            # pada saat ticket dibuat.
            # ==============================================

            ticket.operator_npk or "",


            # ==============================================
            # B - OPERATOR NAME
            # ==============================================

            ticket.operator_name or "",


            # ==============================================
            # C - TGL TRANSAKSI
            #
            # HANYA TANGGAL
            # ==============================================

            transaction_date,


            # ==============================================
            # D - SHIFT
            #
            # BUKAN A/B
            #
            # Menggunakan Shift 1/3
            # berdasarkan waktu transaksi.
            # ==============================================

            report_shift,


            # ==============================================
            # E - NO CRUSHING TICKET
            # ==============================================

            ticket.ticket_number,


            # ==============================================
            # F - MESIN / LINE
            # ==============================================

            ticket.line,


            # ==============================================
            # G - REMARK
            # ==============================================

            ticket.remarks or "",


            # ==============================================
            # H - PART NO
            # ==============================================

            trx.part_number,


            # ==============================================
            # I - PART NAME
            # ==============================================

            trx.part_name,


            # ==============================================
            # J - QTY PER JENIS
            # ==============================================

            quantity,


            # ==============================================
            # K - NO TRANSAKSI
            # ==============================================

            ticket.maris_transaction_number or "",


            # ==============================================
            # L - KLASIFIKASI NG
            # ==============================================

            ticket.remarks or "",


            # ==============================================
            # M - JENIS NG
            # ==============================================

            trx.jenis_ng or "",


            # ==============================================
            # N - SECTION
            # ==============================================

            SECTION_NAME,


            # ==============================================
            # O - SUB SECTION
            # ==============================================

            SUB_SECTION_NAME,


            # ==============================================
            # P - PERIODE
            # ==============================================

            periode,


            # ==============================================
            # Q - PRICE
            #
            # Harga sudah dikalikan quantity.
            # ==============================================

            total_price

        ]


        # ==================================================
        # TAMBAHKAN ROW
        # ==================================================

        worksheet.append(
            row
        )


    # ======================================================
    # STYLE DATA
    # ======================================================

    for row in worksheet.iter_rows(
        min_row=2
    ):

        for cell in row:

            cell.border = (
                thin_border
            )


            cell.alignment = Alignment(

                vertical="center",

                wrap_text=True

            )


    # ======================================================
    # FORMAT TANGGAL
    #
    # Kolom C
    #
    # Karena tanggal sudah berupa string
    # dd-mm-yyyy, Excel tidak akan menampilkan
    # jam.
    # ======================================================

    for cell in worksheet["C"][1:]:

        if cell.value:

            cell.number_format = (
                "dd-mm-yyyy"
            )


    # ======================================================
    # FORMAT QUANTITY
    #
    # Kolom J
    # ======================================================

    for cell in worksheet["J"][1:]:

        if cell.value is not None:

            cell.number_format = (
                '#,##0'
            )


    # ======================================================
    # FORMAT PRICE
    #
    # Kolom Q
    #
    # Contoh:
    #
    # 2500
    #
    # Ditampilkan sebagai:
    #
    # 2,500
    #
    # Sesuai format angka Excel.
    # ======================================================

    for cell in worksheet["Q"][1:]:

        if cell.value is not None:

            cell.number_format = (
                '#,##0'
            )


    # ======================================================
    # FREEZE HEADER
    # ======================================================

    worksheet.freeze_panes = (
        "A2"
    )


    # ======================================================
    # AUTO FILTER
    # ======================================================

    if worksheet.max_row >= 2:

        worksheet.auto_filter.ref = (
            worksheet.dimensions
        )


    # ======================================================
    # LEBAR KOLOM
    # ======================================================

    column_widths = {

        "A": 14,

        "B": 22,

        "C": 16,

        "D": 10,

        "E": 25,

        "F": 18,

        "G": 20,

        "H": 22,

        "I": 35,

        "J": 15,

        "K": 22,

        "L": 20,

        "M": 25,

        "N": 15,

        "O": 15,

        "P": 15,

        "Q": 18

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
        1
    ].height = 30


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

    if (
        start_date
        and
        end_date
    ):

        # ==============================================
        # SATU HARI
        # ==============================================

        if start_date == end_date:

            filename = (

                "Crushing_"

                +
                start_date.strftime(
                    "%Y%m%d"
                )

                +
                ".xlsx"

            )


        # ==============================================
        # RANGE TANGGAL
        # ==============================================

        else:

            filename = (

                "Crushing_"

                +
                start_date.strftime(
                    "%Y%m%d"
                )

                +
                "_"

                +
                end_date.strftime(
                    "%Y%m%d"
                )

                +
                ".xlsx"

            )


    else:

        filename = (
            "Crushing_Export.xlsx"
        )


    # ======================================================
    # DOWNLOAD
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