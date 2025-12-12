#Importing needed libraries
import ast
import sys
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
import requests
import json
import warnings
import time

#Hiding FutureWarnings because they keep popping up when read_json is used and UserWarning when CRS may not match (it does!)
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action = 'ignore', category=UserWarning)

#Grabbing county data, then downselecting to just Texas counties
counties_path = Path("US_COUNTY_SHPFILE/US_county_cont.shp")
us_counties = gpd.read_file(counties_path)

texas_counties = us_counties[us_counties["STATE_NAME"] == "Texas"]
texas_counties = texas_counties.to_crs(epsg=4326)

#Calculating a centroid for each county to pull solar capacity factor data from
texas_centroids = gpd.GeoDataFrame(geometry=texas_counties.centroid)
texas_centroids["COUNTY_NAME"] = texas_counties["NAME"]

#Separating latitude and longitude into their own columns
texas_centroids['longitude'] = texas_centroids.geometry.x
texas_centroids['latitude'] = texas_centroids.geometry.y
texas_centroids = texas_centroids.sort_values("COUNTY_NAME", ascending=True)
texas_centroids = texas_centroids.reset_index(drop=True)

#Creating output geodataframe
texas_pv_cf = gpd.GeoDataFrame(geometry=texas_counties.geometry)
texas_pv_cf["COUNTY_NAME"] = texas_counties["NAME"]
texas_pv_cf = texas_pv_cf.sort_values("COUNTY_NAME", ascending=True)
texas_pv_cf = texas_pv_cf.reset_index(drop=True)
month_cols = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
for col in month_cols:
    texas_pv_cf[col] = None

#Establishing API key and requests
token = "null" #Add your API key here!
url = 'https://www.renewables.ninja/api/data/pv'
s = requests.session()
s.headers = {'Authorization': 'Token ' + token}

#Setting up loop timing control variable
timeout = 0

#Passing each centroid to Renewables Ninja and storing the resulting capacity factor
for i in range(len(texas_centroids)):
    lon = texas_centroids.loc[i,'longitude']
    lat = texas_centroids.loc[i, 'latitude']
    args = {
        'lat': lat,
        'lon': lon,
        'date_from': '2022-01-01',
        'date_to': '2022-12-31',
        'dataset': 'merra2',
        'capacity': 1.0,
        'system_loss': 0.1,
        'tracking': 1,
        'tilt': round(lat, 0),
        'azim': 180,
        'mean': 'month',
        'format': 'json'

    }

    #Getting the API response
    response = s.get(url, params=args)

    #Parsing the returned JSON
    parsed_response = json.loads(response.text)
    response_df = pd.read_json(json.dumps(parsed_response['data']), orient='index')

    #Inserting capacity factor values into final dataframe
    texas_pv_cf.loc[i, month_cols] = response_df.T.values.round(3)

    #Calcuting capacity factor and adding it to our results array
    print(response_df)

    if timeout == 49:
        timeout = 0
        time.sleep(3600)
    else:
        timeout = timeout + 1

texas_pv_cf.to_csv("texas_pv_cf.csv")
