from sqlalchemy import select, update
from Create_movement_table import create_movement_table
from Create_user_table import create_user_table
from PB_1RM import Best_one_rep_max

def calculate_and_fill_relative_intensities(user_table_name: str,
                                            movement_table_name: str,
                                            db_url: str = 'sqlite:///Movement_Database.db'):
    """
    Calculates and fills the Relative_Intensity and Wilks_Relative_intensity columns
    for each row in the specified movement table.

    - Relative_Intensity = round(One_Rep_Max / PB_1rm)
    - Wilks_Relative_intensity computed using sex-specific coefficients (if gender present).
    """
    # Ensure tables and engine
    movement_table, engine = create_movement_table(movement_table_name, db_url=db_url)
    user_table, _ = create_user_table(user_table_name, db_url=db_url)

    # Read gender (single user expected); ignore failure and skip Wilks if not available
    gender = None
    try:
        with engine.connect() as conn:
            result = conn.execute(select(user_table.c.gender).limit(1)).fetchone()
            if result:
                gender = result[0]
    except Exception:
        gender = None

    # Get best 1RM for this movement
    PB_1rm = Best_one_rep_max(movement_table_name, db_url=db_url)
    if not PB_1rm:
        # Nothing to compute against
        return

    # Read movement rows and update relative intensities
    with engine.begin() as conn:  # transaction
        rows = conn.execute(
            select(
                movement_table.c.Set,
                movement_table.c.One_Rep_Max,
                movement_table.c.Body_weight
            )
        ).fetchall()

        for set_id, one_rep_max, body_weight in rows:
            if one_rep_max is None or body_weight is None:
                continue

            try:
                relative_intensity = int(round(float(one_rep_max) / float(PB_1rm)))
            except Exception:
                continue

            wilks_relative_intensity = None

            if gender and isinstance(gender, str):
                g = gender.lower()
                bw = float(body_weight)

                if g == 'male':
                    # Wilks coefficients (male)
                    a = 47.46178854
                    b = 8.472061379
                    c = 0.07369410346
                    d = -0.001395833811
                    e = 0.00000707665973070743
                    f = -0.0000000120804336482315
                    denominator = (
                        a +
                        b * bw +
                        c * bw ** 2 +
                        d * bw ** 3 +
                        e * bw ** 4 +
                        f * bw ** 5
                    )
                    if denominator != 0:
                        wilks_relative_intensity = int(round(relative_intensity * 600 / denominator))

                elif g == 'female':
                    # Wilks coefficients (female)
                    a = -125.4255398
                    b = 13.71219419
                    c = -0.03307250631
                    d = -0.001050400051
                    e = 0.00000938773881462799
                    f = -0.000000023334613884954
                    denominator = (
                        a +
                        b * bw +
                        c * bw ** 2 +
                        d * bw ** 3 +
                        e * bw ** 4 +
                        f * bw ** 5
                    )
                    if denominator != 0:
                        wilks_relative_intensity = int(round(relative_intensity * 600 / denominator))

            # Persist updates for this row
            conn.execute(
                update(movement_table)
                .where(movement_table.c.Set == set_id)
                .values(
                    Relative_Intensity=relative_intensity,
                    Wilks_Relative_intensity=wilks_relative_intensity
                )
            )