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
import re

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this_in_production" # Required for sessions

# --- Database Setup ---
DB_URL = 'sqlite:///Fitness_Database.db'
engine = create_engine(DB_URL)
metadata = MetaData()

# 1. Users Table
users_table = Table(
    'Users', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

# 2. Movement categories registry (per-user)
movements_table = Table(
    'Movements', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('Users.id'), nullable=False),
    Column('name', String, nullable=False),
    Column('table_name', String, unique=True, nullable=False)
)

# Create registry / user tables if they don't exist
metadata.create_all(engine)

# Helper: slugify movement name into a safe table name fragment
def _slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9_]+', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    if not name:
        name = 'movement'
    return name

# Helper: ensure per-movement table exists; returns a Table object
def ensure_movement_table(table_name: str):
    # Use the global metadata so ForeignKey('Users.id') can be resolved
    t = Table(
        table_name, metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('user_id', Integer, ForeignKey('Users.id'), nullable=False),
        Column('Set', Integer),
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
    # create physical table if not exists; using metadata attached to t allows FK resolution
    t.create(engine, checkfirst=True)
    return t

# Helper: load existing movement table object (autoload)
def load_movement_table(table_name: str):
    try:
        # use the same global metadata for autoload so FK references are known
        t = Table(table_name, metadata, autoload_with=engine)
        return t
    except Exception:
        # If autoload fails, create it (fallback)
        return ensure_movement_table(table_name)

@app.route("/create_movement", methods=["POST"])
def create_movement():
    if "user_id" not in session:
        return redirect(url_for("login"))
    name = request.form.get("movement_name", "").strip()
    if not name:
        flash("Movement name required.", "error")
        return redirect(url_for("index"))
    slug = _slugify(name)
    table_name = f"Movement_{session['user_id']}_{slug}"
    # ensure unique table_name if duplicate slug exists
    suffix = 1
    base_table_name = table_name
    with engine.begin() as conn:
        while conn.execute(select(movements_table).where(movements_table.c.table_name == table_name)).fetchone():
            suffix += 1
            table_name = f"{base_table_name}_{suffix}"
        # insert movement record
        conn.execute(insert(movements_table).values(user_id=session["user_id"], name=name, table_name=table_name))
    # create movement table
    ensure_movement_table(table_name)
    flash("Movement created.", "success")
    return redirect(url_for("index"))

@app.route("/delete_movement", methods=["POST"])
def delete_movement():
    if "user_id" not in session:
        return redirect(url_for("login"))
    movement_id = request.form.get("movement_id")
    try:
        movement_id = int(movement_id)
    except Exception:
        flash("Invalid movement id.", "error")
        return redirect(url_for("index"))
    with engine.begin() as conn:
        mv = conn.execute(select(movements_table).where(movements_table.c.id == movement_id)).fetchone()
        if not mv:
            flash("Movement not found.", "error")
            return redirect(url_for("index"))
        if mv.user_id != session["user_id"]:
            flash("Not authorized.", "error")
            return redirect(url_for("index"))
        table_name = mv.table_name
        # drop physical table if present — use global metadata for autoload so FKs resolve
        try:
            t = Table(table_name, metadata, autoload_with=engine)
            t.drop(engine, checkfirst=True)
        except Exception:
            pass
        # remove movement registry row
        conn.execute(movements_table.delete().where(movements_table.c.id == movement_id))
    flash("Movement deleted.", "success")
    return redirect(url_for("index"))

@app.route("/tonnage_plot")
def tonnage_plot():
    # Only allow logged-in users to fetch their plot
    if "user_id" not in session:
        return Response("Unauthorized", status=401)

    movement_id = request.args.get("m", type=int)
    if not movement_id:
        return Response("No movement selected", status=400)

    with engine.connect() as conn:
        mv = conn.execute(select(movements_table).where(movements_table.c.id == movement_id, movements_table.c.user_id == session["user_id"])).fetchone()
        if not mv:
            return Response("Movement not found", status=404)
        table_name = mv.table_name

        # load rows from that movement table
        try:
            t = load_movement_table(table_name)
            stmt = select(t.c.id, t.c.Date, t.c.Tonnage, t.c.Relative_Intensity, t.c.One_Rep_Max).where(t.c.user_id == session["user_id"]).order_by(t.c.Date.asc())
            rows = conn.execute(stmt).fetchall()
        except Exception:
            rows = []

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

        ax2 = None
        if dates_r:
            ax2 = ax.twinx()
            ax2.plot(dates_r, rel_intensities, marker='s', linestyle='--', color='#f45b69', label='Relative Intensity')
            ax2.set_ylabel("Relative Intensity (ratio)")
            try:
                ymin, ymax = min(rel_intensities), max(rel_intensities)
                pad = max(1, int((ymax - ymin) * 0.1)) if ymax != ymin else 1
                ax2.set_ylim(max(0, ymin - pad), ymax + pad)
            except Exception:
                pass

        if pb_date is not None:
            ax.axvline(pb_date, color='orange', linestyle=':', linewidth=1.5, alpha=0.9)
            ylim = ax.get_ylim()
            ax.text(pb_date, ylim[1], "PB One Rep Max", color='orange', fontsize=9, ha='center', va='bottom',
                    backgroundcolor='white', bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))

        plt.tight_layout()
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

    # load user's movements
    with engine.connect() as conn:
        movements = conn.execute(select(movements_table).where(movements_table.c.user_id == session["user_id"])).fetchall()

    # find selected movement id from query param or default to first movement
    selected_movement_id = request.args.get("m", type=int)
    if not selected_movement_id and movements:
        selected_movement_id = movements[0].id

    selected_movement = None
    workouts = []
    if selected_movement_id:
        with engine.connect() as conn:
            selected_movement = conn.execute(select(movements_table).where(movements_table.c.id == selected_movement_id, movements_table.c.user_id == session["user_id"])).fetchone()
            if selected_movement:
                # load movement-specific table and fetch workouts
                t = load_movement_table(selected_movement.table_name)
                stmt = select(t).where(t.c.user_id == session["user_id"]).order_by(t.c.Date.desc(), t.c.Set.asc())
                try:
                    workouts = conn.execute(stmt).fetchall()
                except Exception:
                    workouts = []

    if request.method == "POST":
        # logging a set — requires movement_id in form
        movement_id = request.form.get("movement_id", type=int)
        if not movement_id:
            flash("Select a movement first.", "error")
            return redirect(url_for("index"))
        # ensure movement belongs to user
        with engine.connect() as conn:
            mv = conn.execute(select(movements_table).where(movements_table.c.id == movement_id, movements_table.c.user_id == session["user_id"])).fetchone()
            if not mv:
                flash("Movement not found.", "error")
                return redirect(url_for("index"))
            table_name = mv.table_name

        try:
            reps = int(request.form.get("Reps"))
            weight = int(request.form.get("Weight"))
            body_weight = int(request.form.get("Body_Weight"))
            date_str = request.form.get("Date")

            per_set_tonnage = reps * weight
            one_rm = int(round(weight * (1 + (reps / 30.0))))

            # Determine user's current PB in this movement
            # Use a transaction so insert + update are committed
            with engine.begin() as conn:
                t = load_movement_table(table_name)
                pb_stmt = select(func.max(t.c.One_Rep_Max)).where(t.c.user_id == session["user_id"])
                pb_result = conn.execute(pb_stmt).scalar()
                PB_1rm = None if pb_result is None else pb_result

                # compute next set number for this user/date in this movement
                max_set_stmt = select(func.max(t.c.Set)).where(t.c.user_id == session["user_id"], t.c.Date == date_str)
                max_set = conn.execute(max_set_stmt).scalar()
                set_val = 1 if max_set is None else int(max_set) + 1

                if PB_1rm and PB_1rm != 0:
                    relative_intensity = int(round(float(one_rm) / float(PB_1rm)))
                else:
                    relative_intensity = 1

                form_data = {
                    "user_id": session["user_id"],
                    "Set": set_val,
                    "Reps": reps,
                    "Weight": weight,
                    "Body_Weight": body_weight,
                    "Date": date_str,
                    "Tonnage": per_set_tonnage,
                    "One_Rep_Max": one_rm,
                    "Relative_Intensity": relative_intensity
                }

                # insert into movement-specific table and recompute daily total for that movement/date
                conn.execute(insert(t).values(**form_data))

                daily_total_stmt = select(func.sum(t.c.Reps * t.c.Weight)).where(t.c.user_id == session["user_id"], t.c.Date == date_str)
                daily_total = conn.execute(daily_total_stmt).scalar()
                if daily_total is None:
                    daily_total = 0
                try:
                    daily_total = int(daily_total)
                except Exception:
                    daily_total = int(round(float(daily_total)))

                conn.execute(
                    t.update()
                    .where(t.c.user_id == session["user_id"])
                    .where(t.c.Date == date_str)
                    .values(Tonnage=daily_total)
                )

            flash("Workout data logged successfully!", "success")
            return redirect(url_for("index", m=movement_id))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for("index", m=movement_id))

    # GET: render page (workouts loaded above)
    return render_template("index.html", workouts=workouts, username=session["username"], movements=movements, selected_movement=selected_movement)

@app.route("/delete_set", methods=["POST"])
def delete_set():
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    entry_id = request.form.get("entry_id")
    movement_id = request.form.get("movement_id", type=int)
    try:
        entry_id = int(entry_id)
    except Exception:
        flash("Invalid entry id.", "error")
        return redirect(url_for("index"))

    if not movement_id:
        flash("Missing movement id.", "error")
        return redirect(url_for("index"))

    with engine.begin() as conn:
        mv = conn.execute(select(movements_table).where(movements_table.c.id == movement_id)).fetchone()
        if not mv:
            flash("Movement not found.", "error")
            return redirect(url_for("index"))
        if mv.user_id != session["user_id"]:
            flash("Not authorized to delete this entry.", "error")
            return redirect(url_for("index"))

        t = load_movement_table(mv.table_name)
        # Verify entry exists and belongs to current user
        row = conn.execute(select(t.c.user_id, t.c.Date).where(t.c.id == entry_id)).fetchone()
        if not row:
            flash("Entry not found.", "error")
            return redirect(url_for("index", m=movement_id))

        owner_id, entry_date = row[0], row[1]
        if owner_id != session["user_id"]:
            flash("Not authorized to delete this entry.", "error")
            return redirect(url_for("index", m=movement_id))

        # Delete the entry from the movement-specific table
        conn.execute(t.delete().where(t.c.id == entry_id))

        # Recompute daily total for that date and update remaining rows for that date (use t)
        daily_total_stmt = select(func.sum(t.c.Reps * t.c.Weight)).where(
            t.c.user_id == session["user_id"],
            t.c.Date == entry_date
        )
        daily_total = conn.execute(daily_total_stmt).scalar()
        if daily_total is None:
            daily_total = 0
        try:
            daily_total = int(daily_total)
        except Exception:
            daily_total = int(round(float(daily_total)))

        conn.execute(
            t.update()
            .where(t.c.user_id == session["user_id"])
            .where(t.c.Date == entry_date)
            .values(Tonnage=daily_total)
        )

        flash("Entry deleted.", "success")

    return redirect(url_for("index", m=movement_id))

@app.route("/progress")
def progress():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with engine.connect() as conn:
        movements = conn.execute(select(movements_table).where(movements_table.c.user_id == session["user_id"])).fetchall()
    return render_template("progress.html", username=session["username"], movements=movements, selected_tab='progress', selected_movement=None)

@app.route("/science")
def science():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with engine.connect() as conn:
        movements = conn.execute(select(movements_table).where(movements_table.c.user_id == session["user_id"])).fetchall()
    return render_template("science.html", username=session["username"], movements=movements, selected_tab='science', selected_movement=None)

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with engine.connect() as conn:
        movements = conn.execute(select(movements_table).where(movements_table.c.user_id == session["user_id"])).fetchall()
    return render_template("profile.html", username=session["username"], movements=movements, selected_tab='profile', selected_movement=None)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
