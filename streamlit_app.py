import streamlit as st
import pandas as pd
import sqlite3

conn = sqlite3.connect(r"C:\Users\Quantam Waffle\OneDrive\Desktop\Data engineering and management\Data engineering project\widetable.db")



df = pd.read_sql(
    "SELECT * FROM pollutant_wide",
    conn
)

if st.button("Prepare Data for Downstream Applications"):

    df.to_csv(
        "analytics_input.csv",
        index=False
    )

    st.success(
        "analytics_input.csv has been created."
    )

st.title("Air Quality Monitoring Dashboard")

st.write("Cleaned Wide-Table Dataset")

st.dataframe(df.head(100))


st.subheader("Dataset Shape")

st.write(
    f"Rows: {df.shape[0]}"
)

st.write(
    f"Columns: {df.shape[1]}"
)

pollutants = [
    "benzene",
    "co",
    "nh3",
    "no",
    "no2",
    "ozone",
    "pm10",
    "pm25",
    "so2",
    "toluene"
]

selected = st.selectbox(
    "Select Pollutant",
    pollutants
)

st.subheader(
    f"{selected} Statistics"
)

st.write(
    df[selected].describe()
)

st.line_chart(df[selected])
