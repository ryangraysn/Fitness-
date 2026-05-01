from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import Column, Integer, String, Table, MetaData, create_engine, insert, select, ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this_in_production" # Required for sessions

# --- Database Setup ---
DB_URL = 'sqlite:///Fitness_Database.db'
engine = create_engine(DB_URL)
metadata = MetaData()

# 1. New Users Table
users_table = Table(
    'Users', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

# 2. Updated Movement Table
movement_table = Table(
    'Movement_Table', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True), # New Primary Key
    Column('user_id', Integer, ForeignKey('Users.id'), nullable=False), # Links to user
    Column('Set', Integer), # No longer the PK
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

# Create tables if they don't exist
metadata.create_all(engine)

# --- Routes ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")
        password = request.form.get("password")

        with engine.connect() as conn:
            if action == "register":
                # Check if user exists
                existing = conn.execute(select(users_table).where(users_table.c.username == username)).fetchone()
                if existing:
                    flash("Username already exists.", "error")
                else:
                    # Create new user
                    hashed_pw = generate_password_hash(password)
                    conn.execute(insert(users_table).values(username=username, password_hash=hashed_pw))
                    conn.commit()
                    flash("Registration successful! Please log in.", "success")
            
            elif action == "login":
                # Verify user
                user = conn.execute(select(users_table).where(users_table.c.username == username)).fetchone()
                if user and check_password_hash(user.password_hash, password):
                    session["user_id"] = user.id
                    session["username"] = user.username
                    return redirect(url_for("index"))
                else:
                    flash("Invalid username or password.", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    # Enforce login
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            form_data = {
                "user_id": session["user_id"], # Attach data to logged-in user
                "Set": int(request.form.get("Set")),
                "Reps": int(request.form.get("Reps")),
                "Weight": int(request.form.get("Weight")),
                "Body_Weight": int(request.form.get("Body_Weight")),
                "Date": request.form.get("Date"),

            }

            with engine.begin() as conn:
                conn.execute(insert(movement_table).values(**form_data))
            flash("Workout data logged successfully!", "success")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")

    # Fetch this specific user's past data to display
    with engine.connect() as conn:
        stmt = select(movement_table).where(movement_table.c.user_id == session["user_id"]).order_by(movement_table.c.Date.desc())
        user_workouts = conn.execute(stmt).fetchall()

    return render_template("index.html", workouts=user_workouts, username=session["username"])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
