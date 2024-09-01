from strava import *
from datetime import datetime
import streamlit as st
import pandas as pd


client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]

if "code" not in st.query_params and "access_token" not in st.query_params:
    url = get_authentication_code(client_id, "https://strava-analytics.streamlit.app", True)

    st.title("Strava API Data")
    st.write("Click the Following Hyper Link To Login To Strava and Access Your Data")
    st.write(f"<a href=\"{url}\">Login To Strava</a>", unsafe_allow_html=True)


if "code" in st.query_params and "access_token" not in st.query_params:
    access_token = get_access_token(client_id, client_secret, st.query_params["code"])
    st.query_params["access_token"] = access_token
    st.query_params["code"] = "None"


if "access_token" in st.query_params:
    st.title("Strava API Data")

    today = datetime.now()
    start_date = st.date_input("Start Date", datetime(today.year, today.month-1 if today.month != 1 else 12, today.day))
    end_date = st.date_input("End Date", today)

    filter_string = st.text_input("Data Filter", placeholder="Ex. elapsed_time >= moving_time")

    start_datetime = datetime(start_date.year, start_date.month, start_date.day)
    end_datetime = datetime(end_date.year, end_date.month, end_date.day)

    activities = get_athlete_activities(st.query_params["access_token"], start_datetime, end_datetime, 100)

    cols = ["name", "distance", "moving_time", "elapsed_time", "type", "workout_type", "start_date", "athlete_count", "kudos_count", "average_speed", "max_speed", "pr_count", "total_elevation_gain", "average_cadence", "average_watts", "max_watts", "kilojoules"]
    df = dict_to_df(activities, cols)
    df = df.sort_values("start_date").reset_index()[[i for i in cols if i in df.columns]]

    # Alter Workout Type
    df.loc[df["workout_type"] == 0, "workout_type"] = "None"
    df.loc[df["workout_type"] == 1, "workout_type"] = "Race"
    df.loc[df["workout_type"] == 2, "workout_type"] = "Long Run"
    df.loc[df["workout_type"] == 3, "workout_type"] = "Workout"

    try:
        if filter_string != "": df = df.query(filter_string)
    except:
        st.error("Invalid Data Filter String")

    st.subheader("Activity Statistics")
    st.write(df.describe())

    st.subheader("Activity Preview")

    if st.button("Show All"):
        st.write(df)
    else:
        st.write(df.head(10))

    st.subheader("Data Visualization (Scatter Plot)")
    scatter_exclude = ["name", "id"]

    scatter_x = st.selectbox("X Axis", [i for i in df.columns if i not in scatter_exclude], 0)
    scatter_y = st.selectbox("Y Axis", [i for i in df.columns if i not in scatter_exclude], 1)

    enable_size = st.checkbox("Enable Size")

    if enable_size:
        scatter_size = st.selectbox("Size", [i for i in df.columns if i not in scatter_exclude], 2)

    enable_color = st.checkbox("Enable Color")

    if enable_color:
        scatter_color = st.selectbox("Color", [i for i in df.columns if i not in scatter_exclude], 4)


    st.scatter_chart(
        df, 
        x=scatter_x, 
        y=scatter_y, 
        x_label=scatter_x, 
        y_label=scatter_y, 
        size=scatter_size if enable_size else None, 
        color=scatter_color if enable_color else None
    )

    st.subheader("Sample API Response")
    st.write(activities[0])