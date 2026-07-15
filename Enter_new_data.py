import sqlite3
from datetime import datetime

def log_workout(set_value, weight, reps, date, body_weight):

    if set_value <= 0:
        raise ValueError("Set must be greater than 0")
    if weight <= 0:
        raise ValueError("Weight must be greater than 0")
    if reps <= 0:
        raise ValueError("Reps must be greater than 0")
    if body_weight <= 0:
        raise ValueError("Body weight must be greater than 0")

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be YYYY-MM-DD")

    with sqlite3.connect("Fitness_Database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO "Movement Table" ("Set", Reps, Weight, Body_Weight, Date) VALUES (?, ?, ?, ?, ?)',
            (set_value, reps, weight, body_weight, date)
        )
        conn.commit()


if __name__ == "__main__":
    log_workout(1, 135, 8, "2026-03-03", 180)