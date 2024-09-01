from strava import *
from datetime import datetime
import streamlit as st
import pandas as pd


client_id = 133058
client_secret = "b14502a349e7fbcbfd435c975e6fa53102859201"

if "code" not in st.query_params and "access_token" not in st.query_params:
    get_authentication_code(client_id, "https://k9mwtd3ry7jej6abh9c8ho.streamlit.app/", True)


if "code" in st.query_params and "access_token" not in st.query_params:
    access_token = get_access_token(client_id, client_secret, st.query_params["code"])
    #st.session_state["access_token"] = access_token
    st.query_params["access_token"] = access_token
    st.query_params["code"] = "False"


if "access_token" in st.query_params:
    st.title("Strava API Data")

    today = datetime.now()
    start_date = st.date_input("Start Date", datetime(today.year, today.month-1 if today.month != 1 else 12, today.day))
    end_date = st.date_input("End Date", today)

    start_datetime = datetime(start_date.year, start_date.month, start_date.day)
    end_datetime = datetime(end_date.year, end_date.month, end_date.day)

    activities = get_athlete_activities(st.query_params["access_token"], start_datetime, end_datetime, 100)

    cols = ["name", "distance", "moving_time", "elapsed_time", "type", "id", "start_date", "athlete_count", "kudos_count", "average_speed", "max_speed", "pr_count", "total_elevation_gain", "average_cadence", "average_watts", "max_watts", "kilojoules"]
    df = dict_to_df(activities, cols)

    st.subheader("Activity Statistics")
    st.write(df.describe())

    st.subheader("Activity Preview")
    st.write(df.head(10))

    st.subheader("Data Visualization (Scatter Plot)")
    scatter_exclude = ["name", "id"]

    scatter_x = st.selectbox("X Axis", [i for i in df.columns if i not in scatter_exclude], 0)
    scatter_y = st.selectbox("Y Axis", [i for i in df.columns if i not in scatter_exclude], 1)

    st.scatter_chart(df, x=scatter_x, y=scatter_y, x_label=scatter_x, y_label=scatter_y)

    st.subheader("Sample API Response")
    st.write(activities[0])