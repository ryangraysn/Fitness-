import os
import tempfile
from sqlalchemy import inspect
from Create_new_table import create_movement_table

def test_create_movement_table_added():
    # create a temp sqlite file so multiple connections see the same DB
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        db_url = f"sqlite:///{db_path}"
        table_name = "movement_table_test"

        # create the table in the temp DB
        tbl, engine = create_movement_table(table_name, db_url=db_url)

        # inspect the DB for table presence
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert table_name in tables, f"Expected table '{table_name}' to exist; found {tables}"
    finally:
        # cleanup temp DB file
        try:
            os.remove(db_path)
        except OSError:
            pass