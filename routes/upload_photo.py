import os

from PIL import Image, ImageOps

from flask import (
    Blueprint,
    request,
    jsonify
)

from database.db import db
from database.models import Part
from routes.auth import role_required


upload_photo_bp = Blueprint(
    "upload_photo",
    __name__
)


# ==========================================================
# UPLOAD FOTO PART
# ==========================================================

@upload_photo_bp.route(
    "/upload-photo/<part_number>",
    methods=["POST"]
)
@role_required("admin", "maris")
def upload_photo(part_number):

    # ---------------------------------------------
    # Cari Part
    # ---------------------------------------------

    part = Part.query.filter_by(
        part_number=part_number
    ).first()

    if part is None:

        return jsonify({

            "success":False,

            "message":"Part tidak ditemukan."

        }),404


    # ---------------------------------------------
    # Ambil File
    # ---------------------------------------------

    photo = request.files.get("photo")

    if photo is None:

        return jsonify({

            "success":False,

            "message":"Foto belum dipilih."

        }),400


    if photo.filename=="":

        return jsonify({

            "success":False,

            "message":"Nama file kosong."

        }),400


    # ---------------------------------------------
    # Folder Upload
    # ---------------------------------------------

    upload_folder = os.path.join(

        "static",

        "part"

    )

    os.makedirs(

        upload_folder,

        exist_ok=True

    )


    # ---------------------------------------------
    # Nama File
    # ---------------------------------------------

    filename = f"{part.part_number}.jpg"

    save_path = os.path.join(

        upload_folder,

        filename

    )


    # ---------------------------------------------
    # Buka Gambar
    # ---------------------------------------------

    try:

        img = Image.open(photo)

    except Exception:

        return jsonify({

            "success":False,

            "message":"File bukan gambar."

        }),400


    # ---------------------------------------------
    # Perbaiki orientasi kamera HP
    # ---------------------------------------------

    img = ImageOps.exif_transpose(img)

    img = img.convert("RGB")


    # ---------------------------------------------
    # Crop Tengah menjadi Kotak
    # ---------------------------------------------

    width,height = img.size

    size = min(width,height)

    left = (width-size)//2

    top = (height-size)//2

    right = left+size

    bottom = top+size

    img = img.crop(

        (

            left,

            top,

            right,

            bottom

        )

    )


    # ---------------------------------------------
    # Resize Standar
    # ---------------------------------------------

    img = img.resize(

        (

            800,

            800

        ),

        Image.Resampling.LANCZOS

    )


    # ---------------------------------------------
    # Simpan
    # ---------------------------------------------

    img.save(

        save_path,

        "JPEG",

        quality=70,

        optimize=True

    )


    # ---------------------------------------------
    # Update Database
    # ---------------------------------------------

    part.photo = filename

    db.session.commit()


    # ---------------------------------------------
    # Return JSON
    # ---------------------------------------------

    return jsonify({

        "success":True,

        "photo":filename,

        "part_number":part.part_number

    })