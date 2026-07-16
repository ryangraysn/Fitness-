import unittest
import os
import tempfile
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert, select
import app as app_module


class WeightUnitConversionTest(unittest.TestCase):
    def setUp(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.metadata = MetaData()

        self.users_table = Table(
            "Users",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("username", String, unique=True, nullable=False),
            Column("password_hash", String, nullable=False),
            Column("gender", String, nullable=True),
            Column("body_weight", Integer, nullable=True),
        )
        self.movements_table = Table(
            "Movements",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("user_id", Integer, nullable=False),
            Column("name", String, nullable=False),
            Column("table_name", String, nullable=False),
        )
        self.metadata.create_all(self.engine)

        app_module.engine = self.engine
        app_module.metadata = self.metadata
        app_module.users_table = self.users_table
        app_module.movements_table = self.movements_table

        with self.engine.begin() as conn:
            conn.execute(insert(self.users_table).values(username="tester", password_hash="hash"))
            conn.execute(insert(self.movements_table).values(user_id=1, name="Squat", table_name="Movement_1_test"))

        app_module.ensure_movement_table("Movement_1_test")
        with self.engine.begin() as conn:
            movement_table = app_module.load_movement_table("Movement_1_test")
            conn.execute(insert(movement_table).values(user_id=1, Set=1, Reps=5, Weight=50, Body_Weight=80, Date="2026-01-01", Tonnage=250, Relative_Intensity=1, One_Rep_Max=100))

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def test_index_route_converts_weight_values_for_lbs_display(self):
        client = app_module.app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["weight_unit"] = "lbs"

        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("110.23", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
