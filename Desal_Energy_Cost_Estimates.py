#%%
#Importing necessary libraries
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

#%%
#Establishing global variables for cost and solar price
solar_cost_cap = 1200 # $/kW installed capacity, per NREL with one axis tracking
batt_cost_cap = 1711 # $/kW installed capacity, 4 hour battery, per NREL
batt_maint_cap = 38.77 # $/kW installed capacity, each year, per NREL
slightly_saline_sec = 0.15 # kWh/m3 electricity demand for desalination of 3000 mg/L water
moderately_saline_sec = 0.6 # kWh/m3 electricity demand for desalination of 5000 mg/L water
saline_sec = 2.99 # kWh/m3 electricity demand for desalination of 10000 mg/L water
desal_capex_cost = 1820.75 # Use 1318.38 for BWRO # USD/m3/day, 2025 dollars
desal_opex_cost = 0.5184 # USD/m3, 2025 dollars, without energy consumption (similar between EDR and BWRO)

#Setting number of acres purchased and acres irrigated at any given time
acres = 15 #SET TO 15 FOR JUST THE LAND FOR PLANT AND SOLAR, USED IN MY RESEARCH FOR THE AFFORESTATION LAND TOO

#Loading the shapefile for the counties of the US
us_county_path = Path("US_COUNTY_SHPFILE/US_county_cont.shp")
us_counties = gpd.read_file(us_county_path)

#Filtering down to texas and setting crs
texas_counties = us_counties[us_counties['STATE_NAME'] == 'Texas']
texas_counties = texas_counties.to_crs(epsg=4326)

#Loading the CSV file with categories of salinity by county
salinity_path = Path("Desal_Estimates/TDS_BY_COUNTY.csv")
salinity_data = pd.read_csv(salinity_path)

#Loading monthly production ratios (kWh per kW of installed capacity)
pv_production_path = Path("Desal_Estimates/texas_tilt_pv_cf.csv")
pv_production = pd.read_csv(pv_production_path)

#Loading land costs per acre by county
county_land_path = Path("Desal_Estimates/county_land_costs.csv")
county_land_costs = pd.read_csv(county_land_path)

#Creating output and control variables
county_list_path = Path("county_list.csv")
county_data = pd.read_csv(county_list_path)
county_list = county_data["COUNTY"].tolist()

month_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
days_dict = {'Jan':31, 'Feb':28, 'Mar':31, 'Apr':30, 'May':31, 'Jun':30, 'Jul':31, 'Aug':31, 'Sep':30, 'Oct':31, 'Nov':30, 'Dec':31}

desal_system_costs = pd.DataFrame(county_list)
desal_system_costs.columns = ['COUNTY']
new_cols = ["DESAL_CAPACITY", "SLIGHTLY_SALINE_ENERGY_CAPACITY", "MODERATELY_SALINE_ENERGY_CAPACITY"
            , "SALINE_ENERGY_CAPACITY", "SLIGHTLY_SALINE_CAPEX", "SLIGHTLY_SALINE_OPEX", "MODERATELY_SALINE_CAPEX"
            , "MODERATELY_SALINE_OPEX", "SALINE_CAPEX", "SALINE_OPEX"]

for col in new_cols:
    desal_system_costs[col] = None

#%%
#Determining maximum desal capacity and maximum energy production capacity needed for each county and salinity level
for county in county_list:
    desal_cap = np.empty(0) #Empty array to determine maximum desalination capacity required by county
    energy_cap = np.empty(0) #Empty array to determine maximum energy production capacity required by county

    for month in month_list:
        desal_cap = 500000 * 0.0037854118
        energy_cap = np.concatenate((energy_cap, desal_cap * slightly_saline_sec / (pv_production.loc[pv_production['COUNTY_NAME'] == county, month].to_numpy() * 24)))
    
    #Filling in maximum desalination capacity column
    desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "DESAL_CAPACITY"] = np.max(desal_cap)
    
    #Filling in energy requirements IF the county has access to each salinity tier
    if salinity_data.loc[salinity_data['COUNTY NAME'] == county, "CONTAINS_SLIGHTLY_SALINE"].any() == True:
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SLIGHTLY_SALINE_ENERGY_CAPACITY"] = np.max(energy_cap)
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SLIGHTLY_SALINE_CAPEX"] = float(np.max(desal_cap)*desal_capex_cost + acres * county_land_costs.loc[county_land_costs['COUNTY'] == county, "PRICE_PER_ACRE"] + np.max(energy_cap)*(solar_cost_cap + batt_cost_cap))
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SLIGHTLY_SALINE_OPEX"] = float(np.max(desal_cap)*desal_opex_cost * 365 + np.max(energy_cap)*(batt_maint_cap))
    else:
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SLIGHTLY_SALINE_ENERGY_CAPACITY"] = None
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SLIGHTLY_SALINE_CAPEX"] = None
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SLIGHTLY_SALINE_OPEX"] = None
        
    if salinity_data.loc[salinity_data['COUNTY NAME'] == county, "CONTAINS_MODERATELY_SALINE"].any() == True:
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "MODERATELY_SALINE_ENERGY_CAPACITY"] = (np.max(energy_cap) * (moderately_saline_sec/slightly_saline_sec))
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "MODERATELY_SALINE_CAPEX"] = float(np.max(desal_cap)*desal_capex_cost + acres * county_land_costs.loc[county_land_costs['COUNTY'] == county, "PRICE_PER_ACRE"] + np.max(energy_cap)*(solar_cost_cap + batt_cost_cap)*(moderately_saline_sec/slightly_saline_sec))
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "MODERATELY_SALINE_OPEX"] = float(np.max(desal_cap)*desal_opex_cost * 365 + np.max(energy_cap)*(batt_maint_cap) * (moderately_saline_sec/slightly_saline_sec))
    else:
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "MODERATELY_SALINE_ENERGY_CAPACITY"] = None
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "MODERATELY_SALINE_CAPEX"] = None
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "MODERATELY_SALINE_OPEX"] = None
    
    if salinity_data.loc[salinity_data['COUNTY NAME'] == county, "CONTAINS_SALINE"].any() == True:
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SALINE_ENERGY_CAPACITY"] = (np.max(energy_cap) * (saline_sec/slightly_saline_sec))
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SALINE_CAPEX"] = float(np.max(desal_cap)*desal_capex_cost + acres * county_land_costs.loc[county_land_costs['COUNTY'] == county, "PRICE_PER_ACRE"] + np.max(energy_cap)*(solar_cost_cap + batt_cost_cap)*(saline_sec/slightly_saline_sec))
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SALINE_OPEX"] = float(np.max(desal_cap)*desal_opex_cost * 365 + np.max(energy_cap)*(batt_maint_cap) * (saline_sec/slightly_saline_sec))
    else:
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SALINE_ENERGY_CAPACITY"] = None
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SALINE_CAPEX"] = None
        desal_system_costs.loc[desal_system_costs['COUNTY'] == county, "SALINE_OPEX"] = None

#%%
#Saving results as a csv
desal_system_costs.to_csv("Desal_Estimates/EDR_desal_system_costs.csv")
# %%
