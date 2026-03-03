from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from Create_new_table import create_movement_table

def calculate_and_fill_one_rep_max(table_name: str, db_url: str = 'sqlite:///Movement_Database.db'):
    """
    Calculates and fills the One_Rep_Max column for each row in the specified movement table.
    Formula: One_Rep_Max = Weight * (1 + (Reps / 30))
    """
    # Get the table and engine
    movement_table, engine = create_movement_table(table_name, db_url=db_url)

    with engine.connect() as conn:
        # Select all rows
        select_stmt = select(movement_table.c.Set, movement_table.c.Weight, movement_table.c.Reps)
        results = conn.execute(select_stmt).fetchall()

        for row in results:
            set_id = row[0]
            weight = row[1]
            reps = row[2]
            if weight is not None and reps is not None:
                one_rep_max = int(round(weight * (1 + (reps / 30))))
                # Update the One_Rep_Max column for this row
                upd = (
                    update(movement_table)
                    .where(movement_table.c.Set == set_id)
                    .values(One_Rep_Max=one_rep_max)
                )
                conn.execute(upd)
        conn.commit()

# Example usage:
# calculate_and_fill_one_rep_max("Movement Table")