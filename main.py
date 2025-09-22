from strava import get_access_token, get_authentication_code
from strava_workouts import *
from google import genai
from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

'''
Run Command: python -m streamlit run main.py --server.port 8000

Next Steps:
----------------------------------------
1. Fix parsing errors for certain workouts
    - [14159016908, 14034334353, 13081642185]
    - [10080415283, 10069170540, 9857038708, 9850365640]
2. Prototype final app features using a Streamlit app
    - Handle rate limiting errors when retrieving workout data
    - Automatically load new workouts since last fetch
    - Create a page to view all workouts and filter by keywords (like strava)
    - Create a page to view individual workouts
    - Create a page to create new workouts 
    

3. Create full React.js web app or React Native mobile app
----------------------------------------
'''

# Important Exercise Groups to Track:
# -------------------------------------
# Bench Press (*)
# Shoulder Press
# Lateral Raise
# Row
# Upright Row
# Curl (bicep, hammer, preacher, etc.)
# Tricep Extension

# Squat (*)
# Split Squat
# Hex Bar Deadlift
# Deadlift
# Romanian Deadlift (RDL) + Stiff-Legged Deadlift (SLDL)

# Push-ups
# Dips
# Pull-ups
# Chin-ups
# Hollow-Body Reps (possibly also "sit-ups" or "leg raises")
# -------------------------------------


def get_athlete_activities_streamlit(access_token: str, start_time, end_time, max_count=30):
    before = end_time
    after = start_time

    final_data = []
    more_data = True
    page = 1

    my_bar = st.progress(0, text="Fetching Activities...")

    while more_data:
        activities_response = requests.get("https://www.strava.com/api/v3/athlete/activities", 
            headers={
                "Authorization": f"Bearer {access_token}" 
            }, 
            params= {
                "before": int(before.timestamp()), 
                "after": int(after.timestamp()),
                "per_page": max_count,
                "page": page
            }
        )

        if activities_response.status_code != 200:
            print("ERROR from getAthleteActivities")
            print(activities_response.json())
            return
        

        if len(activities_response.json()) < max_count:
            more_data = False
            
        for i in activities_response.json():
            final_data.append(i)
        
        print(str(len(activities_response.json())) + " Entries Recieved From Page " + str(page))
        page += 1
        my_bar.progress(page / 100, text=f"Fetched {len(final_data)} Activities...")
    
    return final_data


def fetch_workout_ids_streamlit(access_token, filename, start_date, end_date):
    st.write("Access Token:", access_token)
    activities = get_athlete_activities_streamlit(access_token, start_date, end_date, max_count=100)

    if activities is None:
        st.error("Error fetching activities from Strava.")
        return
    
    ids = [activity['id'] for activity in activities if activity["type"] == "Workout" or activity["type"] == "WeightTraining"]
    st.success("Fetched " + str(len(ids)) + " Workout IDs")
    
    with open(filename, "w") as f:
        json.dump(ids, f, indent=4)
    
    st.success(f"Saved {len(ids)} workout IDs to {filename}")
    
    return ids


def fetch_workouts_streamlit(access_token, filename, id_list, start_index=0):
    with open(id_list, "r") as f:
        ids = json.load(f)[start_index:]
    
    st.write("Found " + str(len(ids)) + " Workouts to Retrieve")

    all_workouts_json = []
    invalid_workouts = []
    count = 0
    my_bar = st.progress(0, text="Fetching Workouts...")

    for activity_id in ids:
        # Change Workout 14159016908, 14034334353, 13081642185
        w = WorkoutSession(activity_id, auto_retrieve_data=False)

        try:
            w.retrieve_data(access_token)
        except Exception as e:
            st.error("Error retrieving workout " + str(activity_id) + ": " + str(e))

            if str(e) == "429":
                st.error("Rate limit exceeded. Wait 15 minutes.")
            elif str(e) == "401":
                st.error("Unauthorized access. Refresh access token.")

            break
        
        try:
            w.parse_description()
        except Exception as e:
            st.warning(f"Error parsing workout {w.id}")
            invalid_workouts.append(w.id)
            continue

        print("Retrieved workout:", w.id)
        all_workouts_json.append(w.as_dict())
        count += 1
        my_bar.progress(count / len(ids), text=f"Fetched {count} of {len(ids)} Workouts...")

    if filename is not None:
        if os.path.exists(filename):
            all_workout_ids = [w['id'] for w in all_workouts_json]

            with open(filename, "r") as f:
                existing_data = json.load(f)
            
            for workout in existing_data:
                if workout['id'] not in all_workout_ids:
                    all_workouts_json.append(workout)

        with open(filename, "w") as f:
            json.dump(all_workouts_json, f, indent=4)

        st.success(f"Saved {len(all_workouts_json)} workouts to {filename}")
    
    if len(invalid_workouts) > 0:
        st.warning(f"Failed to parse {len(invalid_workouts)} workouts: {invalid_workouts}")
        st.session_state.invalid_workouts = invalid_workouts



def main():
    st.title("Strava Workout Analyzer")

    # ================================ STRAVA AUTHENTICATION ================================
    if "code" in st.query_params:
        st.session_state.code = st.query_params.code
        st.session_state.access_token = get_access_token(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, st.session_state.code)

        st.query_params.clear()
        st.query_params["access_token"] = st.session_state.access_token
        st.info("Access Token: " + str(st.session_state.access_token))
    else:
        st.info("Press the button below to authenticate with Strava.")
        url = get_authentication_code(STRAVA_CLIENT_ID, "http://localhost:8000", streamlit=True)
        st.write(f'''
            <a target="_self" href="{url}">
                <button>
                    Authenticate with Strava
                </button>
            </a>
            ''',
            unsafe_allow_html=True
        )



    if not st.query_params.get("access_token"):
        st.warning("Please authenticate with Strava to continue.")
        return

    access_token = st.query_params.get("access_token")


    # ================================ Fetch Workout IDs ================================
    st.header("Fetch Workout IDs from Strava")
    start_date = datetime.strptime("2023-06-27T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_date = datetime.strptime("2025-09-17T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")

    st.date_input("Start Date", value=start_date, key="start_date")
    st.date_input("End Date", value=end_date, key="end_date")
    st.text_input("Save File", value="workout_ids.json", key="workout_id_file")

    start_date = datetime(st.session_state.start_date.year, st.session_state.start_date.month, st.session_state.start_date.day)
    end_date = datetime(st.session_state.end_date.year, st.session_state.end_date.month, st.session_state.end_date.day)

    if st.button("Fetch Workout IDs"):
        fetch_workout_ids_streamlit(access_token, st.session_state.workout_id_file, start_date, end_date)


    # ================================ Fetch Workout Data ================================
    st.header("Fetch Workout Data from Strava")
    st.text_input("ID List File", value="workout_ids.json", key="id_list_file")
    st.text_input("Save File", value="workouts2.json", key="save_file")
    st.number_input("Start Index", min_value=0, value=0, step=1, key="start_index")
    if st.button("Fetch Workout Data"):
        fetch_workouts_streamlit(access_token, st.session_state.save_file, st.session_state.id_list_file, start_index=st.session_state.start_index)


    # ================================ Load Workout Data ================================
    st.header("Load Workouts from File")
    st.text_input("Workout File", value="workouts2.json", key="workout_file")
    if st.button("Load Workouts"):
        with st.spinner("Loading Workouts..."):
            st.session_state.workouts = get_workouts_from_json(st.session_state.workout_file)
            st.success(f"Loaded {len(st.session_state.workouts)} workouts from {st.session_state.workout_file}")

    if "workouts" not in st.session_state:
        st.warning("Please load workouts from file above.")
        return


    # ================================ Workout Data Analysis ================================
    st.header("Filter through Exercises")
    st.text_input("Included", key="included")
    st.text_input("Excluded", key="excluded")
    st.checkbox("Remove Exercises with No Weight Data", value=False, key="remove_no_weight")

    filtered_exercises = get_exercises_with_keywords(
        st.session_state.workouts,
        [kw.strip().lower() for kw in st.session_state.included.split(",") if kw.strip() != ""],
        [kw.strip().lower() for kw in st.session_state.excluded.split(",") if kw.strip() != ""],
        remove_no_weight=st.session_state.remove_no_weight
    )
    exercise_df = exercises_to_dataframe(filtered_exercises)

    if len(filtered_exercises) > 0:
        st.dataframe(exercise_df)
    else:
        st.write("No exercises found matching those keywords.")

    st.radio("Set Y-Axis", options=["Estimated 1RM", "Total Reps"], index=0, key="chart_type")
    st.line_chart(exercise_df, x='Date', y=st.session_state.chart_type, use_container_width=True)



    if "invalid_workouts" in st.session_state:
        st.warning(f"Failed to parse {len(st.session_state.invalid_workouts)} workouts: {st.session_state.invalid_workouts}")


    # ================================ Individual Workout Lookup ================================
    st.header("Search for Workout by ID")
    st.text_input("Workout ID", key="workout_id")

    if "workout_id" not in st.session_state or st.session_state.workout_id == "":
        st.write("Please enter a workout ID above.")
    else:
        selected_workout = WorkoutSession(int(st.session_state.workout_id), auto_retrieve_data=False)
        try:
            with st.spinner("Fetching Workout Data..."):
                selected_workout.retrieve_data(access_token)
            st.write(selected_workout)
        except Exception as e:
            st.error(f"Workout with ID {st.session_state.workout_id} could not be retrieved: {e}")


if __name__ == "__main__":
    main()
