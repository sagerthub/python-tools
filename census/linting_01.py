# -*- coding: utf-8 -*-
"""
Created on Mon Mar 28 16:25:10 2022.

@author: sager
"""
import requests
import pandas as pd
from os import path, makedirs
# import re
from collections import OrderedDict
from datetime import datetime


acs_api_url = 'https://api.census.gov/data/{}/acs/acs5'


def mostRecentYear(program='acs5'):
    if program == 'acs5':
        year = datetime.now().year
        code = requests.get(acs_api_url.format(year)).status_code
        while code != 200:
            year -= 1
            check_url = acs_api_url.format(year)
            code = requests.get(check_url).status_code
        return year
    else:
        return None


tract_keywords = [
    'tract',
    'tracts'
]

block_group_keywords = [
    'blockgroup',
    'block_group',
    'block group',
    'bg',
    'blockgroups',
    'block_groups',
    'block groups',
    'bgs'
]

geography_keywords = tract_keywords + block_group_keywords


def setCounty(county_fips_code='*', state_fips_code='35'):
    state = str(state_fips_code).zfill(2)
    if state.isnumeric():
        state = '&in=state:{}'.format(state)
    else:
        return None

    if county_fips_code.lower() in ['all', '*']:
        county = '&in=county:*'
    elif county_fips_code.zfill(3).isnumeric():
        county = '&in=county:{}'.format(county_fips_code.zfill(3))
    else:
        return None

    county_query = state + county
    return county_query


def setArea(area='tract', fips_code='*'):
    if area.lower() not in geography_keywords:
        return None

    if area.lower() in tract_keywords:
        area = 'tract'
    elif area.lower() in block_group_keywords:
        area = 'block%20group'
    else:
        return None

    fips_code = str(fips_code)
    if fips_code.lower() in ['*', 'all']:
        code = '*'
    elif fips_code.isnumeric():
        code = fips_code
    else:
        return None

    area_query = f'&for={area}:{code}'
    return area_query


def buildQuery(api_key, table, area_query=None, county_query=None, year=None):
    api_key = api_key

    table = str(table)
    if '_' not in table:
        table = f'group({table})'
    elif '_' in table:
        table = table
    else:
        return None

    if year:
        year = str(year)
    else:
        year = mostRecentYear()

    if area_query:
        area_query = str(area_query)
        if '&for=' not in area_query:
            return None
        else:
            area_query = area_query
    else:
        area_query = setArea()

    if county_query:
        county_query = str(county_query)
        if '&in=' not in county_query:
            return None
        else:
            county_query = county_query
    else:
        county_query = setCounty()

    query = '{}?get={}{}{}&key={}'.format(
        acs_api_url.format(year),
        table,
        area_query,
        county_query,
        api_key
    )
    return query


def parseQuery(query):
    query_parts = query.split('=')
    api_parts = query_parts[0].split('/')
    year = api_parts[4]
    program = api_parts[6].split('?')[0]
    table = query_parts[1].split('&')[0]
    area = query_parts[2].split(':')[0]
    state = query_parts[3].split(':')[1].split('&')[0]
    county = query_parts[4].split(':')[0]
    key = query_parts[5]
    parsed_query = {
        'Year': year,
        'Program': program,
        'Table': table,
        'Area': area,
        'State': state,
        'County': county,
        'Key': key
    }
    return parsed_query
    
def createErrorLog():
    error_log = pd.DataFrame(
        {
        'Year': [],
        'Program': [],
        'Table': [],
        'Area': [],
        'State': [],
        'County': [],
        'Key': []
        }
    )
    return error_log

def getTable(query):
    call = requests.get(query)
    if call.status_code == 200:
        jsonArray = call.json()
        return jsonArray
    else:
        return None

def isEmptyTable(pandasDataFrame):
    shape_check = pandasDataFrame.dropna(axis='columns', how='all').shape[1]
    bg_check = 'block group' in pandasDataFrame.columns.to_list()
    if shape_check == 5:
        return True
    elif shape_check == 6 and bg_check:
        return True
    else:
        return False
    
def getTableToPandas(query, error_log=None):
    result = getTable(query)
    if result:
        df = pd.DataFrame(result[1:], columns=result[0])
        ### NEED A BETTER CHECK THAN THIS ###
        ## if df.dropna(axis='columns', how='all').shape[1] in [5, 6]:
        # Make this a separate function, and/or make it a parameter
# ---
        if isEmptyTable(df):
#         if (
#             'tract' in query and df.dropna(axis='columns', how='all'.shape[1]) == 5
#         ) or (
#             'block%20group' in query and df.dropna(axis='columns', how='all').shape[1] == 6
#         ):
            if error_log:
                empty_result = parseQuery(query)
                # concat is not done in place, meaning the return needs to be captured and re-returned
                # .loc should do this in place
                # error_log = pd.concat([error_log, pd.DataFrame(empty_result)], ignore_index=True)
                error_log.loc[len(df.index)] = [v for k, v in empty_result.items()]
                return None
            else:
                return None
        else:
            return df
# ---


## ------
        cols_by_letter = sortColumns(df)
        num_cols = cols_by_letter['E'] + cols_by_letter['M']
        # Should E and M be sorted together?
        # num_cols.sort()
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')
## ------


    else:
        bad_result = parseQuery(query)
        # error_log = pd.concat([error_log, pd.DataFrame(bad_result)], ignore_index=True)
        error_log.loc[len(df.index)] = [v for k, v in bad_result.items()]
        return None


def countiesByBlockGroups(api_key, table, list_of_county_fips_codes, year=None, error_log=None):
    api_key = api_key
    
#     table = str(table)
#     if '_' not in table:
#         table = f'group({table})'
#     elif '_' in table:
#         table = table
#     else:
#         return None

    table = setTable(table)
    
    if year:
        year = str(year)
    else:
        year = mostRecentYear()
    
    e = error_log
    
    if type(list_of_county_fips_codes) == list:
        fips = [str(c).zfill(3) for c in list_of_county_fips_codes]
        counties = [f for f in fips if len(f) == 3]
    else:
        return None

    bg = setArea('bg', '*')
    co = setCounty(counties[0])
    q = buildQuery(api_key, table, area_query=bg, county_query=co, year=year)

    df = getTableToPandas(q, e)
    
    if df:
        for c in counties[1:]:
            qx = q.replace(co, setCounty(c))
            dfx = getTableToPandas(qx, e)
            df = pd.concat([df, dfx], ignore_index=True)
        return df
    else:
        return None
    

base_api_label_dictionary = {
    'GEO_ID': 'GeoID',
    'NAME': 'AreaName',
    'state': 'StateFIPS',
    'county': 'CountyFIPS',
    'tract': 'TractCE',
    'block group': 'BlkGrpCE'
}

filename_dict = OrderedDict(
    {
        ' ': '_',
        'The_United_States': 'U.S.',
        'In_The_Past_12_Months': 'In_Past_Year',
        'The_': '',
        '___': '_',
        '__': '_'
    }
)


def pandasRegion(DataFrame, SourceColumn, TargetColumn, Reference):
    """CHECK IF THIS NEED TO RETURN THE DF."""
    def insideRegion(pd_df):
        g = pd_df[SourceColumn]
        if g in Reference:
            return 'Yes'
        else:
            return 'No'
    DataFrame[TargetColumn] = DataFrame.apply(insideRegion, axis=1)
    return DataFrame


def areaName(DataFrame, SourceColumn, TargetColumn, Reference):
    """CHECK IF THIS NEEDS TO RETURN THE DF."""
    def nameLookup(pd_df):
        f = pd_df[SourceColumn]
        if f in Reference:
            n = Reference[f]
            return n
        else:
            return None
    DataFrame[TargetColumn] = DataFrame.apply(nameLookup, axis=1)
    return DataFrame


def simpleGeoid(pandasDataFrame):
    """CHECK IF THIS NEEDS TO RETURN THE DF."""
    df = pandasDataFrame
    df['GEO_ID'] = df['GEO_ID'].str[9:]
    return


def sortColumns(pandasDataFrame):
    """
    Sort column names by API return type.

    Takes pandas data frame with Census API data and field names.
    Returns dictionary with the followign key:value pairs:
    'A': list of Annotation fields,
    'E': list of Estimate fields,
    'M': list of Margin of Error fields,
    'G': list of Geography/Place fields.
    """
    df = pandasDataFrame
    colNames = df.columns.to_list()
    annos, ests, moes, places = [], [], [], []
    for c in colNames:
        if c[-1] == 'A':
            annos.append(c)
        elif c[-1] == 'E' and c != 'NAME':
            ests.append(c)
        elif c[-1] == 'M':
            moes.append(c)
        else:
            places.append(c)
    for i in [annos, ests, moes, places]:
        i.sort()
    letter_categories = {
        'A': annos,
        'E': ests,
        'M': moes,
        'G': places
    }
    return letter_categories


def getUniversesFromShells(pathToTableShellsXLSX):
    """Get dictionary of Universe definitions."""
    t = pathToTableShellsXLSX
    shells = pd.read_excel(t)
    shells = shells[shells['Stub'].str.contains('Universe') == True]
    universes = dict(zip(shells['Table ID'], shells['Stub']))
    return universes


def getTableIdFromDataFrame(pandasDataFrame):
    """Check Table ID of a data frame."""
    cols = pandasDataFrame.columns.to_list()
    code = ''
    while code == '':
        for c in cols:
            if c not in base_api_label_dictionary:
                code = c.split('_')[0]
    return code


def removeInflation(string, space=' '):
    """Shorten variable names by removing inflation text."""
    if space not in {' ', '_'}:
        return string
    else:
        s = string.lower().replace(' ', '_')

    inf_variation = [i for i in [
        'inflationadjusted',
        'inflation-adjusted',
        'inflation_adjusted'
        ] if i in s]
    if inf_variation:
        start_i = s.index('_(in_')
        end_i = s.index('_dollars)') + len('_dollars)')
        shortened = s[:start_i] + s[end_i:]
        shortened = shortened.title()
    else:
        return string

    if space == ' ':
        shortened = shortened.replace('_', ' ')

    return shortened


def shortVariableDict(variables, table_list):
    shortDict = {}
    for k, v in variables.items():
        if k.split('_')[0] in table_list:
            shortDict[k] = v
        else:
            continue
    return shortDict


def fullVariableDict(variables):
    attrs = {}
    for k, v in variables.items():
        for i in variables[k]["attributes"].split(','):
            if 'EA' in i:
                attrs[i] = v['label'].replace(
                    'Estimate!!', 'Annotation of Estimate!!'
                    )
            elif 'MA' in i:
                attrs[i] = v['label'].replace(
                    'Estimate!!', 'Annotation of Margin of Error!!'
                    )
            elif 'M' in i:
                attrs[i] = v['label'].replace(
                    'Estimate!!', 'Margin of Error!!'
                    )
    return attrs


def tableTitleFileName(table_title_as_string):
    '''THIS ASSUMES FILENAME_DICT IS A GLOBAL VARIABLE'''
    t = table_title_as_string
    t = t.translate(
        {ord(char): '' for char in '''!"'(),-./:;[]{}'''}
    )
    for k, v in filename_dict.items():
        t = t.replace(k, v)
    t = removeInflation(t)
    t = t.replace('__', '_')
    return t


def cleanAlias(string):
    s = string.replace(':!!', '; ')
    s = s.replace('!!', ': ')
    return s


def createDataDictionary(pandasDataFrame, tableId=None):
    '''THIS ASSUMES TABLETITLES, TABLEUNIVERSE ARE GLOBAL'''
    if tableId:
        tableId = tableId
    else:
        tableId = getTableIdFromDataFrame(pandasDataFrame)
    fields = pandasDataFrame.columns.to_list()
    aliases = [cleanAlias(VARIABLES[f]) for f in fields]
    df = pd.DataFrame({
        'Table ID: {}'.format(tableId): ['', 'FIELD CODE'] + fields,
        tableTitles[tableId]: ['', 'FIELD ALIAS'] + aliases,
        tableUniverses[tableId]: ['', ''] + [''] * len(fields)
    })
    return df


# Set year, key

y = 2020
mrcogkey = '722d2ba6712f3952d8daba907b503768680f20ce'

# Set working paths

working_folder = path.normpath('D:/Staging/acs2020v2')

# Script creates output folders
out_anno_dir = path.join(working_folder, 'Tables_with_Annotation')
out_dir_tract = path.join(working_folder, 'ExcelWorkbooks_Tracts')
out_dir_bg = path.join(working_folder, 'ExcelWorkbooks_BlockGroups')
for d in [out_anno_dir, out_dir_tract, out_dir_bg]:
    makedirs(i, exist_ok=True)

# Get list of tables
tables = pd.read_excel(
    path.join(working_folder, 'ACS_Tables_for_Download_python.xlsx'),
    header=None,
    sheet_name=0,
    usecols=0,
    squeeze=True
).to_list()


# def getUniversesFromOtherTable()
dataProductList_5Year_xlsx = 'D:/Staging/acs2020/2020_DataProductList_5Year.xlsx'
dpl = pd.read_excel(dataProductList_5Year_xlsx)

tableTitles = dict(zip(dpl['Table ID'], dpl['Table Title']))
tableUniverses = dict(zip(dpl['Table ID'], dpl['Table Universe']))

tableFileNames = {k: tableTitleFileName(v) for k, v in tableTitles.items()}

# def getVariablesByYear()
var_url = 'https://api.census.gov/data/{}/acs/acs5/variables.json'.format(y)
simpleVariableDict = requests.get(var_url).json()['variables']
shortenedVariables = shortVariableDict(simpleVariableDict, tables)
allVariables = fullVariableDict(shortenedVariables)
# def getConcept()

mrcog_counties = ['001', '043', '049', '057', '061']
# Supp resources
## Field/alias dictionary
## Universes
## Table/file names
errors = createErrorLog()
# For table in table list...
for tableId in tables:
    ###### For tract AND blockgroup...
    for area in ['Tracts', 'BlockGroups']:
#     area = 'Tracts'
        q = buildQuery(mrcogkey, tableId, setArea(area), setCounty('*'), y)
        if area == 'Tracts':
            df = getTableToPandas(q, errors)
        elif area == 'BlockGroups':
            df = countiesByBlockGroups(mrcogkey, tableId, mrcog_counties, y, errors)
        if not df:
            continue
        simpleGeoid(df)
        df = pandasRegion(df, 'GEO_ID', 'MRCOG_Area', mrcog_tracts)

        cols_by_letter = sortColumns(df)

        anno_schema = cols_by_letter['G'] + cols_by_letter['A']
        anno_df = df[anno_schema]
        if not isEmptyTable(anno_df):
            anno_labels = [cleanAlias(FULL_VARIABLE_DICT[a]) for a in anno_df.columns.to_list()]
            anno_df.loc[-1] = anno_labels
            df.index = df.index + 1
            df.sort_index(inplace=True)
            out_anno_name = '{}_{}acs5_Annotation.xlsx'.format(tableId, y)
            out_anno_path = path.join(out_anno_dir, out_anno_name)
            df = df.replace(annotation_all_types, '')

        # After that, the rest is just formatting? Table name, dictionary, and universe?
        main_schema = cols_by_letter['G'] + cols_by_letter['E'] + cols_by_letter['M']
        df = df[main_schema]
        main_labels = [allVariables[m] for m in df.columns.to_list()]

        dataDictionary = createDataDictionary(df, tableId)

        output_file_name = '{}_{}acs5_{}_{}.xlsx'.format(
            tableId,
            y,
            area,
            tableFileNames[tableId]
        )
        out_dir = path.join(working_folder, 'ExcelWorkbooks_{}'.format(area))
        out_file_path = path.join(out_dir, output_file_name)

        if len(out_file_path) > 260:
            maxFileLen = 255 - len(out_dir)
            truncated_filename = output_file_name[:maxFileLen] + '.xlsx'
            out_file_path = path.join(out_dir, truncated_filename)

        with pd.ExcelWriter(fullOutputPath) as excelOut:
            dataDictionary.to_excel(
                excelOut,
                sheet_name='Data_Dictionary',
                header=True,
                index=False
            )
            result.to_excel(
                excelOut,
                sheet_name='Table_{}'.format(tableId),
                header=True,
                index=False
            )

out_error_path = path.join(working_folder, 'ApiErrorLog.xlsx')
errors.to_excel(out_error_path)
