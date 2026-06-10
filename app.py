from flask import Flask, jsonify
import pandas as pd
import sqlite3

app = Flask(__name__)

@app.route("/pollutants")
def pollutants():

    conn = sqlite3.connect("widetable.db")

    df = pd.read_sql(
        "SELECT * FROM pollutant_wide LIMIT 100",
        conn
    )

    return jsonify(
        df.to_dict(orient="records")
    )

app.run(debug=False)