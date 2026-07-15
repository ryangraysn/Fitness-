from sqlalchemy import Column, Integer, String, Table, MetaData, create_engine

def create_movement_table(
    table_name: str,
    db_url: str = 'sqlite:///Fitness_Database.db'
):

    engine = create_engine(db_url)
    metadata = MetaData()

    movement_table = Table(
        table_name,
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),  # ✅ NEW
        Column('Set', Integer),  # keep it
        Column('Reps', Integer),
        Column('Weight', Integer),
        Column('Body_Weight', Integer),
        Column('Date', String),
        Column('Tonnage', Integer),
        Column('One_Rep_Max', Integer),
    )

    metadata.create_all(engine)
    return movement_table, engine


if __name__ == "__main__":
    create_movement_table("Movement Table")