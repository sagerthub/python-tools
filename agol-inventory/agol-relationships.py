# Version 1.0 2022-02-16
# Works with MRMPO's ArcGIS Online (AGOL)
# Cannot process Hub sites (skips them)

organization_items_csv_name = 'OrganizationItems_2022-02-09.csv'
#file_path_to_organization_items_csv

from arcgis.gis import GIS
# from os import path
import json
# import openpyxl
from openpyxl import Workbook
import pandas as pd
from datetime import datetime

start_time = datetime.now()

def getTry(agol_item_id):
    try:
        if agol_item_id in orgItemsSummary:
            item_content = gis.content.get(agol_item_id)
            return item_content
        else:
            return None
    except:
        pass
        return None
        
def itemDataToIdList(agol_item_id):
    '''Takes one 32-character ArcGIS Online Item Id as a string and returns a list of items found in the original item's data. Elements of the list are lists with the discovered item id, its title, and its type.'''
    # Get content object for item
    agol_item = getTry(agol_item_id)
    # Some item ids point to null content - like a folder. If not null...
    if agol_item:
        # Get data returns a string or dictionary describing the item
        agol_item_data = agol_item.get_data()
        # For maps and apps, get data returns a dictionary with settings, configurations, etc. that also points to the items it depends on
        # The string values do not point to any additional data and are treated as an endpoint (has no further dependencies)
        if agol_item_data and type(agol_item_data)==dict:
            # Dump dictionary to string (text)
            dump = json.dumps(agol_item_data)
            # Replace special characters with spaces
            for spec_char in '!"(),-./:;[]{}':
                dump = dump.replace(spec_char, ' ')
            # Split on spaces and find 32-charcter items - assumed to be Item Ids
            list_of_item_ids_from_dump = [i for i in dump.split(' ') if len(i)==32 and i != agol_item_id]
            # Output a list of the Item Id, Title, and Type suitable for use in a table - also checks for and excludes non-content
            list_of_items_with_title_and_type = [
                [
                    i, 
                    orgItemsSummary[i][0], 
                    orgItemsSummary[i][1]
                ] for i in list_of_item_ids_from_dump if i in orgItemsSummary
            ]
            return list_of_items_with_title_and_type
        else:
            return []
    else:
        return []

def getAllDependencies(agol_item_id):
    '''Takes one 32-character ArcGIS Online Item Id as a string and searches a list of other item ids in the original item's data. Continues searching through all referenced item ids - including items nested within items - and returns a list of lists. Each sublist comprises the original item's id, title, and type, and a dependency's item id, title, and type.'''
    # Create new list with item id
    list_of_item_ids = [agol_item_id]
    # Create empty output list
    list_of_dependencies = []
    # Will continue searching as long as item ids are added to the original list
    while len(list_of_item_ids) > 0:
        # Pops (removes) item id from list when it is searched
        agol_item_to_check = list_of_item_ids.pop(0)
        # Uses previously defined function to find associated item ids
        candidate_items = itemDataToIdList(agol_item_to_check)
        # Isolates item ids from return (return includes titles and types)
        candidate_ids = [i[0] for i in candidate_items]
        # Adds new item ids to origina list so their dependencies will be checked
        list_of_item_ids.extend(candidate_ids)
        # Iterate through discovered items to form lists suitable for use in a table
        for i in candidate_items:
            if i[0] in orgItemsSummary:
                list_of_dependencies.append([
                    agol_item_to_check,
                    orgItemsSummary[agol_item_to_check][0],
                    orgItemsSummary[agol_item_to_check][1]
                ] + ['CONTAINS'] + i)
    return list_of_dependencies


# Read list of item Ids from organization report
orgItemsIdList = pd.read_csv(organization_items_csv_name, usecols=['Item ID'], squeeze=True).to_list()
orgItemsTitleList = pd.read_csv(organization_items_csv_name, usecols=['Title'], squeeze=True).to_list()
orgItemsTypeList = pd.read_csv(organization_items_csv_name, usecols=['Item Type'], squeeze=True).to_list()
orgItemsSummary = {}
for i in range(len(orgItemsIdList)):
    if 'Hub' not in orgItemsTypeList[i]:
        orgItemsSummary[orgItemsIdList[i]] = [orgItemsTitleList[i], orgItemsTypeList[i]]

num_of_inputs = len(orgItemsSummary)
five_percent_increment = num_of_inputs/20

# Create GIS and use Pro credentials to login
gis = GIS('pro')

print('GIS connected. {} items to check. Progress updates every 5% (of items checked). Starting at {}'.format(num_of_inputs, datetime.now().isoformat()))

# Start with list containing header row for output table
itemMatrix = [['Parent Item ID', 'Parent Item Title', 'Parent Item Type', 'Relationship', 'Child Item ID', 'Child Item Title', 'Child Item Type']]

counter = 0
five_percent_counter = 1
previous_out_count = len(itemMatrix)
previous_time = datetime.now()

# Use previously defined function to iterate through all items in org list and create connections (dependencies) as lists
for orgItem in orgItemsSummary.keys():
    # Newly created lists are added to itemMatrix list for output to Excel table
    itemMatrix.extend(getAllDependencies(orgItem))
    counter += 1
    progress = counter/num_of_inputs
    if progress > five_percent_counter*0.05:
        progress_percent = '{0:.0%}'.format(progress)
        progress_time = datetime.now() - previous_time
        progress_count = len(itemMatrix) - previous_out_count
        print('{} of inputs checked. {} elapsed and {} connections found since last progress update'.format(progress_percent, progress_time, progress_count))
        previous_time = datetime.now()
        previous_out_count = len(itemMatrix)
        five_percent_counter += 1

# Create openpyxl workbook and worksheet
wb = Workbook()
ws = wb.active

# Each list is written as a row to the output Excel table
for itemConnection in itemMatrix:
    ws.append(itemConnection)

# Get system time (local time zone) for file time stamp
file_time = datetime.now().isoformat()[:19]
# Format time stamp for file name
file_time_stamp = file_time.replace('T', '_').replace('-', '').replace(':', '')
# Create file name
out_file = 'AGOL_Item_Dependency_Matrix_{}.xlsx'.format(file_time_stamp)

# Write output file
wb.save(out_file)

print('All done!')
print(datetime.now() - start_time)
