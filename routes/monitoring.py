from flask import (
    Blueprint,
    render_template,
    request
)

from sqlalchemy import (
    or_,
    func
)

from database.db import db

from routes.auth import role_required

from database.models import (
    CrushingTicket,
    CrushingTransaction
)

from datetime import (
    datetime
)


# ==========================================================
# BLUEPRINT
# ==========================================================

monitoring_bp = Blueprint(
    "monitoring",
    __name__
)


# ==========================================================
# FUNGSI AGING
# ==========================================================

def calculate_aging(created_at):

    if not created_at:

        return {
            "minutes": 0,
            "text": "-",
            "level": "normal"
        }


    now = datetime.now()


    difference = (
        now - created_at
    )


    total_seconds = max(
        0,
        int(
            difference.total_seconds()
        )
    )


    total_minutes = (
        total_seconds // 60
    )


    hours = (
        total_minutes // 60
    )


    minutes = (
        total_minutes % 60
    )


    # ======================================================
    # FORMAT TEXT
    # ======================================================

    if hours > 0:

        aging_text = (
            f"{hours} Jam "
            f"{minutes} Menit"
        )

    else:

        aging_text = (
            f"{minutes} Menit"
        )


    # ======================================================
    # LEVEL AGING
    #
    # NORMAL       < 30 menit
    # WARNING      30 - 59 menit
    # ATTENTION    60 - 119 menit
    # CRITICAL     >= 120 menit
    # ======================================================

    if total_minutes < 30:

        aging_level = "normal"


    elif total_minutes < 60:

        aging_level = "warning"


    elif total_minutes < 120:

        aging_level = "attention"


    else:

        aging_level = "critical"


    return {

        "minutes":
            total_minutes,

        "text":
            aging_text,

        "level":
            aging_level

    }


# ==========================================================
# FUNGSI FILTER TANGGAL
# ==========================================================

def apply_date_filter(
    query,
    start_date,
    end_date
):

    if start_date:

        query = query.filter(

            CrushingTicket.created_at
            >=
            datetime.combine(
                start_date,
                datetime.min.time()
            )

        )


    if end_date:

        query = query.filter(

            CrushingTicket.created_at
            <=
            datetime.combine(
                end_date,
                datetime.max.time()
            )

        )


    return query


# ==========================================================
# MONITORING
# ==========================================================

@monitoring_bp.route(
    "/monitoring"
)
@role_required("admin", "leader", "viewer")
def monitoring():

    # ======================================================
    # FILTER
    # ======================================================

    selected_line = (

        request.args.get(
            "line",
            ""
        )
        .strip()

    )


    selected_shift = (

        request.args.get(
            "shift",
            ""
        )
        .strip()

    )


    selected_status = (

        request.args.get(
            "status",
            "All"
        )
        .strip()

    )


    search = (

        request.args.get(
            "search",
            ""
        )
        .strip()

    )


    start_date_value = (

        request.args.get(
            "start_date",
            ""
        )
        .strip()

    )


    end_date_value = (

        request.args.get(
            "end_date",
            ""
        )
        .strip()

    )


    # ======================================================
    # VALIDASI TANGGAL
    # ======================================================

    start_date = None

    end_date = None


    if start_date_value:

        try:

            start_date = datetime.strptime(
                start_date_value,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            start_date_value = ""


    if end_date_value:

        try:

            end_date = datetime.strptime(
                end_date_value,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            end_date_value = ""


    # Jika pengguna tidak memilih tanggal, grafik dan monitoring
    # otomatis fokus pada data hari ini. Filter tanggal tetap bisa
    # digunakan untuk melihat histori.
    if not start_date_value and not end_date_value:
        today = datetime.now().date()
        start_date = today
        end_date = today
        start_date_value = today.strftime("%Y-%m-%d")
        end_date_value = today.strftime("%Y-%m-%d")


    # ======================================================
    # QUERY TICKET
    # ======================================================

    query = (
        CrushingTicket.query
    )


    # ======================================================
    # FILTER LINE
    # ======================================================

    if selected_line != "":

        query = query.filter(

            CrushingTicket.line
            ==
            selected_line

        )


    # ======================================================
    # FILTER SHIFT
    # ======================================================

    if selected_shift != "":

        query = query.filter(

            CrushingTicket.shift
            ==
            selected_shift

        )


    # ======================================================
    # FILTER STATUS
    # ======================================================

    if selected_status != "All":

        query = query.filter(

            CrushingTicket.status
            ==
            selected_status

        )


    # ======================================================
    # FILTER SEARCH
    # ======================================================

    if search != "":

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


    # ======================================================
    # FILTER TANGGAL
    # ======================================================

    query = apply_date_filter(

        query,

        start_date,

        end_date

    )


    # ======================================================
    # AMBIL TICKET
    # ======================================================

    tickets = (

        query

        .order_by(

            CrushingTicket.created_at.desc()

        )

        .all()

    )


    # ======================================================
    # JUMLAH PART + AGING
    # ======================================================

    for ticket in tickets:


        # ==================================================
        # JUMLAH PART
        # ==================================================

        ticket.total_part = (

            CrushingTransaction.query

            .filter_by(

                ticket_id=ticket.id

            )

            .count()

        )


        # ==================================================
        # AGING
        # ==================================================

        aging = calculate_aging(

            ticket.created_at

        )


        ticket.aging_minutes = (
            aging["minutes"]
        )


        ticket.aging_text = (
            aging["text"]
        )


        ticket.aging_level = (
            aging["level"]
        )


    # ======================================================
    # SUMMARY QUERY
    #
    # Summary mengikuti:
    # - Line
    # - Shift
    # - Tanggal
    #
    # Status tidak digunakan sebagai filter dasar summary
    # agar KPI tetap menunjukkan distribusi semua status.
    # ======================================================

    summary = (
        CrushingTicket.query
    )


    # ======================================================
    # FILTER LINE
    # ======================================================

    if selected_line != "":

        summary = summary.filter(

            CrushingTicket.line
            ==
            selected_line

        )


    # ======================================================
    # FILTER SHIFT
    # ======================================================

    if selected_shift != "":

        summary = summary.filter(

            CrushingTicket.shift
            ==
            selected_shift

        )


    # ======================================================
    # FILTER TANGGAL
    # ======================================================

    summary = apply_date_filter(

        summary,

        start_date,

        end_date

    )


    # ======================================================
    # TOTAL TICKET
    # ======================================================

    total_ticket = (

        summary.count()

    )


    # ======================================================
    # STATUS COUNT
    # ======================================================

    pending_count = (

        summary

        .filter(

            CrushingTicket.status
            ==
            "Pending Pulling"

        )

        .count()

    )


    leader_count = (

        summary

        .filter(

            CrushingTicket.status
            ==
            "Need Leader Confirmation"

        )

        .count()

    )


    approved_count = (

        summary

        .filter(

            CrushingTicket.status
            ==
            "Approved"

        )

        .count()

    )


    maris_completed_count = (

        summary

        .filter(

            CrushingTicket.status
            ==
            "MARIS Completed"

        )

        .count()

    )


    # ======================================================
    # TOTAL QTY
    #
    # Mengikuti filter:
    # - Line
    # - Shift
    # - Tanggal
    #
    # Semua status.
    # ======================================================

    qty_query = (

        db.session.query(

            func.sum(
                CrushingTransaction.quantity
            )

        )

        .join(

            CrushingTicket,

            CrushingTransaction.ticket_id
            ==
            CrushingTicket.id

        )

    )


    if selected_line != "":

        qty_query = qty_query.filter(

            CrushingTicket.line
            ==
            selected_line

        )


    if selected_shift != "":

        qty_query = qty_query.filter(

            CrushingTicket.shift
            ==
            selected_shift

        )


    if start_date:

        qty_query = qty_query.filter(

            CrushingTicket.created_at
            >=
            datetime.combine(
                start_date,
                datetime.min.time()
            )

        )


    if end_date:

        qty_query = qty_query.filter(

            CrushingTicket.created_at
            <=
            datetime.combine(
                end_date,
                datetime.max.time()
            )

        )


    total_qty = (

        qty_query.scalar()

        or 0

    )


    # ======================================================
    # NILAI APPROVED
    # ======================================================

    approved_value_query = (

        db.session.query(

            func.sum(

                CrushingTransaction.price
                *
                CrushingTransaction.quantity

            )

        )

        .join(

            CrushingTicket,

            CrushingTransaction.ticket_id
            ==
            CrushingTicket.id

        )

        .filter(

            CrushingTicket.status
            ==
            "Approved"

        )

    )


    if selected_line != "":

        approved_value_query = (

            approved_value_query.filter(

                CrushingTicket.line
                ==
                selected_line

            )

        )


    if selected_shift != "":

        approved_value_query = (

            approved_value_query.filter(

                CrushingTicket.shift
                ==
                selected_shift

            )

        )


    if start_date:

        approved_value_query = (

            approved_value_query.filter(

                CrushingTicket.created_at
                >=
                datetime.combine(
                    start_date,
                    datetime.min.time()
                )

            )

        )


    if end_date:

        approved_value_query = (

            approved_value_query.filter(

                CrushingTicket.created_at
                <=
                datetime.combine(
                    end_date,
                    datetime.max.time()
                )

            )

        )


    total_approved_value = (

        approved_value_query.scalar()

        or 0

    )


    # ======================================================
    # NILAI MARIS COMPLETED
    # ======================================================

    maris_value_query = (

        db.session.query(

            func.sum(

                CrushingTransaction.price
                *
                CrushingTransaction.quantity

            )

        )

        .join(

            CrushingTicket,

            CrushingTransaction.ticket_id
            ==
            CrushingTicket.id

        )

        .filter(

            CrushingTicket.status
            ==
            "MARIS Completed"

        )

    )


    if selected_line != "":

        maris_value_query = (

            maris_value_query.filter(

                CrushingTicket.line
                ==
                selected_line

            )

        )


    if selected_shift != "":

        maris_value_query = (

            maris_value_query.filter(

                CrushingTicket.shift
                ==
                selected_shift

            )

        )


    if start_date:

        maris_value_query = (

            maris_value_query.filter(

                CrushingTicket.created_at
                >=
                datetime.combine(
                    start_date,
                    datetime.min.time()
                )

            )

        )


    if end_date:

        maris_value_query = (

            maris_value_query.filter(

                CrushingTicket.created_at
                <=
                datetime.combine(
                    end_date,
                    datetime.max.time()
                )

            )

        )


    total_maris_value = (

        maris_value_query.scalar()

        or 0

    )


    # ======================================================
    # AGING SUMMARY
    #
    # HANYA TICKET AKTIF.
    #
    # MARIS COMPLETED TIDAK MASUK.
    # ======================================================

    active_tickets = (

        summary

        .filter(

            CrushingTicket.status
            !=
            "MARIS Completed"

        )

        .all()

    )


    aging_under_30 = 0

    aging_30_60 = 0

    aging_60_120 = 0

    aging_over_120 = 0


    for ticket in active_tickets:


        aging = calculate_aging(

            ticket.created_at

        )


        minutes = aging["minutes"]


        if minutes < 30:

            aging_under_30 += 1


        elif minutes < 60:

            aging_30_60 += 1


        elif minutes < 120:

            aging_60_120 += 1


        else:

            aging_over_120 += 1


    # ======================================================
    # TICKET TERLAMA
    #
    # HANYA TICKET AKTIF.
    # ======================================================

    oldest_active_ticket = None


    if active_tickets:

        oldest_active_ticket = min(

            active_tickets,

            key=lambda ticket:
                ticket.created_at
                if ticket.created_at
                else datetime.max

        )


        oldest_aging = calculate_aging(

            oldest_active_ticket.created_at

        )


        oldest_active_ticket.aging_minutes = (

            oldest_aging["minutes"]

        )


        oldest_active_ticket.aging_text = (

            oldest_aging["text"]

        )


        oldest_active_ticket.aging_level = (

            oldest_aging["level"]

        )


        oldest_active_ticket.total_part = (

            CrushingTransaction.query

            .filter_by(

                ticket_id=
                oldest_active_ticket.id

            )

            .count()

        )


    # ======================================================
    # GRAFIK NILAI TICKET PRODUKSI PER LINE
    # ======================================================

    line_value_query = (

        db.session.query(

            CrushingTicket.line,

            func.sum(

                CrushingTransaction.price
                *
                CrushingTransaction.quantity

            ).label(
                "total_value"
            )

        )

        .join(

            CrushingTransaction,

            CrushingTransaction.ticket_id
            ==
            CrushingTicket.id

        )


    )


    if selected_line != "":

        line_value_query = (

            line_value_query.filter(

                CrushingTicket.line
                ==
                selected_line

            )

        )


    if selected_shift != "":

        line_value_query = (

            line_value_query.filter(

                CrushingTicket.shift
                ==
                selected_shift

            )

        )


    if start_date:

        line_value_query = (

            line_value_query.filter(

                CrushingTicket.created_at
                >=
                datetime.combine(
                    start_date,
                    datetime.min.time()
                )

            )

        )


    if end_date:

        line_value_query = (

            line_value_query.filter(

                CrushingTicket.created_at
                <=
                datetime.combine(
                    end_date,
                    datetime.max.time()
                )

            )

        )


    line_value_data = (

        line_value_query

        .group_by(

            CrushingTicket.line

        )

        .order_by(

            func.sum(

                CrushingTransaction.price
                *
                CrushingTransaction.quantity

            ).desc()

        )

        .all()

    )


    line_chart_labels = [

        row.line

        for row in line_value_data

    ]


    line_chart_values = [

        float(

            row.total_value
            or 0

        )

        for row in line_value_data

    ]


    # ======================================================
    # TOP 10 PART
    # ======================================================

    top_part_query = (

        db.session.query(

            CrushingTransaction.part_number,

            CrushingTransaction.part_name,

            func.sum(

                CrushingTransaction.price
                *
                CrushingTransaction.quantity

            ).label(
                "total_value"
            )

        )

        .join(

            CrushingTicket,

            CrushingTransaction.ticket_id
            ==
            CrushingTicket.id

        )


    )


    if selected_line != "":

        top_part_query = (

            top_part_query.filter(

                CrushingTicket.line
                ==
                selected_line

            )

        )


    if selected_shift != "":

        top_part_query = (

            top_part_query.filter(

                CrushingTicket.shift
                ==
                selected_shift

            )

        )


    if start_date:

        top_part_query = (

            top_part_query.filter(

                CrushingTicket.created_at
                >=
                datetime.combine(
                    start_date,
                    datetime.min.time()
                )

            )

        )


    if end_date:

        top_part_query = (

            top_part_query.filter(

                CrushingTicket.created_at
                <=
                datetime.combine(
                    end_date,
                    datetime.max.time()
                )

            )

        )


    top_parts = (

        top_part_query

        .group_by(

            CrushingTransaction.part_number,

            CrushingTransaction.part_name

        )

        .order_by(

            func.sum(

                CrushingTransaction.price
                *
                CrushingTransaction.quantity

            ).desc()

        )

        .limit(
            10
        )

        .all()

    )


    top_part_chart_labels = [

        f"{row.part_number} - {row.part_name}"

        for row in top_parts

    ]


    top_part_chart_values = [

        float(

            row.total_value
            or 0

        )

        for row in top_parts

    ]


    # ======================================================
    # MASTER LINE
    # ======================================================

    lines = (

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


    # ======================================================
    # SHIFT GROUP
    # ======================================================

    shifts = [

        "A",
        "B"

    ]


    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "monitoring.html",

        tickets=tickets,

        lines=lines,

        shifts=shifts,


        selected_line=
            selected_line,

        selected_shift=
            selected_shift,

        selected_status=
            selected_status,

        search=
            search,


        start_date=
            start_date_value,

        end_date=
            end_date_value,


        # ==================================================
        # SUMMARY
        # ==================================================

        total_ticket=
            total_ticket,

        pending_count=
            pending_count,

        leader_count=
            leader_count,

        approved_count=
            approved_count,

        maris_completed_count=
            maris_completed_count,


        # ==================================================
        # QTY
        # ==================================================

        total_qty=
            int(total_qty),


        # ==================================================
        # VALUE
        # ==================================================

        total_approved_value=
            float(total_approved_value),

        total_maris_value=
            float(total_maris_value),


        # ==================================================
        # AGING
        # ==================================================

        aging_under_30=
            aging_under_30,

        aging_30_60=
            aging_30_60,

        aging_60_120=
            aging_60_120,

        aging_over_120=
            aging_over_120,


        oldest_active_ticket=
            oldest_active_ticket,


        # ==================================================
        # CHART
        # ==================================================

        line_chart_labels=
            line_chart_labels,

        line_chart_values=
            line_chart_values,


        top_part_chart_labels=
            top_part_chart_labels,

        top_part_chart_values=
            top_part_chart_values

    )