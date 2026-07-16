from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert, select
import app as app_module


def test_profile_route_updates_gender_and_body_weight(tmp_path):
    db_path = tmp_path / "profile_test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)

    metadata = MetaData()
    users_table = Table(
        "Users",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("username", String, unique=True, nullable=False),
        Column("password_hash", String, nullable=False),
        Column("gender", String, nullable=True),
        Column("body_weight", Integer, nullable=True),
    )
    metadata.create_all(engine)

    app_module.engine = engine
    app_module.metadata = metadata
    app_module.users_table = users_table

    with engine.begin() as conn:
        conn.execute(insert(users_table).values(username="tester", password_hash="hash"))

    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "tester"

    response = client.post("/profile", data={"gender": "female", "body_weight": "72"}, follow_redirects=True)

    assert response.status_code == 200

    with engine.connect() as conn:
        row = conn.execute(select(users_table.c.gender, users_table.c.body_weight).where(users_table.c.id == 1)).fetchone()

    assert row.gender == "female"
    assert row.body_weight == 72
