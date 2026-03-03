from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from Create_new_table import create_movement_table

def Best_one_rep_max(table_name: str, db_url: str = 'sqlite:///Movement_Database.db'):
    """
    Calculates and fills the One_Rep_Max column for each row in the specified movement table.
    Formula: One_Rep_Max = Weight * (1 + (Reps / 30))
    """
    # Get the table and engine
    movement_table, engine = create_movement_table(table_name, db_url=db_url)

    with engine.connect() as conn:
        # Select all rows
        select_stmt = select(movement_table.c.Set, movement_table.c.one_rep_max)
        results = conn.execute(select_stmt).fetchall()

        for row in results:
            set_id = row[0]
            one_rep_max = row[1]
            
            if one_rep_max is not None:
                return max(one_rep_max)
                
        conn.commit()

