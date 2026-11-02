from app import app
from database.db import db
from database.models import NgClassification, NgType


# ==========================================================
# MASTER KLASIFIKASI NG
# ==========================================================

NG_CLASSIFICATIONS = [
    "Setting",
    "Process",
    "Verifikasi",
    "SFG Outflow",
]


# ==========================================================
# MASTER JENIS NG
# ==========================================================

NG_TYPES = [
    "Bending",
    "Bintik",
    "Black dot",
    "Blueing",
    "Bocor",
    "Bubble",
    "Bulb Jatuh/Mati",
    "Buram",
    "CF",
    "Crack",
    "Dented",
    "Dirty",
    "Discolor",
    "Duplikat QR",
    "Ejector mark",
    "Foreign Material",
    "Finger",
    "Flashing",
    "Flex",
    "Flowmark",
    "Foreign parting line",
    "Gata-gata",
    "Gelap",
    "Getting",
    "Gompal",
    "Grazemark",
    "Gumpalan",
    "Kena heater",
    "Keriput",
    "Keropos",
    "kontaminasi",
    "Laser miring",
    "Leleh",
    "Lighting",
    "Lock patah",
    "Lose Screw",
    "Current abnormal",
    "Noisy",
    "Oil",
    "Orange peel",
    "Over glue",
    "Over Material",
    "Over metalizing",
    "Over painting",
    "Over spray",
    "Over Welding",
    "Overbasecoat",
    "Overcut",
    "Overlap",
    "Peel off",
    "Pin hole seret",
    "Pin lock tertutup",
    "Painting tipis",
    "Plastik",
    "Sagging",
    "Scratch",
    "Serabut",
    "Setting",
    "Setting after downtime",
    "Setting Welding",
    "Short mold",
    "Silver",
    "Sinkmark",
    "Sobek",
    "Stud bolt naik",
    "Studpin abnormal",
    "Terminal Bending",
    "Uneven paint",
    "Verifikasi",
    "Welding lepas",
    "Welding putih",
    "Weldline",
    "Yellow",
    "PCB mati",
]


# ==========================================================
# SEED DATABASE
# ==========================================================

def seed_database():

    with app.app_context():

        print("=" * 60)
        print("SEED MASTER KLASIFIKASI NG & JENIS NG")
        print("=" * 60)


        # ==================================================
        # KLASIFIKASI NG
        # ==================================================

        classification_added = 0
        classification_existing = 0


        for name in NG_CLASSIFICATIONS:

            existing = (
                NgClassification.query
                .filter_by(name=name)
                .first()
            )


            if existing:

                classification_existing += 1

                print(
                    f"[SUDAH ADA] Klasifikasi NG : {name}"
                )

                continue


            classification = NgClassification(
                name=name
            )


            db.session.add(
                classification
            )


            classification_added += 1

            print(
                f"[DITAMBAHKAN] Klasifikasi NG : {name}"
            )


        # ==================================================
        # JENIS NG
        # ==================================================

        ng_type_added = 0
        ng_type_existing = 0


        for name in NG_TYPES:

            existing = (
                NgType.query
                .filter_by(name=name)
                .first()
            )


            if existing:

                ng_type_existing += 1

                print(
                    f"[SUDAH ADA] Jenis NG : {name}"
                )

                continue


            ng_type = NgType(
                name=name
            )


            db.session.add(
                ng_type
            )


            ng_type_added += 1

            print(
                f"[DITAMBAHKAN] Jenis NG : {name}"
            )


        # ==================================================
        # COMMIT
        # ==================================================

        try:

            db.session.commit()

            print()
            print("=" * 60)
            print("SEED BERHASIL")
            print("=" * 60)

            print(
                f"Klasifikasi NG ditambahkan : "
                f"{classification_added}"
            )

            print(
                f"Klasifikasi NG sudah ada   : "
                f"{classification_existing}"
            )

            print(
                f"Jenis NG ditambahkan        : "
                f"{ng_type_added}"
            )

            print(
                f"Jenis NG sudah ada          : "
                f"{ng_type_existing}"
            )

            print("=" * 60)

            # ==============================================
            # TOTAL DATABASE
            # ==============================================

            total_classification = (
                NgClassification.query.count()
            )

            total_ng_type = (
                NgType.query.count()
            )

            print(
                f"TOTAL KLASIFIKASI NG DI DATABASE : "
                f"{total_classification}"
            )

            print(
                f"TOTAL JENIS NG DI DATABASE       : "
                f"{total_ng_type}"
            )

            print("=" * 60)


        except Exception as e:

            db.session.rollback()

            print()
            print("=" * 60)
            print("SEED GAGAL")
            print("=" * 60)

            print(
                "ERROR :",
                e
            )

            print("=" * 60)

            raise


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    seed_database()