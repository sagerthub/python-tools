# -*- coding: utf-8 -*-
"""
Download, format, and save Census ACS tables from a list of table numbers.

More description coming soon.
"""
import requests  # Retrieving url-based API requests
import pandas as pd  # Data frames and Excel writing
from os import path, makedirs  # Path and file access
from collections import OrderedDict  # Ordered dictionaries for data dictionary
import re  # Regular expressions for string editing
from datetime import datetime

start_time = datetime.now()

# USER INPUTS HERE ############################################################
# End year of 5 yr dataset (e.g., 2017 = 2013-2017)
yr = '2019'
# Working directory
# MUST CONTAIN: download table, Table Shells
table_dir = path.normpath(r'D:/Staging/acs2019')
# Excel workbook with list of table codes for download
table_xls = 'ACS_Tables_for_Download_python.xlsx'
# Sheet number (first sheet = 0)
table_sheet = 0
# Column number (first column = 0)
table_col = 0
###############################################################################

# OS Path creates full file paths
table_path = path.join(table_dir, table_xls)

# Create necessary directories (and suppresses OSError if they already exist)
# Output directories for workbooks
out_dir_tract = path.join(table_dir, 'Excel_Workbooks_for_Tracts')
out_dir_bg = path.join(table_dir, 'Excel_Workbooks_for_BlockGroups')
makedirs(out_dir_tract, exist_ok=True)
makedirs(out_dir_bg, exist_ok=True)

# Vintage, a field used in MRCOG copies of these datasets
vintage = '{}-{}'.format(int(yr)-4, yr)  # Data File Year >> Vintage

# Dictionary of Column Name pairs that we will use across all tables
# (and don't need to be retrieved from the API)
cogDict = {
    'GEO_ID': 'GeoID',
    'Data File Year': 'Vintage',
    'State Name': 'StateName',
    'state': 'StateCode',
    'County Name': 'CountyName',
    'county': 'CountyCode',
    'tract': 'TractCode',
    'block group': 'BgCode',
    'NAME': 'AreaName',
    'MRCOG Area': 'MrcogArea'
}

# Dictionary for managing failed API calls
failDict = {}

# Base API URL
base_url = 'https://api.census.gov/data/{}/acs/acs5'.format(yr)
# subject_base_url = '{}/subject'.format(base_url)

# Variables (table codes and names as dictionary)
variables_url = '{}/variables.json'.format(base_url)

# Request for address, returned as text
get_variables = requests.get(variables_url)

# Text to JSON (python recognizes as a dictionary)
variableDict = get_variables.json()

# API Key: 722d2ba6712f3952d8daba907b503768680f20ce
# Sample Query: https://api.census.gov/data/2017/acs/acs5
#                       ?get=group(B05002)
#                       &for=tract:*
#                       &in=state:35
#                       &in=county:001
#                       &key=722d2ba6712f3952d8daba907b503768680f20ce

# Address template for whole state with 3 format openings:
# group ID and geography level and county (necessary for block groups)
api = '?get=group({})'\
          '&for={}:*' \
          '&in=state:35' \
          '&in=county:{}' \
          '&key=722d2ba6712f3952d8daba907b503768680f20ce'
# Geography variables for use with the address
blockGroup = 'block%20group'
tract = 'tract'
address = base_url + api

# Use pandas' built-in excel reader to get list of table codes for download
table_column = pd.read_excel(
        table_path,
        header=None,
        sheet_name=table_sheet,
        usecols=[table_col],
        squeeze=True
        )
tableList = table_column.to_list()

# Create dictionary of Universes from Table Shells
table_shells_xlsx = path.join(table_dir, 'ACS2019_Table_Shells.xlsx')
shells = pd.read_excel(table_shells_xlsx)
shells_universe = shells[shells['Stub'].str.contains('Universe') == True]
universes = dict(zip(shells_universe['Table ID'], shells_universe['Stub']))


def apiCall(year, table, geography, county, state='35'):
    base_url = 'https://api.census.gov/data/'