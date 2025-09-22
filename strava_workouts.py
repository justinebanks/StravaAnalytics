from strava import *
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv
import pandas as pd
import regex
import json
from datetime import datetime
import os

load_dotenv()

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")


class Exercise:
    def __init__(self, name):
        self.name = name
        self.workout_id = None
        self.date = None
        self.sets: list[dict] = [] # List of dicts with keys "reps" and "weight"
    
    def as_dict(self):
        return {
            "name": self.name,
            "workout_id": self.workout_id,
            "date": self.date,
            "sets": self.sets
        }

    @classmethod
    def from_dict(cls, data: dict): # { workout_id, date, exercise: { name, sets: [ { reps, weight } ] } }
        exercise = cls(data["name"])
        exercise.date = data["date"]
        exercise.workout_id = data["workout_id"]
        exercise.sets = data["sets"]
        return exercise
    
    @staticmethod
    def sort_by_date(exercises: list):
        return  sorted(exercises, key=lambda ex: datetime.strptime(ex.date, "%Y-%m-%dT%H:%M:%SZ"))



class WorkoutSession:
    def __init__(self, id, auto_retrieve_data=True, access_token=None):
        self.access_token = access_token

        self.id = id
        self.name = ""
        self.date = None
        self.description = ""
        self.exercises = []

        if auto_retrieve_data:
            assert access_token is not None, "Access token must be provided if auto_retrieve_data is True"
            self.retrieve_data(access_token)
            self.parse_description()


    def __repr__(self):
        result = f"Workout ID: {self.id}\n"
        result += f"Workout Name: {self.name}\n"
        result += f"Workout Date: {self.date}\n"
        result += f"Description: \n{self.description}\n"
        result += f"Parsed Exercises: {json.dumps(self.exercises, indent=4)}\n"
        result += "----------------------------------------\n\n"
        return result


    def retrieve_data(self, access_token):
        workout = get_activity(access_token, self.id)

        if type(workout) is int:
            raise ValueError(workout)
        else:
            self.name = workout["name"]
            self.date = workout["start_date"]
            self.description = workout["description"]


    def parse_description(self):
        pattern = r"(?:(?P<sets>\d{1,3})x(?P<reps>\d{1,3})|(?P<all>[0-9][0-9\-, ]+)) (?P<exercise>[A-Za-z'’+\-/0-9 ]+)[ ]?(?:\((?:(?P<weight>[0-9@\.]+)[, ]{0,3})+)?"
        matches = regex.finditer(pattern, self.description)
        exercises = []

        for match in matches: # Runs For Each Detected Exercise
            group_dict = match.groupdict()
            exercise_name = group_dict["exercise"].strip()
            sets = []

            weight_list = match.captures("weight") # List of weights on each set
            rep_list = [] # List of reps on each set

            if group_dict["all"]:
                if "-" in group_dict["all"]:
                    rep_list = group_dict["all"].split("-")
                elif ", " in group_dict["all"]:
                    rep_list = group_dict["all"].split(", ")
                elif "," in group_dict["all"]:
                    rep_list = group_dict["all"].split(",")
                else:
                    rep_list = [group_dict["all"]]
            elif group_dict["reps"] and group_dict["sets"]:
                rep_list = [group_dict["reps"]] * int(group_dict["sets"])
            
            if len(weight_list) == 1 and len(rep_list) > 1:
                weight_list = [weight_list[0]] * len(rep_list)
            
            if (len(weight_list) == 0):
                weight_list = [None] * len(rep_list)
                exercises.append({
                    "name": exercise_name,
                    "sets": [{"reps": int(rep), "weight": None} for rep in rep_list]
                })
                continue
            
            if (len(weight_list) < len(rep_list)):
                weight_list = weight_list + [weight_list[-1]] * (len(rep_list) - len(weight_list))


            assert len(weight_list) == len(rep_list), f"Weight list and rep list lengths do not match for exercise {exercise_name} in workout {self.id}"
            
            for i in range(len(rep_list)): # Runs For Each Set Detected For The Exercise
                reps = None
                weight = None

                weight_sections = weight_list[i].split("@")

                if len(weight_sections) == 2:
                    reps = weight_sections[0]
                    weight = weight_sections[1]
                else:
                    reps = rep_list[i]
                    weight = weight_list[i]
                
                sets.append({
                    "reps": int(reps),
                    "weight": float(weight)
                })

            exercises.append({
                "name": exercise_name,
                "sets": sets
            })

        self.exercises = exercises
    

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date,
            "description": self.description,
            "exercises": self.exercises
        }


def get_workout_ids(access_token: str):
    start_time = datetime.strptime("2023-06-27T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_time = datetime.strptime("2024-06-27T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")

    activities = get_athlete_activities(access_token, start_time, end_time)
    ids = [activity['id'] for activity in activities if activity["type"] == "Workout"] # or activity["type"] == "WeightTraining"

    print(f"Found {len(ids)} weight training activities")

    with open("workout_ids2.json", "w") as f:
        json.dump(ids, f, indent=4)
    
    return ids


def get_workouts_from_strava(access_token, filename=None, start_index=0):
    # ids = get_workout_ids(access_token)
    with open("workout_ids2.json", "r") as f:
        ids = json.load(f)[start_index:]

    all_workouts_json = []
    all_workouts = []

    for activity_id in ids:
        workout = WorkoutSession(activity_id, access_token=access_token)
        # print(workout)
        print("Retrieved workout:", workout.id)
        all_workouts.append(workout)
        all_workouts_json.append(workout.as_dict())

    if filename is not None:
        # Save all workouts to a JSON file
        with open(filename, "w") as f:
            json.dump(all_workouts_json, f, indent=4)

        print(f"Saved {len(all_workouts)} workouts to {filename}")
    
    return all_workouts


def get_workouts_from_json(filename):
    with open(filename, "r") as f:
        workouts_data = json.load(f)
    
    all_workouts = []
    for workout_data in workouts_data:
        workout = WorkoutSession(workout_data["id"], auto_retrieve_data=False)
        workout.name = workout_data["name"]
        workout.date = workout_data["date"]
        workout.description = workout_data["description"]
        workout.exercises = workout_data["exercises"]
        all_workouts.append(workout)
    
    return all_workouts


def save_exercises_to_excel(exercises: list[Exercise], filename, sheet_name):
    current_row = 2
    workbook = load_workbook(filename) if os.path.exists(filename) else Workbook()
    sheet = None

    if sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
    else: 
        sheet = workbook.create_sheet(title=sheet_name)

    # Create Column Headers
    headers = ["Workout ID", "Date", "Exercise Name", "# Sets", "Total Reps", "Total Weight", "Average Reps/Set", "Average Weight/Rep", "Estimated 1RM"]
    for col_num, header in enumerate(headers, 1):
        sheet.cell(row=1, column=col_num, value=header)
        sheet.column_dimensions[get_column_letter(col_num)].width = 15

    # Fill in Data
    for exercise in exercises:
        total_reps = sum(int(s["reps"]) for s in exercise.sets if s["reps"] is not None)
        total_weight = sum(int(s["reps"]) * float(s["weight"]) for s in exercise.sets if s["reps"] is not None and s["weight"] is not None)

        sheet.cell(row=current_row, column=1, value=exercise.workout_id)
        sheet.cell(row=current_row, column=2, value=exercise.date)
        sheet.cell(row=current_row, column=3, value=exercise.name)
        sheet.cell(row=current_row, column=4, value=len(exercise.sets))
        sheet.cell(row=current_row, column=5, value=total_reps)
        sheet.cell(row=current_row, column=6, value=total_weight)

        sheet[get_column_letter(7) + str(current_row)] = f"=TRUNC(E{current_row}/D{current_row}, 2)"
        sheet[get_column_letter(8) + str(current_row)] = f"=TRUNC(IF(E{current_row}=0, 0, F{current_row}/E{current_row}), 2)"
        sheet[get_column_letter(9) + str(current_row)] = f"=TRUNC(H{current_row}*G{current_row}/30.48 + H{current_row}, 2)"

        current_row += 1

    workbook.save(filename)


def get_exercises_with_keywords(workouts: list, has: list, not_has: list, remove_no_weight=False) -> list[Exercise]:
    selected_exercises = []
    
    for w in workouts:
        for ex in w.exercises:
            if all(keyword in ex["name"].lower() for keyword in has) and not any(keyword in ex["name"].lower() for keyword in not_has):
                selected_exercises.append(Exercise.from_dict({ **ex, "workout_id": w.id, "date": w.date }))

    if remove_no_weight:
        selected_exercises = [ex for ex in selected_exercises if any(s["weight"] is not None and s["weight"] > 0 for s in ex.sets)]

    return Exercise.sort_by_date(selected_exercises)


def exercises_to_dataframe(exercises: list[Exercise]) -> pd.DataFrame:
    data = []
    for ex in exercises:
        totalReps = sum(int(s["reps"]) for s in ex.sets if s["reps"] is not None)
        totalWeight = sum(float(s["weight"]*s["reps"]) for s in ex.sets if s["weight"] is not None and s["reps"] is not None)

        avgWeightPerRep =  round(totalWeight / totalReps, 2) if totalReps else 0
        avgRepsPerSet = round(totalReps / len(ex.sets), 2) if ex.sets else 0

        data.append({
            "Workout ID": ex.workout_id,
            "Date": ex.date,
            "Exercise Name": ex.name,
            "# Sets": len(ex.sets),
            "Total Reps": totalReps,
            "Total Weight": totalWeight,
            "Average Reps/Set": avgRepsPerSet,
            "Average Weight/Rep": avgWeightPerRep,
            "Estimated 1RM": round((avgWeightPerRep * avgRepsPerSet) / 30.48 + avgWeightPerRep, 2) if totalReps else 0
        })
    
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    return df
