import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import folium
import pandas as pd
import urllib3
from zipfile import ZipFile
import requests #this is what we need for calls to OTP server!!
import osmnx as ox
import geopy.distance
import networkx as nx
from selenium import webdriver
from matplotlib import colormaps
from matplotlib.colors import ListedColormap
import time
import os
import json

"""
this file is in essence very similar to what yubo did, i will just exclude the stuff that i find useless.
it will be easier for me to wrap my head around it.
"""

def calculate_straight_line_distance(point1, point2):
    """Calculate the straight line distance between two points in kilometers."""
    distance = geopy.distance.distance(point1, point2).m
    return distance

def otp_calculate_route_time(point1, point2):
    """fetch a travel time by a call to the OTP server"""
    otp_base_url = 'http://localhost:8080'
    endpoint = '/otp/routers/plan'


    params = {
    'fromPlace': f'{point1[0]},{point1[1]}',
    'toPlace': f'{point2[0]},{point2[1]}',
    'time': '10:00am',
    'date': '06-10-2024',
    'mode' : 'TRANSIT,WALK',
    'maxWalkDistance': '1000'
    }
    print(params)

    # Make a GET request to the OTP server
    response = requests.get(f'{otp_base_url}{endpoint}', params=params)

    # Check if the request was successful
    if response.status_code == 200:
    # Parse the JSON response
        trip_data = response.json()
        print(trip_data)
        # Dump the trip data to a file called res.json
        #with open('res.json', 'w') as f:
        #    json.dump(trip_data, f, indent=4, sort_keys=True)
       #return (trip_data["transitServiceEnds"] - trip_data["transitServiceStarts"])/ 60
    else:
        print(f'Error: {response.status_code} - {response.text}')

def otp_calculate_route_time_new(point1, point2, date=None, time=None):
    url = 'http://localhost:8080/otp/gtfs/v1'
    
    # Define the GraphQL query
    query = """
    query plan($from: InputCoordinates!, $to: InputCoordinates!, $date: String!, $time: String!) {
    plan(
        from: $from,
        to: $to,
        date: $date,
        time: $time,
        transportModes: [
        { mode: WALK },
        { mode: TRANSIT }
        ],
        numItineraries: 1
    ) {
        itineraries {
        startTime
        endTime
        legs {
            mode
            startTime
            endTime
            from {
            name
            lat
            lon
            departureTime
            arrivalTime
            }
            to {
            name
            lat
            lon
            departureTime
            arrivalTime
            }
            route {
            gtfsId
            longName
            shortName
            }
            legGeometry {
            points
            }
        }
        }
    }
    }
    """

    #fill in missing data
    if date == None:
        date = "2024-10-08"
    if time == None:
        time = "11:59"
    
    # Define the variables for the query
    variables = {
    "from": {"lat": point1[0], "lon": point1[1]},  # Replace with your origin coordinates
    "to": {"lat": point2[0], "lon": point2[1]},    # Replace with your destination coordinates
    "date": date,                           # Replace with the desired date (YYYY-MM-DD)
    "time": time                                 # Replace with the desired time (HH:MM)
    }

    # Define the headers for the request
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Make the POST request to the GraphQL endpoint
    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)


    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        #just see if this is a tiny bit faster please
        
        # Check if itineraries are present in the response
        itineraries = data.get('data', {}).get('plan', {}).get('itineraries', [])
        if not itineraries:
            print("No itineraries found for the given locations and time.")
            return None
        travel_time_in_minutes = min([int(itinerary['endTime']) - int(itinerary['startTime']) for itinerary in itineraries]) / 1000 / 60
        return travel_time_in_minutes
    else:
        print(f"Query failed with status code {response.status_code}: {response.text}")
        return None

def otp_calculate_time_matrix(gdf,
                              idCol = "IdINSPIRE",
                              geometryCol = "geometry",
                              threshold = 30,
                              output_file_path  = "time_by_id.csv",
                              column_num = 'All',
                              date=None,
                              triptime=None):
    """
    Calculate the time matrix for a given geodataframe.
    """

    if column_num != 'All':
        gdf = gdf.head(column_num)
    if 'level_0' in gdf.columns:
        gdf = gdf.drop(columns=['level_0'])
    gdf.reset_index(inplace=True)
    time_by_id = pd.DataFrame(index=gdf[idCol])

    for idx, row in gdf.iterrows():
        #print(f"Calculating weights for {idx + 1} of {len(gdf)}")
        for idx1, row1 in gdf.loc[idx:].iterrows():
            print(f"{idx1 + 1} out of {len(gdf.loc[idx:])}")
            #print("itering!")
            if idx != idx1:
                #print(f"{row[geometryCol].y}, {row[geometryCol].x} are start coords and {row1[geometryCol].y}, {row1[geometryCol].x} are end coords") 
                tm = otp_calculate_route_time_new((row[geometryCol].y, row[geometryCol].x),
                                                (row1[geometryCol].y, row1[geometryCol].x),
                                                date,
                                                triptime)
            else:
                tm = 0.0
            
            time_by_id.at[gdf.at[idx, idCol], gdf.at[idx1, idCol]] = tm
            time_by_id.at[gdf.at[idx1, idCol], gdf.at[idx, idCol]] = tm
        



            
    gdf.set_index(idCol, inplace=True)

    return time_by_id
        

start = time.time()
otp_calculate_route_time_new((48.86107, 2.364267), (48.84900, 2.330620))
end = time.time()
print(f"Time taken: {end - start}") #this takes way longer than it should #like 0.2 seconds
