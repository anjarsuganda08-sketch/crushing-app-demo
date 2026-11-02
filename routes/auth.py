# ============================================================
# AUTHENTICATION & AUTHORIZATION
# CRUSHING APP
# F-6.2 / F-6.3
# ============================================================

from functools import wraps
from datetime import datetime
import secrets

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database.db import db

from database.models import (
    User,
    UserDevice
)


# ============================================================
# BLUEPRINT
# ============================================================

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


# ============================================================
# CONSTANT
# ============================================================

DEVICE_COOKIE_NAME = "crushing_device_token"

DEVICE_COOKIE_MAX_AGE = (
    60 * 60 * 24 * 365
)


# ============================================================
# ROLE SYSTEM
# ============================================================

VALID_ROLES = {
    "admin",
    "operator",
    "pulling",
    "leader",
    "viewer",
    "maris"
}


# ============================================================
# ROLE HELPER
# ============================================================

def normalize_role(role):

    if not role:
        return ""

    return str(
        role
    ).strip().lower()


# ============================================================
# SESSION USER
# ============================================================

def get_current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    try:

        user = User.query.get(
            user_id
        )

    except Exception:

        return None

    if not user:
        session.clear()
        return None

    if not user.is_active:

        session.clear()

        return None

    return user


# ============================================================
# CURRENT ROLE
# ============================================================

def get_current_role():

    user = get_current_user()

    if not user:
        return None

    return normalize_role(
        user.role
    )


# ============================================================
# LOGIN STATUS
# ============================================================

def is_logged_in():

    return (
        get_current_user()
        is not None
    )


# ============================================================
# ROLE CHECK
# ============================================================

def user_has_role(*roles):

    user = get_current_user()

    if not user:
        return False

    current_role = normalize_role(
        user.role
    )

    allowed_roles = {
        normalize_role(role)
        for role in roles
    }

    return current_role in allowed_roles


# ============================================================
# ADMIN
# ============================================================

def is_admin():

    return user_has_role(
        "admin"
    )


# ============================================================
# LEADER
# ============================================================

def is_leader():

    return user_has_role(
        "leader",
        "admin"
    )


# ============================================================
# MARIS
# ============================================================

def is_maris():

    return user_has_role(
        "maris",
        "admin"
    )


# ============================================================
# VIEWER
# ============================================================

def is_viewer():

    return user_has_role(
        "viewer",
        "admin"
    )


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(view_function):

    @wraps(view_function)
    def wrapped_view(
        *args,
        **kwargs
    ):

        user = get_current_user()

        if not user:

            next_url = request.full_path

            return redirect(
                url_for(
                    "auth.login",
                    next=next_url
                )
            )

        return view_function(
            *args,
            **kwargs
        )

    return wrapped_view


# ============================================================
# ROLE REQUIRED
# ============================================================

def role_required(*roles):

    allowed_roles = {
        normalize_role(role)
        for role in roles
    }

    def decorator(view_function):

        @wraps(view_function)
        def wrapped_view(
            *args,
            **kwargs
        ):

            user = get_current_user()

            # ----------------------------------------------
            # BELUM LOGIN
            # ----------------------------------------------

            if not user:

                next_url = request.full_path

                return redirect(
                    url_for(
                        "auth.login",
                        next=next_url
                    )
                )

            # ----------------------------------------------
            # CEK ROLE
            # ----------------------------------------------

            current_role = normalize_role(
                user.role
            )

            # PUBLIC DEMO: satu akun demo dapat membuka halaman seluruh alur
            # agar pengunjung bisa mengikuti transaksi dari Production sampai MARIS.
            # Pembatasan mutasi tetap diatur terpisah oleh app.py.
            if str(getattr(user, "username", "") or "").strip().lower() == "public_demo_operator":
                return view_function(*args, **kwargs)

            # Viewer boleh membuka semua halaman sebagai read-only.
            # Semua metode perubahan (POST/PUT/PATCH/DELETE) ditolak
            # secara global di app.py sebelum route dijalankan.
            if current_role == "viewer" and request.method in {"GET", "HEAD", "OPTIONS"}:
                return view_function(*args, **kwargs)

            if current_role not in allowed_roles:

                return redirect(
                    url_for(
                        "auth.unauthorized"
                    )
                )

            return view_function(
                *args,
                **kwargs
            )

        return wrapped_view

    return decorator


# ============================================================
# DEVICE TOKEN
# ============================================================

def generate_device_token():

    return secrets.token_urlsafe(
        64
    )


# ============================================================
# GET DEVICE FROM COOKIE
# ============================================================

def get_device_from_cookie():

    token = request.cookies.get(
        DEVICE_COOKIE_NAME
    )

    if not token:
        return None

    try:

        device = (
            UserDevice.query
            .filter_by(
                device_token=token,
                is_active=True
            )
            .first()
        )

    except Exception:

        return None

    return device


# ============================================================
# UPDATE DEVICE
# ============================================================

def update_device_last_seen(device):

    if not device:
        return

    try:

        device.last_seen_at = (
            datetime.now()
        )

        db.session.commit()

    except Exception:

        db.session.rollback()


# ============================================================
# CREATE LOGIN SESSION
# ============================================================

def create_login_session(user):

    session.clear()

    session["user_id"] = user.id

    session["username"] = user.username

    session["npk"] = user.npk

    session["full_name"] = user.full_name

    session["nickname"] = user.nickname

    session["role"] = normalize_role(
        user.role
    )

    session.permanent = True


# ============================================================
# DEVICE LOGIN
# ============================================================

def login_with_device(device):

    if not device:
        return None

    user = device.user

    if not user:
        return None

    if not user.is_active:

        device.is_active = False

        db.session.commit()

        return None

    try:

        now = datetime.now()

        user.last_login_at = now

        device.last_seen_at = now

        db.session.commit()

        create_login_session(
            user
        )

        return user

    except Exception:

        db.session.rollback()

        return None


# ============================================================
# CREATE USER DEVICE
# ============================================================

def create_user_device(user):

    token = generate_device_token()

    user_agent = request.headers.get(
        "User-Agent",
        ""
    )

    device_name = (
        user_agent[:255]
        if user_agent
        else "Unknown Device"
    )

    device = UserDevice(
        user_id=user.id,
        device_token=token,
        device_name=device_name,
        user_agent=user_agent,
        is_active=True,
        created_at=datetime.now(),
        last_seen_at=datetime.now()
    )

    db.session.add(
        device
    )

    db.session.flush()

    return device


# ============================================================
# SET DEVICE COOKIE
# ============================================================

def set_device_cookie(
    response,
    token
):

    response.set_cookie(
        DEVICE_COOKIE_NAME,
        token,
        max_age=DEVICE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure
    )

    return response


# ============================================================
# CLEAR DEVICE COOKIE
# ============================================================

def clear_device_cookie(response):

    response.delete_cookie(
        DEVICE_COOKIE_NAME
    )

    return response


# ============================================================
# AUTO LOGIN
# ============================================================

def try_auto_login():

    current_user = get_current_user()

    if current_user:

        return current_user

    device = get_device_from_cookie()

    if not device:

        return None

    return login_with_device(
        device
    )


# ============================================================
# SAFE NEXT URL
# ============================================================

def get_safe_next_url():

    next_url = request.args.get(
        "next"
    )

    if not next_url:
        return None

    # Jangan izinkan redirect ke domain luar.
    if not next_url.startswith("/"):

        return None

    if next_url.startswith("//"):

        return None

    return next_url


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # ========================================================
    # SUDAH LOGIN
    # ========================================================

    current_user = get_current_user()

    if current_user:

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    # ========================================================
    # AUTO LOGIN
    # ========================================================

    auto_user = try_auto_login()

    if auto_user:

        next_url = get_safe_next_url()

        if next_url:

            return redirect(
                next_url
            )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        username = (
            request.form
            .get(
                "username",
                ""
            )
            .strip()
        )

        password = (
            request.form
            .get(
                "password",
                ""
            )
        )

        # ----------------------------------------------------
        # VALIDASI
        # ----------------------------------------------------

        if not username:

            flash(
                "Username / NPK wajib diisi.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if not password:

            flash(
                "Password wajib diisi.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # ----------------------------------------------------
        # CARI USER
        #
        # Bisa login menggunakan:
        # username atau NPK
        # ----------------------------------------------------

        user = (
            User.query
            .filter(
                (
                    User.username == username
                )
                |
                (
                    User.npk == username
                )
            )
            .first()
        )

        if not user:

            flash(
                "Username atau password salah.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # ----------------------------------------------------
        # ACCOUNT NONAKTIF
        # ----------------------------------------------------

        if not user.is_active:

            flash(
                "Account Anda tidak aktif. "
                "Silakan hubungi Admin.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # ----------------------------------------------------
        # PASSWORD
        # ----------------------------------------------------

        if not check_password_hash(
            user.password_hash,
            password
        ):

            flash(
                "Username atau password salah.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # ====================================================
        # LOGIN BERHASIL
        # ====================================================

        try:

            now = datetime.now()

            # ------------------------------------------------
            # SESSION
            # ------------------------------------------------

            create_login_session(
                user
            )

            # ------------------------------------------------
            # LAST LOGIN
            # ------------------------------------------------

            user.last_login_at = now

            # ------------------------------------------------
            # CEK DEVICE
            # ------------------------------------------------

            existing_device = (
                get_device_from_cookie()
            )

            if (
                existing_device
                and existing_device.user_id
                == user.id
            ):

                existing_device.last_seen_at = now

                device_token = (
                    existing_device.device_token
                )

            else:

                device = create_user_device(
                    user
                )

                device_token = (
                    device.device_token
                )

            # ------------------------------------------------
            # COMMIT
            # ------------------------------------------------

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            session.clear()

            print(
                "LOGIN ERROR:",
                error
            )

            flash(
                "Terjadi kesalahan saat login.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # ====================================================
        # REDIRECT
        # ====================================================

        next_url = get_safe_next_url()

        if next_url:

            response = redirect(
                next_url
            )

        else:

            response = redirect(
                url_for(
                    "dashboard.dashboard"
                )
            )

        # ====================================================
        # DEVICE COOKIE
        # ====================================================

        return set_device_cookie(
            response,
            device_token
        )

    # ========================================================
    # GET
    # ========================================================

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route(
    "/logout"
)
def logout():
    """
    Logout normal.

    Setelah logout:
        - session dihapus
        - cookie device dihapus
        - user kembali ke halaman login

    UserDevice di database TIDAK dihapus.
    """

    # --------------------------------------------------------
    # Hapus session login
    # --------------------------------------------------------

    session.clear()

    # --------------------------------------------------------
    # Redirect ke login
    # --------------------------------------------------------

    response = redirect(
        url_for(
            "auth.login"
        )
    )

    # --------------------------------------------------------
    # Hapus cookie device dari browser
    #
    # Ini penting agar halaman login tidak langsung
    # melakukan auto-login kembali.
    # --------------------------------------------------------

    response = clear_device_cookie(
        response
    )

    return response


# ============================================================
# UNAUTHORIZED
# ============================================================

@auth_bp.route(
    "/unauthorized"
)
def unauthorized():

    user = get_current_user()

    return render_template(
        "unauthorized.html",
        user=user
    ), 403


# ============================================================
# HASH PASSWORD
# ============================================================

def hash_password(password):

    return generate_password_hash(
        password
    )


# ============================================================
# CREATE USER
# ============================================================

def create_user(
    username,
    full_name,
    password,
    role="operator",
    npk=None,
    nickname=None
):

    username = str(
        username
    ).strip()

    full_name = str(
        full_name
    ).strip()

    role = normalize_role(
        role
    )

    if npk is None:

        npk = username

    npk = str(
        npk
    ).strip()

    if role not in VALID_ROLES:

        raise ValueError(
            f"Role tidak valid: {role}"
        )

    if not username:

        raise ValueError(
            "Username wajib diisi."
        )

    if not npk:

        raise ValueError(
            "NPK wajib diisi."
        )

    if not password:

        raise ValueError(
            "Password wajib diisi."
        )

    # --------------------------------------------------------
    # CEK USERNAME
    # --------------------------------------------------------

    existing_user = (
        User.query
        .filter(
            (
                User.username
                == username
            )
            |
            (
                User.npk
                == npk
            )
        )
        .first()
    )

    if existing_user:

        raise ValueError(
            "Username atau NPK sudah digunakan."
        )

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    user = User(
        npk=npk,
        username=username,
        nickname=nickname,
        full_name=full_name,
        password_hash=hash_password(
            password
        ),
        role=role,
        is_active=True,
        created_at=datetime.now()
    )

    db.session.add(
        user
    )

    db.session.commit()

    return user


# ============================================================
# TEMPLATE CONTEXT
# ============================================================

@auth_bp.app_context_processor
def inject_auth_context():

    user = get_current_user()

    current_role = (
        normalize_role(
            user.role
        )
        if user
        else None
    )

    return {

        "current_user": user,

        "current_user_role":
            current_role,

        "logged_in":
            user is not None,

        "is_admin":
            current_role == "admin",

        "is_operator":
            current_role == "operator",

        "is_pulling":
            current_role == "pulling",

        "is_leader":
            current_role in {
                "leader",
                "admin"
            },

        "is_viewer":
            current_role in {
                "viewer",
                "admin"
            },

        "is_maris":
            current_role in {
                "maris",
                "admin"
            }
    }