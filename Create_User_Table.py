
from sqlalchemy import Column, Integer, String, Table, MetaData, create_engine

def create_user_table(table_name: str,
                          db_url: str = 'sqlite:///Fitness_Database.db',
                          unique: bool = False):
    """
    Create a new user table in the database and return the Table object.

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

    user_table = Table(
        table_name,
        metadata,
        Column('User', Integer, primary_key=True),
        Column('Gender', Integer, primary_key=True)
        
    )

    # create only this table (no-op if it already exists)
    metadata.create_all(engine, tables=[user_table])
    return user_table, engine

# Example usage:
if __name__ == "__main__":
    tbl, eng = create_user_table("user Table", unique=True)
    print(f"Created table: {tbl.name} in {eng.url}")

