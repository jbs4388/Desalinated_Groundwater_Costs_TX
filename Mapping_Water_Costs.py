#%%
#Importing necessary libraries
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import streamlit as st
import folium
from streamlit_folium import st_folium
from branca.colormap import LinearColormap

#%%
#Reading datasets
BWRO_path = Path("Desal_Estimates/BWRO_desal_system_costs.csv")
EDR_path = Path("Desal_Estimates/EDR_desal_system_costs.csv")

BWRO_data = pd.read_csv(BWRO_path)
EDR_data = pd.read_csv(EDR_path)

county_map_path = Path("US_COUNTY_SHPFILE/US_county_cont.shp")
county_map = gpd.read_file(county_map_path)

#Creating just a map of Texas and setting crs
water_costs = county_map[county_map['STATE_NAME'] == 'Texas']
water_costs = water_costs.to_crs(epsg=4326)
water_costs = water_costs.sort_values(by="NAME", ascending=True)

#Global variables to decide on
analysis_period = 30 #Estimated lifetime of desal plant in years

#Creating output matrix
water_costs = water_costs.drop(columns=["STATE_NAME", "STATE_FIPS", "CNTY_FIPS", "FIPS", "SQMI", "Shape_Leng", "Shape_Area"])
cols_to_add = ["BWRO_SLIGHT_COST", "BWRO_MODERATE_COST", "BWRO_SALINE_COST", "EDR_SLIGHT_COST", "EDR_MODERATE_COST", "EDR_SALINE_COST"]
for col in cols_to_add:
    water_costs[col] = None

#%%
#Filling in the output matrix with water costs [$/m3]
for county in water_costs["NAME"]:
    if pd.notna(BWRO_data.loc[BWRO_data["COUNTY"] == county, "SLIGHTLY_SALINE_CAPEX"].values[0]):
        water_costs.loc[water_costs["NAME"] == county, "BWRO_SLIGHT_COST"] = ((BWRO_data.loc[BWRO_data["COUNTY"] == county, "SLIGHTLY_SALINE_CAPEX"].values[0] + 
            BWRO_data.loc[BWRO_data["COUNTY"] == county, "SLIGHTLY_SALINE_OPEX"].values[0] * analysis_period) / 
            (500000 * 365 * 0.0037854118 * analysis_period)
            )
        
        water_costs.loc[water_costs["NAME"] == county, "EDR_SLIGHT_COST"] = ((EDR_data.loc[EDR_data["COUNTY"] == county, "SLIGHTLY_SALINE_CAPEX"].values[0] + 
            EDR_data.loc[EDR_data["COUNTY"] == county, "SLIGHTLY_SALINE_OPEX"].values[0] * analysis_period) / 
            (500000 * 365 * 0.0037854118 * analysis_period)
            )
    
    if pd.notna(BWRO_data.loc[BWRO_data["COUNTY"] == county, "MODERATELY_SALINE_CAPEX"].values[0]):
        water_costs.loc[water_costs["NAME"] == county, "BWRO_MODERATE_COST"] = ((BWRO_data.loc[BWRO_data["COUNTY"] == county, "MODERATELY_SALINE_CAPEX"].values[0] + 
            BWRO_data.loc[BWRO_data["COUNTY"] == county, "MODERATELY_SALINE_OPEX"].values[0] * analysis_period) / 
            (500000 * 365 * 0.0037854118 * analysis_period)
            )
        
        water_costs.loc[water_costs["NAME"] == county, "EDR_MODERATE_COST"] = ((EDR_data.loc[EDR_data["COUNTY"] == county, "MODERATELY_SALINE_CAPEX"].values[0] + 
            EDR_data.loc[EDR_data["COUNTY"] == county, "MODERATELY_SALINE_OPEX"].values[0] * analysis_period) / 
            (500000 * 365  * 0.0037854118 * analysis_period)
            )
        
    if pd.notna(BWRO_data.loc[BWRO_data["COUNTY"] == county, "SALINE_CAPEX"].values[0]):
        water_costs.loc[water_costs["NAME"] == county, "BWRO_SALINE_COST"] = ((BWRO_data.loc[BWRO_data["COUNTY"] == county, "SALINE_CAPEX"].values[0] + 
            BWRO_data.loc[BWRO_data["COUNTY"] == county, "SALINE_OPEX"].values[0] * analysis_period) / 
            (500000 * 365  * 0.0037854118 * analysis_period)
            )
        
        water_costs.loc[water_costs["NAME"] == county, "EDR_SALINE_COST"] = ((EDR_data.loc[EDR_data["COUNTY"] == county, "SALINE_CAPEX"].values[0] + 
            EDR_data.loc[EDR_data["COUNTY"] == county, "SALINE_OPEX"].values[0] * analysis_period) / 
            (500000 * 365  * 0.0037854118 * analysis_period)
            )
# %%
"""Code below this point generated primarily with ChatGPT to visualize data above as a streamlit application"""
# --- Streamlit UI ---
st.title("Texas Desalination Cost Map")
st.markdown("Select technology and salinity level to visualize the lowest cost per county.")

tech_options = ["Both", "BWRO", "EDR"]
tech_choice = st.selectbox("Technology", tech_options)
salinity_options = ["All", "Slightly Saline", "Moderately Saline", "Saline"]
salinity_choice = st.selectbox("Salinity Level", salinity_options)

selected_columns = []
if tech_choice == "BWRO":
    selected_columns += ["BWRO_SLIGHT_COST", "BWRO_MODERATE_COST", "BWRO_SALINE_COST"]
elif tech_choice == "EDR":
    selected_columns += ["EDR_SLIGHT_COST", "EDR_MODERATE_COST", "EDR_SALINE_COST"]
else:
    selected_columns += cols_to_add

if salinity_choice == "Slightly Saline":
    selected_columns = [col for col in selected_columns if "SLIGHT" in col]
elif salinity_choice == "Moderately Saline":
    selected_columns = [col for col in selected_columns if "MODERATE" in col]
elif salinity_choice == "Saline":
    selected_columns = [col for col in selected_columns if "SALINE_COST" in col and "MODERATE" not in col and "SLIGHT" not in col]

water_costs["MIN_COST"] = water_costs[selected_columns].min(axis=1, skipna=True)

# --- Folium Map ---
st.markdown("#### Cheapest Desalination Cost per County (USD/m³)")

# Center of Texas
m = folium.Map(location=[31.0, -99.5], zoom_start=6, tiles='cartodbpositron')

# Color scale
min_cost = water_costs["MIN_COST"].min()
max_cost = water_costs["MIN_COST"].max()
# Avoid division by zero
if min_cost == max_cost:
    max_cost += 1

# Function to get color
colormap = LinearColormap(
    colors=['green', 'yellow', 'red'],
    vmin=min_cost, vmax=max_cost
)
colormap = colormap.to_step(n=10)

def style_function(feature):
    county_name = feature['properties']['NAME']
    value = water_costs.loc[water_costs["NAME"] == county_name, "MIN_COST"].values
    # Check for missing or invalid values
    if len(value) > 0 and value[0] is not None and not np.isnan(value[0]):
        return {
            'fillColor': colormap(value[0]),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    else:
        return {
            'fillColor': 'lightgrey',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.3
        }

def highlight_function(feature):
    return {
        'fillColor': '#ffff00',
        'color': 'black',
        'weight': 2,
        'fillOpacity': 0.9
    }

# Add counties to map
folium.GeoJson(
    water_costs,
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.features.GeoJsonTooltip(
        fields=['NAME', 'MIN_COST'],
        aliases=['County:', 'Water Cost (USD/m³):'],
        localize=True,
        labels=True,
        sticky=True
    )
).add_to(m)

# Add legend
colormap.caption = 'Lowest Desalination Cost (USD/m³)'
colormap.add_to(m)

# Display map in Streamlit
st_data = st_folium(m, width=700, height=700)

# Optional: Show data table
if st.checkbox("Show data table"):
    st.dataframe(
        water_costs[["NAME", "MIN_COST"] + selected_columns].sort_values("MIN_COST")
    )