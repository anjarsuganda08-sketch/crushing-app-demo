from flask import (
    Blueprint,
    render_template,
    request,
    send_file
)

from sqlalchemy import or_

from datetime import datetime, timedelta

from io import BytesIO

from openpyxl import Workbook

from openpyxl.styles import (
    Font,
    Alignment,
    PatternFill,
    Border,
    Side
)

from openpyxl.utils import get_column_letter

from openpyxl.worksheet.page import PageMargins

from routes.auth import role_required

from database.models import (
    CrushingTicket,
    CrushingTransaction
)


# =====================================================
# BLUEPRINT
# =====================================================

pulling_bp = Blueprint(
    "pulling",
    __name__
)


# =====================================================
# HALAMAN OPERATOR PULLING
# =====================================================

@pulling_bp.route("/pulling")
@role_required("pulling", "admin")
def pulling():

    # =====================================
    # FILTER
    # =====================================

    selected_line = request.args.get(
        "line",
        ""
    )

    selected_status = request.args.get(
        "status",
        "Pending Pulling"
    )

    search = request.args.get(
        "search",
        ""
    )


    # =====================================
    # QUERY TICKET
    # =====================================

    query = CrushingTicket.query


    # =====================================
    # FILTER LINE
    # =====================================

    if selected_line:

        query = query.filter(
            CrushingTicket.line == selected_line
        )


    # =====================================
    # FILTER STATUS
    # =====================================

    if selected_status != "All":

        query = query.filter(
            CrushingTicket.status == selected_status
        )


    # =====================================
    # SEARCH
    # =====================================

    if search:

        query = query.filter(

            or_(

                CrushingTicket.ticket_number.contains(
                    search
                ),

                CrushingTicket.line.contains(
                    search
                )

            )

        )


    # =====================================
    # AMBIL DATA TICKET
    # =====================================

    tickets = (

        query

        .order_by(
            CrushingTicket.created_at.desc()
        )

        .all()
    )


    # =====================================
    # PREVIEW PART
    # =====================================

    for ticket in tickets:

        preview_items = (

            CrushingTransaction.query

            .filter(
                CrushingTransaction.ticket_id
                == ticket.id
            )

            .order_by(
                CrushingTransaction.id.asc()
            )

            .limit(5)

            .all()
        )


        total_item = (

            CrushingTransaction.query

            .filter(
                CrushingTransaction.ticket_id
                == ticket.id
            )

            .count()
        )


        ticket.preview_items = preview_items

        ticket.more_items = max(
            0,
            total_item - 5
        )


    # =====================================
    # SUMMARY
    # =====================================

    summary_query = CrushingTicket.query


    # =====================================
    # FILTER LINE UNTUK SUMMARY
    # =====================================

    if selected_line:

        summary_query = summary_query.filter(
            CrushingTicket.line == selected_line
        )


    # =====================================
    # TOTAL TICKET
    # =====================================

    total_ticket = (
        summary_query.count()
    )


    # =====================================
    # PENDING PULLING
    # =====================================

    pending_count = (

        summary_query

        .filter(
            CrushingTicket.status
            == "Pending Pulling"
        )

        .count()
    )


    # =====================================
    # NEED LEADER
    # =====================================

    leader_count = (

        summary_query

        .filter(
            CrushingTicket.status
            == "Need Leader Confirmation"
        )

        .count()
    )


    # =====================================
    # APPROVED
    # =====================================

    approved_count = (

        summary_query

        .filter(
            CrushingTicket.status
            == "Approved"
        )

        .count()
    )


    # =====================================
    # AMBIL DAFTAR LINE
    # =====================================

    lines = (

        CrushingTicket.query

        .with_entities(
            CrushingTicket.line
        )

        .distinct()

        .order_by(
            CrushingTicket.line.asc()
        )

        .all()
    )


    # =====================================
    # RENDER
    # =====================================

    return render_template(

        "pulling.html",

        tickets=tickets,

        lines=lines,

        selected_line=selected_line,

        selected_status=selected_status,

        search=search,

        total_ticket=total_ticket,

        pending_count=pending_count,

        leader_count=leader_count,

        approved_count=approved_count

    )


# =====================================================
# DOWNLOAD LIST PULLING HARI INI
#
# FUNGSI:
# 1 TICKET = 1 BARIS
#
# Dokumen digunakan sebagai:
# CONTROL LIST TICKET FISIK
#
# Hanya ticket:
# STATUS = Approved
# =====================================================

@pulling_bp.route(
    "/pulling/download-today"
)
@role_required(
    "pulling",
    "admin"
)
def download_today():

    # =================================================
    # TANGGAL HARI INI
    # =================================================

    today = datetime.now().date()

    start_today = datetime.combine(
        today,
        datetime.min.time()
    )

    tomorrow = (
        start_today
        + timedelta(days=1)
    )


    # =================================================
    # AMBIL TICKET SELESAI PULLING
    #
    # HANYA APPROVED
    # =================================================

    tickets = (

        CrushingTicket.query

        .filter(

            CrushingTicket.created_at
            >= start_today,

            CrushingTicket.created_at
            < tomorrow,

            CrushingTicket.status
            == "Approved"

        )

        .order_by(

            CrushingTicket.created_at.asc(),

            CrushingTicket.id.asc()

        )

        .all()

    )


    # =================================================
    # HITUNG TOTAL TICKET
    # =================================================

    total_ticket = len(
        tickets
    )


    # =================================================
    # HITUNG TOTAL PART
    #
    # TOTAL PART = TOTAL QTY
    # DARI SELURUH TICKET
    # =================================================

    total_part = 0


    ticket_part_totals = {}


    for ticket in tickets:

        part_total = 0

        transactions = (

            CrushingTransaction.query

            .filter(
                CrushingTransaction.ticket_id
                == ticket.id
            )

            .all()

        )


        for item in transactions:

            quantity = (
                item.quantity
                or 0
            )

            part_total += quantity


        ticket_part_totals[
            ticket.id
        ] = part_total


        total_part += part_total


    # =================================================
    # BUAT WORKBOOK
    # =================================================

    workbook = Workbook()

    worksheet = (
        workbook.active
    )

    worksheet.title = (
        "List Pulling"
    )


    # =================================================
    # WARNA
    # =================================================

    dark_blue = "17365D"

    medium_blue = "1F4E78"

    light_blue = "D9EAF7"

    orange = "F59E0B"

    light_orange = "FFF2CC"

    green = "E2F0D9"

    border_color = "9EADBA"

    white = "FFFFFF"

    black = "1F2937"

    gray = "6B7280"


    # =================================================
    # BORDER
    # =================================================

    thin_side = Side(
        style="thin",
        color=border_color
    )

    medium_side = Side(
        style="medium",
        color=dark_blue
    )

    thin_border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side
    )


    # =================================================
    # PAGE SETTING
    # =================================================

    worksheet.page_setup.orientation = (
        "landscape"
    )

    worksheet.page_setup.paperSize = (
        worksheet.PAPERSIZE_A4
    )

    worksheet.page_setup.fitToWidth = 1

    worksheet.page_setup.fitToHeight = 0

    worksheet.sheet_properties.pageSetUpPr.fitToPage = True

    worksheet.page_margins = PageMargins(
        left=0.25,
        right=0.25,
        top=0.40,
        bottom=0.40,
        header=0.20,
        footer=0.20
    )


    # =================================================
    # JUDUL
    # =================================================

    worksheet.merge_cells(
        "A1:H1"
    )

    worksheet["A1"] = (
        "LIST PULLING HARIAN"
    )

    worksheet["A1"].font = Font(
        bold=True,
        size=18,
        color=white
    )

    worksheet["A1"].fill = PatternFill(
        "solid",
        fgColor=dark_blue
    )

    worksheet["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    worksheet.row_dimensions[1].height = 30


    # =================================================
    # INFORMASI TANGGAL
    # =================================================

    worksheet.merge_cells(
        "A2:B2"
    )

    worksheet["A2"] = (
        "Tanggal"
    )

    worksheet["A2"].font = Font(
        bold=True,
        color=black
    )

    worksheet["A2"].fill = PatternFill(
        "solid",
        fgColor=light_blue
    )

    worksheet["A2"].border = (
        thin_border
    )

    worksheet["A2"].alignment = Alignment(
        vertical="center"
    )


    worksheet.merge_cells(
        "C2:D2"
    )

    worksheet["C2"] = (
        today.strftime(
            "%d-%m-%Y"
        )
    )

    worksheet["C2"].font = Font(
        bold=True,
        color=black
    )

    worksheet["C2"].border = (
        thin_border
    )

    worksheet["C2"].alignment = Alignment(
        horizontal="left",
        vertical="center"
    )


    # =================================================
    # TOTAL TICKET
    # =================================================

    worksheet.merge_cells(
        "E2:F2"
    )

    worksheet["E2"] = (
        "Total Ticket"
    )

    worksheet["E2"].font = Font(
        bold=True,
        color=black
    )

    worksheet["E2"].fill = PatternFill(
        "solid",
        fgColor=light_blue
    )

    worksheet["E2"].border = (
        thin_border
    )


    worksheet.merge_cells(
        "G2:H2"
    )

    worksheet["G2"] = (
        total_ticket
    )

    worksheet["G2"].font = Font(
        bold=True,
        size=13,
        color=dark_blue
    )

    worksheet["G2"].border = (
        thin_border
    )

    worksheet["G2"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


    # =================================================
    # TOTAL PART
    # =================================================

    worksheet.merge_cells(
        "A3:B3"
    )

    worksheet["A3"] = (
        "Total Part"
    )

    worksheet["A3"].font = Font(
        bold=True,
        color=black
    )

    worksheet["A3"].fill = PatternFill(
        "solid",
        fgColor=light_blue
    )

    worksheet["A3"].border = (
        thin_border
    )


    worksheet.merge_cells(
        "C3:D3"
    )

    worksheet["C3"] = (
        total_part
    )

    worksheet["C3"].font = Font(
        bold=True,
        size=13,
        color=dark_blue
    )

    worksheet["C3"].border = (
        thin_border
    )

    worksheet["C3"].alignment = Alignment(
        horizontal="left",
        vertical="center"
    )


    # =================================================
    # OPERATOR PULLING
    # =================================================

    worksheet.merge_cells(
        "E3:F3"
    )

    worksheet["E3"] = (
        "Operator Pulling"
    )

    worksheet["E3"].font = Font(
        bold=True,
        color=black
    )

    worksheet["E3"].fill = PatternFill(
        "solid",
        fgColor=light_blue
    )

    worksheet["E3"].border = (
        thin_border
    )


    worksheet.merge_cells(
        "G3:H3"
    )

    worksheet["G3"] = (
        "________________________"
    )

    worksheet["G3"].font = Font(
        color=black
    )

    worksheet["G3"].border = (
        thin_border
    )


    # =================================================
    # ADMIN PRODUCTION
    # =================================================

    worksheet.merge_cells(
        "A4:B4"
    )

    worksheet["A4"] = (
        "Admin Production"
    )

    worksheet["A4"].font = Font(
        bold=True,
        color=black
    )

    worksheet["A4"].fill = PatternFill(
        "solid",
        fgColor=light_blue
    )

    worksheet["A4"].border = (
        thin_border
    )


    worksheet.merge_cells(
        "C4:D4"
    )

    worksheet["C4"] = (
        "________________________"
    )

    worksheet["C4"].font = Font(
        color=black
    )

    worksheet["C4"].border = (
        thin_border
    )


    # =================================================
    # CATATAN
    # =================================================

    worksheet.merge_cells(
        "E4:H4"
    )

    worksheet["E4"] = (
        "Checklist ini digunakan sebagai kontrol "
        "keberadaan ticket fisik."
    )

    worksheet["E4"].font = Font(
        italic=True,
        size=9,
        color=gray
    )

    worksheet["E4"].alignment = Alignment(
        wrap_text=True,
        vertical="center"
    )


    worksheet.row_dimensions[4].height = 25


    # =================================================
    # HEADER TABEL
    # =================================================

    header_row = 6

    headers = [

        "No",

        "Ticket Number",

        "Tanggal",

        "Line",

        "Shift",

        "Jumlah Part",

        "Status",

        "Cek Ticket Fisik"

    ]


    for column_index, header in enumerate(
        headers,
        start=1
    ):

        cell = worksheet.cell(
            row=header_row,
            column=column_index
        )

        cell.value = header

        cell.font = Font(
            bold=True,
            color=white,
            size=10
        )

        cell.fill = PatternFill(
            "solid",
            fgColor=medium_blue
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

        cell.border = (
            thin_border
        )


    worksheet.row_dimensions[
        header_row
    ].height = 28


    # =================================================
    # DATA TICKET
    # =================================================

    current_row = (
        header_row + 1
    )


    if tickets:

        for number, ticket in enumerate(
            tickets,
            start=1
        ):

            part_total = (
                ticket_part_totals.get(
                    ticket.id,
                    0
                )
            )


            row_data = [

                number,

                ticket.ticket_number,

                (
                    ticket.created_at.strftime(
                        "%d-%m-%Y %H:%M"
                    )
                    if ticket.created_at
                    else "-"
                ),

                ticket.line,

                ticket.shift,

                part_total,

                "Approved",

                "☐"

            ]


            for column_index, value in enumerate(
                row_data,
                start=1
            ):

                cell = worksheet.cell(
                    row=current_row,
                    column=column_index
                )

                cell.value = value

                cell.border = (
                    thin_border
                )

                cell.alignment = Alignment(
                    vertical="center",
                    horizontal=(
                        "center"
                        if column_index
                        in [1, 3, 4, 5, 6, 7, 8]
                        else "left"
                    )
                )

                cell.font = Font(
                    size=10,
                    color=black
                )


            # -----------------------------------------
            # STATUS
            # -----------------------------------------

            status_cell = worksheet.cell(
                row=current_row,
                column=7
            )

            status_cell.font = Font(
                bold=True,
                color="008000"
            )

            status_cell.fill = PatternFill(
                "solid",
                fgColor=green
            )


            # -----------------------------------------
            # CHECKBOX
            # -----------------------------------------

            check_cell = worksheet.cell(
                row=current_row,
                column=8
            )

            check_cell.font = Font(
                size=14,
                bold=True,
                color=dark_blue
            )

            check_cell.alignment = Alignment(
                horizontal="center",
                vertical="center"
            )

            check_cell.fill = PatternFill(
                "solid",
                fgColor="F8FAFC"
            )


            # -----------------------------------------
            # NOMOR
            # -----------------------------------------

            no_cell = worksheet.cell(
                row=current_row,
                column=1
            )

            no_cell.font = Font(
                bold=True,
                color=dark_blue
            )


            # -----------------------------------------
            # TICKET NUMBER
            # -----------------------------------------

            ticket_cell = worksheet.cell(
                row=current_row,
                column=2
            )

            ticket_cell.font = Font(
                bold=True,
                color=dark_blue
            )


            # -----------------------------------------
            # JUMLAH PART
            # -----------------------------------------

            qty_cell = worksheet.cell(
                row=current_row,
                column=6
            )

            qty_cell.font = Font(
                bold=True,
                color=black
            )

            qty_cell.fill = PatternFill(
                "solid",
                fgColor=light_orange
            )


            worksheet.row_dimensions[
                current_row
            ].height = 24


            current_row += 1


    else:

        worksheet.merge_cells(
            start_row=current_row,
            start_column=1,
            end_row=current_row,
            end_column=8
        )

        empty_cell = worksheet.cell(
            row=current_row,
            column=1
        )

        empty_cell.value = (
            "Tidak ada ticket yang selesai pulling hari ini."
        )

        empty_cell.font = Font(
            italic=True,
            color=gray
        )

        empty_cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

        empty_cell.border = (
            thin_border
        )

        worksheet.row_dimensions[
            current_row
        ].height = 28


        current_row += 1


    # =================================================
    # TOTAL BARIS BAWAH
    # =================================================

    total_row = (
        current_row + 1
    )


    worksheet.merge_cells(
        start_row=total_row,
        start_column=1,
        end_row=total_row,
        end_column=5
    )

    worksheet.cell(
        row=total_row,
        column=1
    ).value = (
        "TOTAL"
    )

    worksheet.cell(
        row=total_row,
        column=1
    ).font = Font(
        bold=True,
        color=white
    )

    worksheet.cell(
        row=total_row,
        column=1
    ).fill = PatternFill(
        "solid",
        fgColor=dark_blue
    )

    worksheet.cell(
        row=total_row,
        column=1
    ).alignment = Alignment(
        horizontal="right",
        vertical="center"
    )


    worksheet.cell(
        row=total_row,
        column=6
    ).value = total_part

    worksheet.cell(
        row=total_row,
        column=6
    ).font = Font(
        bold=True,
        color=white
    )

    worksheet.cell(
        row=total_row,
        column=6
    ).fill = PatternFill(
        "solid",
        fgColor=dark_blue
    )

    worksheet.cell(
        row=total_row,
        column=6
    ).alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


    worksheet.cell(
        row=total_row,
        column=7
    ).value = (
        f"{total_ticket} Ticket"
    )

    worksheet.cell(
        row=total_row,
        column=7
    ).font = Font(
        bold=True,
        color=white
    )

    worksheet.cell(
        row=total_row,
        column=7
    ).fill = PatternFill(
        "solid",
        fgColor=dark_blue
    )

    worksheet.cell(
        row=total_row,
        column=7
    ).alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


    worksheet.cell(
        row=total_row,
        column=8
    ).value = (
        "Checklist"
    )

    worksheet.cell(
        row=total_row,
        column=8
    ).font = Font(
        bold=True,
        color=white
    )

    worksheet.cell(
        row=total_row,
        column=8
    ).fill = PatternFill(
        "solid",
        fgColor=dark_blue
    )

    worksheet.cell(
        row=total_row,
        column=8
    ).alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


    # =================================================
    # BORDER TOTAL ROW
    # =================================================

    for column_index in range(
        1,
        9
    ):

        worksheet.cell(
            row=total_row,
            column=column_index
        ).border = Border(
            top=medium_side,
            bottom=medium_side,
            left=thin_side,
            right=thin_side
        )


    worksheet.row_dimensions[
        total_row
    ].height = 26


    # =================================================
    # LEBAR KOLOM
    # =================================================

    column_widths = {

        "A": 7,

        "B": 25,

        "C": 20,

        "D": 14,

        "E": 10,

        "F": 14,

        "G": 16,

        "H": 20

    }


    for column, width in (
        column_widths.items()
    ):

        worksheet.column_dimensions[
            column
        ].width = width


    # =================================================
    # FREEZE HEADER
    # =================================================

    worksheet.freeze_panes = (
        "A7"
    )


    # =================================================
    # AUTO FILTER
    # =================================================

    if tickets:

        worksheet.auto_filter.ref = (
            f"A{header_row}:H{current_row - 1}"
        )


    # =================================================
    # PRINT AREA
    # =================================================

    worksheet.print_area = (
        f"A1:H{total_row}"
    )


    # =================================================
    # PRINT HEADER
    # =================================================

    worksheet.oddFooter.center.text = (
        "Crushing App • List Pulling Harian"
    )

    worksheet.oddFooter.center.size = 8

    worksheet.oddFooter.center.font = (
        "Arial"
    )


    # =================================================
    # SIMPAN KE MEMORY
    # =================================================

    output = BytesIO()

    workbook.save(
        output
    )

    output.seek(0)


    # =================================================
    # NAMA FILE
    # =================================================

    filename = (
        "List crushing ticket("
        f"{today.strftime('%d-%m-%Y')}"
        ").xlsx"
    )


    # =================================================
    # DOWNLOAD
    # =================================================

    return send_file(

        output,

        as_attachment=True,

        download_name=filename,

        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    )