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

# Data File Year, a field used in MRCOG copies of these datasets
dfy = '{}-{}'.format(int(yr)-4, yr)  # Data File Year

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

####
annolist = []
####


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
# subj_address = subject_base_url + api

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


# FUNCTIONS ###################################################################
def makeTractCall(code):
    url = address.format(code, tract, '*')
    apiCall = requests.get(url)
    if apiCall.status_code == 400:
        failDict['{}_Tracts'.format(code)] = '400 Error - Tract'
        return False
    jsonArray = apiCall.json()
    df = pd.DataFrame(jsonArray[1:], columns=jsonArray[0])
    df = df.dropna(axis='columns', how='all')
    # tract_test = (df.shape[1] == 5 and geography == tract)
    if df.shape[1] == 5:
        failDict['{}_Tracts'.format(code)] = 'No Tracts Data'
        return False
    return df


def makeBlockGroupCall(code):
    url = address.format(code, blockGroup, '001')
    apiCall = requests.get(url)
    if apiCall.status_code == 400:
        failDict['{}_BG'.format(code)] = '400 Error - Block Group'
        return False
    jsonArray = apiCall.json()
    df = pd.DataFrame(jsonArray[1:], columns=jsonArray[0])
    check = df.dropna(axis='columns', how='all')
    if check.shape[1] == 6:
        failDict['{}_BG'.format(code)] = 'No Block Groups Data'
        return False
    for c in ['043', '049', '057', '061']:
        url = address.format(code, blockGroup, c)
        apiCall = requests.get(url)
        jsonArray = apiCall.json()
        df2 = pd.DataFrame(jsonArray[1:], columns=jsonArray[0])
        df = pd.concat([df, df2], ignore_index=True)
    df = df.dropna(axis='columns', how='all')
    return df


def processColumns(pandasDataFrame):
    """Pass me one pandas Data Frame"""
    df = pandasDataFrame
    # Get the column labels - the alphanumeric codes - as a list
    colCodes = df.columns.tolist()
    # Prepare to separate the codes by Estimate and Margin of Error
    eCols, mCols, bgCol = [], [], []
    # Sort the codes into separate lists
    for c in colCodes:
        if c[-1] == 'A' or c == 'NAME':
            continue
        elif c[-1] == 'E':
            eCols.append(c)
        elif c[-1] == 'M':
            mCols.append(c)
        elif c == 'block group':
            bgCol.append(c)
            df[c] = pd.to_numeric(df[c], errors='coerce')
        else:
            continue
    # They are not returned by the API in alphabetical or numeric order
    # Sorting them puts them in order
    # Generally, the alpha-numeric order follows a familiar logic
    # e.g., starting with a total, then breaking down into categories
    eCols.sort(), mCols.sort()
    # Values are returned from the API as text, but need to be numeric
    txtToNumCols = eCols + mCols + ['state', 'county', 'tract']
    for col in txtToNumCols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # The GeoIDs returned by the API are too long for most GIS Joins
    df['GEO_ID'] = df['GEO_ID'].str[9:]
    # Reorder columns by reordering the names
    colCodes = ['GEO_ID', 'state', 'county', 'tract']\
        + bgCol + ['NAME'] + eCols + mCols
    df = df[colCodes]
    # We need the shape of the table for entering some dummy/filler values
    tabLen = df.shape[0]
    # Create a column for a data vintage label
    df.insert(1, 'Data File Year', [dfy] * tabLen)
    # Creat a column for the state
    df.insert(2, 'State Name', ['New Mexico'] * tabLen)
    # Get lists of county, tract, and NAME values for processing
    countyCol = df['county'].tolist()
    tractCol = df['tract'].tolist()
    nameCol = df['NAME'].tolist()
    # Prepare a placeholder to receive County Names
    countyList = ['County'] * tabLen
    # A boolean field for indicating if the tract is in MRCOG's area
    mrcogBool = [0] * tabLen
    # A loop for processing these values
    for i in range(tabLen):
        # Get the County Name from the NAME field
        countyList[i] = nameCol[i].split(', ')[-2]
        # Identify which are in the MRCOG area
        if countyCol[i] in [1, 43, 57, 61]:
            mrcogBool[i] = 1
        elif countyCol[i] == 49 and tractCol[i] in [10310, 10311, 10312]:
            mrcogBool[i] = 1
    # Insert the County Name column
    df.insert(4, 'County Name', countyList)
    # Insert a Block Group column if necessary
    if len(bgCol) == 0:
        df.insert(7, 'block group', [''] * tabLen)
    # Insert the MRCOG Area list as a column
    df.insert(9, 'MRCOG Area', mrcogBool)
    # Return the dataframe with some column names processed
    return df


def columnNames(columnCode):
    """Pass me one string"""
    # Some column names are decided by MRCOG convention
    if columnCode in cogDict:
        cog_label = cogDict[columnCode]
        return [cog_label, cog_label]
    # The 2017 API lists M (margin of error) as sub-types of E
    # So they can't be accessed individually
    # Remove the M, add an E
    colCodeRoot = columnCode[:-1]+'E'
    # Variable names/descriptions are stored as JSON in the API,
    # and can be accessed like dictionaries within dictionaries
    col = variableDict['variables'][colCodeRoot]['label']
    if '$' in col:
        usd_amts = re.findall('(\$\d+ )(\d\d\d)( \d\d\d)?', col)
        if usd_amts:
            for i in range(len(usd_amts)):
                thousands = [t.strip() for t in usd_amts[i] if t != '']
                col = col.replace(''.join(thousands), ','.join(thousands))
    # Creates a 'plain' description of the variable
    plaintext = col.replace('!!', '; ')  # .replace('$', 'USD')
    if '.' in col:
        decimals = re.findall('(\d+)\.(\d+)', col)
        if decimals:
            for i in range(len(decimals)):
                vals = [v for v in decimals[i]]
                col = col.replace('.'.join(vals), 'd'.join(vals))
    badchars = OrderedDict({
            '!!': '_',
            '$': 'USD',
            'U.S.': 'US',
            'Estimate': 'Est',
            'Median': 'Mdn',
            'in the past 12 months': 'past yr',
            'occupations': 'jobs',
            'Population': 'Pop',
            'population': 'pop',
            'excluding': 'excl',
            'year': 'yr',
            'percent': 'pct',
            'level': 'lvl',
            'health insurance coverage': 'hlth ins',
            'health': 'hlth',
            'insurance': 'ins',
            'Public': 'Pub',
            'public': 'pub',
            'English': 'Eng',
            'family': 'fam',
            'Family': 'Fam',
            'management': 'mgmt',
            'transportation': 'trans',
            'taxicab': 'taxi',
            'school': 'schl',
            'languages': 'lang',
            'incorporated': 'inc',
            'household': 'HH',
            'Household': 'HH',
            'households': 'HH',
            'Households': 'HH',
            'Housing units': 'HU',
            'housing units': 'HU',
            'Total': 'Tot',
            ' ': '_',
            'United_States': 'US',
            'the_US': 'US',
            '_-_': '_',
            '___': '_',
            '__': '_'
            })
    for k, v in badchars.items():
        col = col.replace(k, v)
    # translates each character, based on its unicode number, to nothing
    col = col.translate({ord(c): '' for c in '''!"'(),-./:;[]{}'''})
    # Add Est and MoE to indicate Estimate or Margin of Error
    # File geodatabase fields names max out at 64 characters
    if columnCode[-1] == 'M':
        col = col.replace('Est_', 'MoE_')
        plaintext = plaintext.replace('Estimate;', 'Margin of Error;')
    if len(col) > 64:
        col = col.replace('Est_', 'E_')\
                 .replace('Tot_', 'T_')\
                 .replace('MoE_', 'M_')
    if len(col) > 64:
        col = columnCode
    # Gives us a dictionary where each code has a full description
    # and a database compliant name (code: [desc, name])
    return [plaintext, col]


for code in tableList:
    # TRACTS
    print('Starting {} for {}'.format(code, tract))
    result = makeTractCall(code)
    # Return could be a DF or an Error code.
    # Error codes are added to a dictionary by the function.
    # Data Frames are processed:
    if type(result) == pd.core.frame.DataFrame:
        # Annotation values need to be removed
        annoT = ['-999999999',
                 '-888888888',
                 '-666666666',
                 '-555555555',
                 '-333333333',
                 '-222222222',
                 '*'
                 ]
        annoI = [int(i) for i in annoT if i != '*']
        annoF = [float(i) for i in annoT if i != '*']
        annoFT = [str(i) for i in annoF]
        anno = annoT + annoI + annoF + annoFT

        if True in [(i in result.values) for i in anno]:
            print('{} Tracts contains annotation'.format(code))
            annolist.append('{}.Tract'.format(code))
            result = result.replace(anno, '')
#        else:
#            continue
        # Plain text "concept" (title) of table
        plain_concept = variableDict['variables'][
                '{}_001E'.format(code)]['concept'].title()
        # Prepare a file system compliant table name by removing special chars
        # and shortening where possible
        concept = plain_concept.translate({
                ord(c): '' for c in '''!"'(),-./:;[]{}'''
                })
        filename_dict = OrderedDict({
                'In 2019 InflationAdjusted Dollars': '',
                ' ': '_',
                'The_United_States': 'US',
                'In_The_Past_12_Months': 'In_Past_Year',
                'The_': '',
                '___': '_',
                '__': '_'
                })
        for k, v in filename_dict.items():
            concept = concept.replace(k, v)
        # Use the function to begin processing column (field) names
        result = processColumns(result)
        # Get a list of column codes/names for further processing
        colCodes = result.columns.tolist()
        # This ordered dictionary, with column codes as keys,
        # forms the basis of a data dictionary for each table
        fielDict = OrderedDict.fromkeys(colCodes)
        # Iterate through keys, adding values based on returns from the func
        # The data dictionary will be a table with 3 columns:
        # Code, plain text, and field name
        for f in fielDict:
            fielDict[f] = columnNames(f)
        labels_list = [i[1] for i in fielDict.values()]
        # The "result" Data Frame will become the Excel sheet and GDB table
        # It needs clear but database compliant field names
        result.columns = labels_list

        # The following section is primarily for preparing a 'data dictionary'
        # sheet for each Excel file
        empty_cell = ''
        space = ' '
        # Spaces and empty cells are used to improve output formatting
        fielDict.update({
                space: [empty_cell, empty_cell],
                'FIELD CODE': ['DESCRIPTION', 'FIELD NAME']
                })
        # These values will be the "headers" of the data dictionary
        fielDict.move_to_end('FIELD CODE', last=False)
        fielDict.move_to_end(space, last=False)
        # Create a title for the data dictionary page
        head_text = 'Source Table: {}'.format(code)
        universe = universes[code]
        data_keys = [head_text, plain_concept, universe]
        # Create another dictionary to help format the page
        data_dict = OrderedDict.fromkeys(data_keys)
        # Moving values in order from one dictionary to the other
        first_column = [i for i in fielDict.keys()]
        second_column = [i[0] for i in fielDict.values()]
        third_column = [i[1] for i in fielDict.values()]
        data_dict[head_text] = first_column
        data_dict[plain_concept] = second_column
        data_dict[universe] = third_column
        # Put the dictionary into a DF so it can become a sheet in the workbook
        data_dict_frame = pd.DataFrame(data_dict)

        table_name = '{}_2019_ACS_5yr_Tract_{}'.format(concept, code)
        # In case XLSX format table is needed (they can support more columns,
        # but XLS are more compatible with ArcGIS)
        if result.shape[1] > 255:
            xlsx_folder = path.join(out_dir_tract, 'XLSX_format_tables')
            makedirs(xlsx_folder, exist_ok=True)
            excelPath = path.join(xlsx_folder, '{}.xlsx'.format(table_name))
        else:
            excelPath = path.join(out_dir_tract, '{}.xls'.format(table_name))
        with pd.ExcelWriter(excelPath) as excelout:
            data_dict_frame.to_excel(
                    excelout,
                    sheet_name='Data_Dictionary',
                    header=True,
                    index=False
                    )
            result.to_excel(
                    excelout,
                    sheet_name='Table_{}'.format(code),
                    header=True,
                    index=False
                    )

    # BLOCK GROUPS
    print('Starting {} for {}'.format(code, blockGroup))
    result = makeBlockGroupCall(code)
    if type(result) == pd.core.frame.DataFrame:
        # Annotation values need to be removed
        annoT = ['-999999999',
                 '-888888888',
                 '-666666666',
                 '-555555555',
                 '-333333333',
                 '-222222222',
                 '*'
                 ]
        annoI = [int(i) for i in annoT if i != '*']
        annoF = [float(i) for i in annoT if i != '*']
        annoFT = [str(i) for i in annoF]
        anno = annoT + annoI + annoF + annoFT

        if True in [(i in result.values) for i in anno]:
            print('{} BGs contains annotation'.format(code))
            annolist.append('{}.BG'.format(code))
            result = result.replace(anno, '')
#        else:
#            continue

        # Plain text "concept" (title) of table
        plain_concept = variableDict['variables'][
                '{}_001E'.format(code)]['concept'].title()
        # Prepare a file system compliant table name by removing special chars
        # and shortening where possible
        concept = plain_concept.translate({
                ord(c): '' for c in '''!"'(),-./:;[]{}'''
                })
        filename_dict = OrderedDict({
                'In 2019 InflationAdjusted Dollars': '',
                ' ': '_',
                'The_United_States': 'US',
                'In_The_Past_12_Months': 'In_Past_Year',
                'The_': '',
                '___': '_',
                '__': '_'
                })
        for k, v in filename_dict.items():
            concept = concept.replace(k, v)
        # Use the function to begin processing column (field) names
        result = processColumns(result)
        # Get a list of column codes/names for further processing
        colCodes = result.columns.tolist()
        # This ordered dictionary, with column codes as keys,
        # forms the basis of a data dictionary for each table
        fielDict = OrderedDict.fromkeys(colCodes)
        # Iterate through keys, adding values based on returns from the func
        # The data dictionary will be a table with 3 columns:
        # Code, plain text, and field name
        for f in fielDict:
            fielDict[f] = columnNames(f)
        labels_list = [i[1] for i in fielDict.values()]
        # The "result" Data Frame will become the Excel sheet and GDB table
        # It needs clear but database compliant field names
        result.columns = labels_list

        # The following section is primarily for preparing a 'data dictionary'
        # sheet for each Excel file
        empty_cell = ''
        space = ' '
        # Spaces and empty cells are used to improve output formatting
        fielDict.update({
                space: [empty_cell, empty_cell],
                'FIELD CODE': ['DESCRIPTION', 'FIELD NAME']
                })
        # These values will be the "headers" of the data dictionary
        fielDict.move_to_end('FIELD CODE', last=False)
        fielDict.move_to_end(space, last=False)
        # Create a title for the data dictionary page
        head_text = 'Source Table: {}'.format(code)
        universe = universes[code]
        data_keys = [head_text, plain_concept, universe]
        # Create another dictionary to help format the page
        data_dict = OrderedDict.fromkeys(data_keys)
        # Moving values in order from one dictionary to the other
        first_column = [i for i in fielDict.keys()]
        second_column = [i[0] for i in fielDict.values()]
        third_column = [i[1] for i in fielDict.values()]
        data_dict[head_text] = first_column
        data_dict[plain_concept] = second_column
        data_dict[universe] = third_column
        # Put the dictionary into a DF so it can become a sheet in the workbook
        data_dict_frame = pd.DataFrame(data_dict)

        table_name = '{}_2019_ACS_5yr_BlockGroup_{}'.format(concept, code)
        # In case XLSX format table is needed (they can support more columns,
        # but XLS are more compatible with ArcGIS)
        if result.shape[1] > 255:
            xlsx_folder = path.join(out_dir_bg, 'XLSX_format_tables')
            makedirs(xlsx_folder, exist_ok=True)
            excelPath = path.join(xlsx_folder, '{}.xlsx'.format(table_name))
        else:
            excelPath = path.join(out_dir_bg, '{}.xls'.format(table_name))
        with pd.ExcelWriter(excelPath) as excelout:
            data_dict_frame.to_excel(
                    excelout,
                    sheet_name='Data_Dictionary',
                    header=True,
                    index=False
                    )
            result.to_excel(
                    excelout,
                    sheet_name='Table_{}'.format(code),
                    header=True,
                    index=False
                    )

# Create a path and name for logging errors
fail_path = path.join(table_dir, 'Errors.xlsx')
print('Logging errors to {}'.format(fail_path))

# All errors returned by the API are in one dictionary
# Make it a Data Frame
failFrame = pd.DataFrame(failDict, index=[0])

# Transpose it for readability
failFrame = failFrame.T

# Output to an Excel workbook
failFrame.to_excel(fail_path, header=False, index=True)

print('Table Downloads Complete')
print(datetime.now() - start_time)
