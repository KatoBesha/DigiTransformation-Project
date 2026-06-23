import os
from sqlalchemy import create_engine, text
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

# ─── Database connection ───────────────────────────────────────────────────
# On Railway, DATABASE_URL is set as an environment variable
# Locally, it falls back to your local PostgreSQL
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:admin123@localhost:5434/DigitalTransformation"
)

# Railway / Supabase connection strings start with "postgres://" — fix for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)

# ─── Lazy query functions (called per callback, not at startup) ────────────
def get_dropdown_options():
    """Get just the unique values needed to populate dropdowns."""
    with engine.connect() as conn:
        pollutants = pd.read_sql(text("SELECT DISTINCT pollutant FROM pollutant_readings ORDER BY pollutant"), conn)
        stations   = pd.read_sql(text("SELECT DISTINCT station_id FROM stations ORDER BY station_id"), conn)
        years      = pd.read_sql(text("SELECT DISTINCT EXTRACT(YEAR FROM timestamp)::int AS year FROM pollutant_readings ORDER BY year"), conn)
    return pollutants['pollutant'].tolist(), stations['station_id'].tolist(), years['year'].tolist()

def query_pollutants(pollutant, year, station=None):
    params = {"pollutant": pollutant, "year": year}
    station_filter = "AND p.station_id = :station" if station else ""
    if station:
        params["station"] = station
    with engine.connect() as conn:
        df = pd.read_sql(text(f"""
            SELECT p.station_id, p.timestamp, p.pollutant, p.value, s.city, s.state
            FROM pollutant_readings p
            JOIN stations s ON p.station_id = s.station_id
            WHERE LOWER(p.pollutant) = LOWER(:pollutant)
            AND EXTRACT(YEAR FROM p.timestamp) = :year
            {station_filter}
        """), conn, params=params)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df['month'] = df['timestamp'].dt.month
    return df

def query_weather(station=None):
    params = {}
    station_filter = "WHERE r.station_id = :station" if station else ""
    if station:
        params["station"] = station
    with engine.connect() as conn:
        df = pd.read_sql(text(f"""
            SELECT r.station_id, r.timestamp, r.at_c
            FROM weather_readings r
            {station_filter}
        """), conn, params=params)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df

# Load only dropdown options at startup (tiny query)
pollutant_options, station_options, year_options = get_dropdown_options()

# ─── Dash app ──────────────────────────────────────────────────────────────
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # Required for gunicorn

app.layout = dbc.Container([

    # Header
    dbc.Row([
        dbc.Col(html.H1("DigiTransformation — Air Quality Dashboard",
            className="text-center my-4 text-white",
            style={'backgroundColor': '#2c3e50', 'padding': '20px',
                   'borderRadius': '10px'}))
    ]),

    # Filters
    dbc.Row([
        dbc.Col([
            html.Label("Pollutant:"),
            dcc.Dropdown(
                id='pollutant-dropdown',
                options=[{'label': p.upper(), 'value': p}
                         for p in pollutant_options],
                value=pollutant_options[0] if pollutant_options else 'pm25',
                clearable=False
            )
        ], width=4),
        dbc.Col([
            html.Label("Station:"),
            dcc.Dropdown(
                id='station-dropdown',
                options=[{'label': s, 'value': s}
                         for s in station_options],
                value=None,
                placeholder="All stations",
                clearable=True
            )
        ], width=4),
        dbc.Col([
            html.Label("Year:"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(y), 'value': y}
                         for y in year_options],
                value=year_options[-1] if year_options else 2024,
                clearable=False
            )
        ], width=4),
    ], className="my-3"),

    # Summary cards
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Stations", className="card-title"),
            html.H3(id='total-stations', className="text-primary")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Avg Value", className="card-title"),
            html.H3(id='avg-value', className="text-success")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Value", className="card-title"),
            html.H3(id='max-value', className="text-danger")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Readings", className="card-title"),
            html.H3(id='total-readings', className="text-info")
        ])), width=3),
    ], className="my-3"),

    # Charts row 1
    dbc.Row([
        dbc.Col([
            html.H5("Monthly Trend"),
            dcc.Graph(id='trend-chart')
        ], width=8),
        dbc.Col([
            html.H5("Avg by Station"),
            dcc.Graph(id='station-chart')
        ], width=4),
    ], className="my-3"),

    # Charts row 2
    dbc.Row([
        dbc.Col([
            html.H5("Temperature vs Pollutant"),
            dcc.Graph(id='scatter-chart')
        ], width=6),
        dbc.Col([
            html.H5("Pollutant Distribution"),
            dcc.Graph(id='box-chart')
        ], width=6),
    ], className="my-3"),

    # Data table
    dbc.Row([
        dbc.Col([
            html.H5("Raw Data Table"),
            dash_table.DataTable(
                id='data-table',
                page_size=15,
                sort_action='native',
                filter_action='native',
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={
                    'backgroundColor': '#2c3e50',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[{
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }]
            )
        ])
    ], className="my-3")

], fluid=True)


@app.callback(
    [Output('total-stations', 'children'),
     Output('avg-value', 'children'),
     Output('max-value', 'children'),
     Output('total-readings', 'children'),
     Output('trend-chart', 'figure'),
     Output('station-chart', 'figure'),
     Output('scatter-chart', 'figure'),
     Output('box-chart', 'figure'),
     Output('data-table', 'data'),
     Output('data-table', 'columns')],
    [Input('pollutant-dropdown', 'value'),
     Input('station-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_dashboard(pollutant, station, year):

    # Query only what's needed for this filter combination
    filtered        = query_pollutants(pollutant, year, station)
    weather_filtered = query_weather(station)

    # Summary cards
    total_stations = str(filtered['station_id'].nunique())
    avg_val        = f"{filtered['value'].mean():.2f}"
    max_val        = f"{filtered['value'].max():.2f}"
    total_readings = f"{len(filtered):,}"

    # Monthly trend
    monthly = filtered.groupby('month')['value'].mean().reset_index()
    monthly['month'] = monthly['month'].astype(int)
    trend_fig = px.line(
        monthly, x='month', y='value',
        title=f"Monthly Avg {pollutant.upper()} — {year}",
        markers=True,
        color_discrete_sequence=['#3498db']
    )

    # Station bar chart
    station_avg = filtered.groupby('station_id')['value'].mean().reset_index()
    station_fig = px.bar(
        station_avg, x='station_id', y='value',
        title=f"Avg {pollutant.upper()} by Station",
        color_discrete_sequence=['#27ae60']
    )

    # Scatter — temperature vs pollutant
    merged = filtered.merge(
        weather_filtered[['station_id', 'timestamp', 'at_c']],
        on=['station_id', 'timestamp'],
        how='inner'
    ).dropna(subset=['at_c'])

    scatter_fig = px.scatter(
        merged.sample(min(1000, len(merged))),
        x='at_c', y='value',
        color='station_id',
        title=f"Temperature vs {pollutant.upper()}",
        labels={'at_c': 'Temperature (°C)', 'value': pollutant.upper()}
    )

    # Box plot
    box_fig = px.box(
        filtered, x='station_id', y='value',
        title=f"{pollutant.upper()} Distribution by Station",
        color_discrete_sequence=['#e74c3c']
    )

    # Data table
    table_data = filtered[['station_id', 'city', 'timestamp',
                            'pollutant', 'value']]\
        .head(200).to_dict('records')
    table_cols = [{'name': c, 'id': c} for c in
                  ['station_id', 'city', 'timestamp', 'pollutant', 'value']]

    return (total_stations, avg_val, max_val, total_readings,
            trend_fig, station_fig, scatter_fig, box_fig,
            table_data, table_cols)


if __name__ == '__main__':
    app.run(debug=False)