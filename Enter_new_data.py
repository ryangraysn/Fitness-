import sqlite3

def log_workout(set, weight, reps, weight, body_weight, date, tonnage, relative_intensity, wilks_tonnage, wilks_relative_intensity, one_rep_max):
        # Code to validate input data #

        if set <=0:
            raise ValueError("Sets must be greater than 0")
        if weight <=0:
            raise ValueError("Weight must be greater than 0")
        if reps<=0:
            raise ValueError("Reps must be greater than 0")
        if date <=0:
            raise ValueError("Date must be greater than 0")
        
        # Code to connect to the database and insert the workout data #

        with sqlite3.connect('#insert file name#') as conn:
            cursor = conn.cursor()
            # execute SQL here
            cursor.execute("INSERT INTO workouts (set, weight, reps, body_weight, date, tonnage, relative_intensity, wilks_tonnage, wilks_relative_intensity, one_rep_max) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (set, weight, reps, body_weight, date, tonnage, relative_intensity, wilks_tonnage, wilks_relative_intensity, one_rep_max))
        

