# Import the dependencies.
from flask import Flask, jsonify, render_template, request
from sqlalchemy import create_engine, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import requests

#################################################
# Database Setup
#################################################

# Define the database URL
database_url = 'sqlite:///hawaii.sqlite'

# Create the engine
engine = create_engine(database_url)

# Reflect the tables into classes
Base = automap_base()

# Reflect the tables from the database
Base.prepare(engine, reflect=True)

# Save references to each table
Station = Base.classes.station
Measurement = Base.classes.measurement

# Create our session (link) from Python to the DB
Session = sessionmaker(bind=engine)
session = Session()

# the format of the date string
date_format = "%Y-%m-%d"

# fetching latest date from the the dataset
latest_date = session.query(func.max(Measurement.date)).scalar()

# getting the one year ago date
one_year_ago = datetime.strptime(latest_date, date_format) - timedelta(days=365)


#################################################
# Flask Setup
#################################################

# Create a Flask app
app = Flask(__name__)

#################################################
# Flask Routes
#################################################

@app.route("/")
def home():
    """Render the home page."""
    return render_template("index.html", latest_date=latest_date)

@app.route("/api/v1.0/precipitation")
def get_precipitation_analysis():
    """Get precipitation data for the last year."""

    # Perform a query to retrieve the data and precipitation scores
    results = session.query(Measurement.date, Measurement.prcp) \
                 .filter(Measurement.date >= one_year_ago) \
                 .all()
    
    # # Convert the results to a JSON list
    precipitation_data = [{'date': date, 'precipitation': prcp} for date, prcp in results]

    return jsonify(precipitation_data)

@app.route("/precipitation")
def precipitation_client():
    """Render the precipitation page with data fetched from the API."""

    # Send a GET request to the stations API endpoint
    response = requests.get("http://localhost:5000/api/v1.0/precipitation")
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        precipitation = response.json()
       
        # Render the HTML template with the stations data
        return render_template('precipitation.html', precipitation=precipitation)
    else:
        # If the request fails, return an error message
        return "Failed to fetch stations data"


@app.route("/api/v1.0/stations")
def get_stations():
    """Get information about weather stations."""

    # Query all stations
    stations = session.query(Station).all()
    
    # Convert the stations to a list of dictionaries
    station_list = []
    for station in stations:
        station_dict = {
            'id': station.id,
            'name': station.name,
            'latitude': station.latitude,
            'longitude': station.longitude,
            'elevation': station.elevation
        }
        station_list.append(station_dict)
    
    return jsonify(station_list)

# Define a route to fetch stations data and send it to the frontend
@app.route("/stations")
def render_stations():
    """Render the stations page with data fetched from the API."""

    # Send a GET request to the stations API endpoint
    response = requests.get("http://localhost:5000/api/v1.0/stations")
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        stations = response.json()
        
        # Render the HTML template with the stations data
        return render_template('stations.html', stations=stations)
    else:
        # If the request fails, return an error message
        return "Failed to fetch stations data"


@app.route("/api/v1.0/tob")
def get_temperature_observations():
    """Get temperature observations for the last year from the most active station."""
    
    # Query the most active station based on the number of temperature observations
    most_active_station = session.query(Measurement.station, func.count(Measurement.id)) \
                                   .filter(Measurement.date >= one_year_ago) \
                                  .group_by(Measurement.station) \
                                  .order_by(func.count(Measurement.id).desc()) \
                                  .first()[0]
    
    # Query the dates and temperature observations for the previous year from the most active station
    results = session.query(Measurement.station, Measurement.date, Measurement.tobs) \
                     .filter(Measurement.station == most_active_station) \
                     .all()
    
    
    # # Convert the results to a JSON list
    temperature_observations = [{'station': station, 'date': date, 'temperature': temperature} for station, date, temperature in results]
    
    return jsonify(temperature_observations)

# function for temperature observations
@app.route("/temperature-observations")
def render_temperature_observations():
    """Render the temperature observations page with data fetched from the API."""

    # taking temperature observations from the api and sending them at the frontend
    response = requests.get("http://localhost:5000/api/v1.0/tob")

    temperature_observations = response.json()
    return render_template('temperature_observations.html', temperature_observations=temperature_observations)

@app.route("/api/v1.0/<start>")
def data_from_start_date(start):
    """Get temperature statistics from the specified start date to the latest date."""

    # Query the minimum, maximum, and average temperatures for all dates starting from the specified start date
    result = session.query(func.min(Measurement.tobs).label('min_temp'),
                           func.max(Measurement.tobs).label('max_temp'),
                           func.avg(Measurement.tobs).label('avg_temp')) \
                   .filter(Measurement.date >= start) \
                   .first()

    # Create a dictionary to hold the results
    stats = {
        'start_date': start,
        'end_date': latest_date,
        'min_temp': result.min_temp,
        'max_temp': result.max_temp,
        'avg_temp': result.avg_temp
    }

    return jsonify(stats)

@app.route("/api/v1.0/<start>/<end>")
def data_from_date_range(start, end):
    """Get temperature statistics for a specified date range."""

    # Query the minimum, maximum, and average temperatures for all dates starting from the specified start date uptill the end date
    result = session.query(func.min(Measurement.tobs).label('min_temp'),
                           func.max(Measurement.tobs).label('max_temp'),
                           func.avg(Measurement.tobs).label('avg_temp')) \
                   .filter(Measurement.date >= start) \
                   .filter(Measurement.date <= end) \
                   .first()

    # Create a dictionary to hold the results
    stats = {
        'start_date': start,
        'end_date': end,
        'min_temp': result.min_temp,
        'max_temp': result.max_temp,
        'avg_temp': result.avg_temp
    }

    return jsonify(stats)

# This route is for sending minimum, maximum and average temperature at the frontend
@app.route("/temperature_info", methods=["POST"])
def temperature_information():
    """Render the temperature info page with data fetched from the API."""

    # If the form has an end date we call api/v1.0/start/end endpoint
    if request.form["end_date"]:
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        response = requests.get(f"http://localhost:5000/api/v1.0/{start_date}/{end_date}")
        stats = response.json()
        return render_template("temperature_info.html", stats=stats)
    
    # If the form does not have an end date then we ca;; api/v1.0/start endpoint    
    else:
        start_date = request.form["start_date"]
        response = requests.get(f"http://localhost:5000/api/v1.0/{start_date}")
        stats = response.json()
        return render_template("temperature_info.html", stats=stats)
    
if __name__ == '__main__':
    app.run(debug=True)