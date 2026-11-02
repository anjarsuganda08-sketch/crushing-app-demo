import pandas as pd

from database.models import Part
from database.db import db


def import_master_part(file_path):

    df = pd.read_excel(file_path)

    for _, row in df.iterrows():

        existing_part = Part.query.filter_by(
            part_number=row["Part Number"]
        ).first()

        if existing_part:
            continue

        part = Part(
            line=row["Line"],
            model=row["Model"],
            part_number=row["Part Number"],
            part_name=row["Part Name"],
            return_location=row["Return Location"],
            photo=""
        )

        db.session.add(part)

    db.session.commit()

    print("Import selesai.")
    