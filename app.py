# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, Response
from sqlalchemy import Column, Integer, String, Table, MetaData, create_engine, insert, select, ForeignKey, func
from werkzeug.security import generate_password_hash, check_password_hash
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

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

@app.route("/tonnage_plot")
def tonnage_plot():
    # Only allow logged-in users to fetch their plot
    if "user_id" not in session:
        return Response("Unauthorized", status=401)

    with engine.connect() as conn:
        stmt = select(
            movement_table.c.id,
            movement_table.c.Date,
            movement_table.c.Tonnage,
            movement_table.c.Relative_Intensity,
            movement_table.c.One_Rep_Max
        ).where(
            movement_table.c.user_id == session["user_id"]
        ).order_by(movement_table.c.Date.asc())
        rows = conn.execute(stmt).fetchall()

    # Build structured list with parsed dates so we can find the PB set's date easily
    entries = []
    for r in rows:
        if r.Date is None:
            continue
        date_str = r.Date
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                continue

        entries.append({
            "id": r.id,
            "dt": dt,
            "tonnage": (int(r.Tonnage) if r.Tonnage is not None else None),
            "rel_int": (int(r.Relative_Intensity) if r.Relative_Intensity is not None else None),
            "one_rm": (int(r.One_Rep_Max) if r.One_Rep_Max is not None else None)
        })

    # Separate lists for plotting
    dates_t = [e["dt"] for e in entries if e["tonnage"] is not None]
    tonnages = [e["tonnage"] for e in entries if e["tonnage"] is not None]
    dates_r = [e["dt"] for e in entries if e["rel_int"] is not None]
    rel_intensities = [e["rel_int"] for e in entries if e["rel_int"] is not None]

    # Determine PB One Rep Max and the date of the corresponding set (use most recent date if ties)
    pb_one_rm = None
    pb_date = None
    one_rms = [e["one_rm"] for e in entries if e["one_rm"] is not None]
    if one_rms:
        pb_one_rm = max(one_rms)
        # find entries with that one_rm and pick the latest date
        pb_entries = [e for e in entries if e["one_rm"] == pb_one_rm]
        if pb_entries:
            pb_date = max(e["dt"] for e in pb_entries)

    # Create image
    img_io = io.BytesIO()
    plt.figure(figsize=(8, 3.5))
    if not dates_t and not dates_r:
        plt.text(0.5, 0.5, "No tonnage or relative intensity data", horizontalalignment='center', verticalalignment='center', fontsize=14)
        plt.axis('off')
    else:
        ax = plt.gca()
        if dates_t:
            ax.plot(dates_t, tonnages, marker='o', linestyle='-', color='#2b7a78', label='Tonnage')
            ax.fill_between(dates_t, tonnages, color='#95d5b2', alpha=0.3)
            ax.set_ylabel("Tonnage (Reps x Weight)")
        ax.set_xlabel("Date")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45, ha='right')
        plt.grid(alpha=0.25)

        # Plot relative intensity on secondary axis if present
        ax2 = None
        if dates_r:
            ax2 = ax.twinx()
            ax2.plot(dates_r, rel_intensities, marker='s', linestyle='--', color='#f45b69', label='Relative Intensity')
            ax2.set_ylabel("Relative Intensity (ratio)")
            # Optionally tighten y-limits for readability
            try:
                ymin, ymax = min(rel_intensities), max(rel_intensities)
                pad = max(1, int((ymax - ymin) * 0.1)) if ymax != ymin else 1
                ax2.set_ylim(max(0, ymin - pad), ymax + pad)
            except Exception:
                pass

        # Draw PB indicator if we found a pb_date
        if pb_date is not None:
            # vertical dashed line
            ax.axvline(pb_date, color='orange', linestyle=':', linewidth=1.5, alpha=0.9)
            # place label near top of plotting area (use ax coordinates to avoid scale issues)
            ylim = ax.get_ylim()
            # text slightly above top of plot area using transform
            ax.text(pb_date, ylim[1], "PB One Rep Max", color='orange', fontsize=9, ha='center', va='bottom',
                    backgroundcolor='white', bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))

        plt.tight_layout()
        # optional legend combining both axes
        try:
            lines, labels = ax.get_legend_handles_labels()
            if ax2 is not None:
                lines2, labels2 = ax2.get_legend_handles_labels()
                lines += lines2
                labels += labels2
            if lines:
                ax.legend(lines, labels, loc='upper left', fontsize='small')
        except Exception:
            pass

    plt.savefig(img_io, format='png', bbox_inches='tight')
    plt.close()
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/", methods=["GET", "POST"])
def index():
    # Enforce login
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            # Parse basic form values
            set_val = int(request.form.get("Set"))
            reps = int(request.form.get("Reps"))
            weight = int(request.form.get("Weight"))
            body_weight = int(request.form.get("Body_Weight"))
            date_str = request.form.get("Date")

            # Calculate tonnage (Reps * Weight)
            tonnage = reps * weight

            # Calculate One Rep Max using common formula: Weight * (1 + Reps/30)
            one_rm = int(round(weight * (1 + (reps / 30.0))))

            # Determine user's current PB (max One_Rep_Max) to compute relative intensity
            with engine.connect() as conn:
                pb_stmt = select(func.max(movement_table.c.One_Rep_Max)).where(movement_table.c.user_id == session["user_id"])
                pb_result = conn.execute(pb_stmt).scalar()
                PB_1rm = None if pb_result is None else pb_result

            # Compute relative intensity as integer ratio (fallback to 1 if no PB)
            if PB_1rm and PB_1rm != 0:
                relative_intensity = int(round(float(one_rm) / float(PB_1rm)))
            else:
                # No PB yet: treat this set as baseline (relative intensity = 1)
                relative_intensity = 1

            form_data = {
                "user_id": session["user_id"], # Attach data to logged-in user
                "Set": set_val,
                "Reps": reps,
                "Weight": weight,
                "Body_Weight": body_weight,
                "Date": date_str,
                "Tonnage": tonnage,
                "One_Rep_Max": one_rm,
                "Relative_Intensity": relative_intensity
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

@app.route("/delete_set", methods=["POST"])
def delete_set():
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    entry_id = request.form.get("entry_id")
    try:
        entry_id = int(entry_id)
    except Exception:
        flash("Invalid entry id.", "error")
        return redirect(url_for("index"))

    with engine.begin() as conn:
        # Verify entry exists and belongs to current user
        stmt = select(movement_table.c.user_id).where(movement_table.c.id == entry_id)
        row = conn.execute(stmt).fetchone()
        if not row:
            flash("Entry not found.", "error")
            return redirect(url_for("index"))

        owner_id = row[0]
        if owner_id != session["user_id"]:
            flash("Not authorized to delete this entry.", "error")
            return redirect(url_for("index"))

        # Delete the entry
        conn.execute(movement_table.delete().where(movement_table.c.id == entry_id))
        flash("Entry deleted.", "success")

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
