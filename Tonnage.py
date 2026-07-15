from sqlalchemy import select, update
from Create_new_table import create_movement_table

def calculate_and_fill_tonnage(
    table_name: str,
    db_url: str = 'sqlite:///Fitness_Database.db'
):

    movement_table, engine = create_movement_table(table_name, db_url=db_url)

    with engine.connect() as conn:

        select_stmt = select(
            movement_table.c.id,     # ✅ use id
            movement_table.c.Set,
            movement_table.c.Weight,
            movement_table.c.Reps
        )

        results = conn.execute(select_stmt).fetchall()

        for row in results:
            row_id = row[0]
            set_value = row[1]
            weight = row[2]
            reps = row[3]

            if set_value and weight and reps:
                tonnage = int(set_value * weight * reps)

                upd = (
                    update(movement_table)
                    .where(movement_table.c.id == row_id)  # ✅ SAFE
                    .values(Tonnage=tonnage)
                )

                conn.execute(upd)

        conn.commit()