
from sqlalchemy import Column, Integer, String, Table, MetaData, create_engine

def create_movement_table(table_name: str,
                          db_url: str = 'sqlite:///Fitness_Database.db',
                          unique: bool = False):
    """
    Create a new movement table in the database and return the Table object.

    Parameters:
    - table_name: desired table name (spaces will be replaced with underscores).
    - db_url: SQLAlchemy database URL (default: sqlite:///Fitness_Database.db).
    - unique: if True, append a timestamp suffix to table_name to ensure uniqueness.

    Returns:
    - sqlalchemy.Table object for the created table.
    """
    if not table_name or not isinstance(table_name, str):
        raise ValueError("table_name must be a non-empty string")

        
    print(f"Creating table with name: {table_name} in database: {db_url}")  # Debug print

    engine = create_engine(db_url)
    metadata = MetaData()

    movement_table = Table(
        table_name,
        metadata,
        Column('Set', Integer, primary_key=True),
        Column('Reps', Integer),
        Column('Weight', Integer),
        Column('Body_Weight', Integer),
        Column('Date', String),
        Column('Tonnage', Integer),
        Column('Relative_Intensity', Integer),
        Column('Wilks_Tonnage', Integer),
        Column('Wilks_Relative_Intensity', Integer),
        Column('One_Rep_Max', Integer),
    )

    # create only this table (no-op if it already exists)
    metadata.create_all(engine, tables=[movement_table])
    return movement_table, engine

# Example usage:
if __name__ == "__main__":
    tbl, eng = create_movement_table("Movement Table", unique=True)
    print(f"Created table: {tbl.name} in {eng.url}")

