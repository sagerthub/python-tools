# Version 1.0 2022-02-16
# Requires ArcGIS Pro. Developed and tested in ArcGIS Pro 2.9 with default python env.
# Requires item report created in ArcGIS Online (AGOL). CSV format, field names unchanged.
# Requires user to be logged into AGOL Administrator (Admin) account through ArcGIS Pro or have username and password for Administrator account.
# Works with MRMPO's ArcGIS Online (AGOL).
# Cannot process Hub sites (skips them).

# organization_items_csv_name = 'OrganizationItems_2022-02-09.csv'
# Enter file path to CSV exported from AGOL between single quotes (keep r).
file_path_to_organization_items_csv = r''
# Enter path to folder where output table will be saved. Leave blank and output will be saved to the same folder as the script or APRX file.
folder_for_output_file = r''

# If you are not logged into an Admin account, enter username and password for Admin account here. Delete after running and do not save.
# Note that usig ArcGIS Pro with an Admin account is the most reliable and secure method.
p = ''
u = ''
credentials = [i for i in [p, u] if i != '']

from arcgis.gis import GIS
from os import path
import json
# import openpyxl
from openpyxl import Workbook
import pandas as pd
from datetime import datetime

start_time = datetime.now()

# Define getTry function. Tries to get AGOL item content based on item ID. Some items have IDs but no content and will cause errors with other functions. Soe items may be owned outside the organization and cannot be accessed, throwing an error. These cases will return None.
def getTry(agol_item_id):
    '''Takes one 32-character ArcGIS Online Item Id as a string and tries to get associated content. If item has content, item content object is returned. Otherwise None is returned.'''
    try:
        # Check if Item Id is in organization report. If not, it is assumed to not belong to the org and access will be denied, throwing an exception.
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

if credentials:
    # LOGIN WITH CREDENTIALS
else:
    # Create GIS and use Pro credentials to login
    gis = GIS('pro')

print('GIS connected.')

# Read list of item Ids from organization report
orgItemsIdList = pd.read_csv(organization_items_csv_name, usecols=['Item ID'], squeeze=True).to_list()
# Read list of item titles from organization report
orgItemsTitleList = pd.read_csv(organization_items_csv_name, usecols=['Title'], squeeze=True).to_list()
# Read list of item types from organzation report
orgItemsTypeList = pd.read_csv(organization_items_csv_name, usecols=['Item Type'], squeeze=True).to_list()
# Empty dictionary for combining Item Ids with Titles and Types
orgItemsSummary = {}
# Creating orgItemsSummary dictionary: {ItemId: [ItemTitle, ItemType]}
for i in range(len(orgItemsIdList)):
    if 'Hub' not in orgItemsTypeList[i]:
        orgItemsSummary[orgItemsIdList[i]] = [orgItemsTitleList[i], orgItemsTypeList[i]]

# Number of inputs as length of lists/dictionary for progress reporting
num_of_inputs = len(orgItemsSummary)
# Script will report progress in 5% increments (based on input items)
five_percent_increment = num_of_inputs/20

print('{} items to check. Progress updates every 5% (of items checked). Starting at {}'.format(num_of_inputs, datetime.now().isoformat()))

# Start with list containing header row for output table
itemMatrix = [['Parent Item ID', 'Parent Item Title', 'Parent Item Type', 'Relationship', 'Child Item ID', 'Child Item Title', 'Child Item Type']]

# Counters for progress reporting. First counter starts at 0 and adds one for every input Item Id processed.
counter = 0
# Five percent counter starts at 1 and adds one after every 5% of input items have been processed.
five_percent_counter = 1
# Length of output list. Number of new outputs is reported every 5%
previous_out_count = len(itemMatrix)
# Time between 5% icrements will be reproted
previous_time = datetime.now()

# Use previously defined function to iterate through all items in org list and create connections (dependencies) as lists
for orgItem in orgItemsSummary.keys():
    # Newly created lists are added to itemMatrix list for output to Excel table
    itemMatrix.extend(getAllDependencies(orgItem))
    # Counter adds 1
    counter += 1
    # Progress is checked (0.5 = 50%, 1 = 100%)
    progress = counter/num_of_inputs
    # Five percent counter (starting at 1) times 0.05 sets the next 5% target. Once this condition is met, next target is set. Each 5% increment is reported only once.
    if progress > five_percent_counter*0.05:
        # Format % text
        progress_percent = '{0:.0%}'.format(progress)
        # Check time elapsed
        progress_time = datetime.now() - previous_time
        # Check outputs found
        progress_count = len(itemMatrix) - previous_out_count
        # Print 5% report
        print('{} of inputs checked. {} elapsed and {} connections found since last progress update'.format(progress_percent, progress_time, progress_count))
        # Set time and count variables for next report
        previous_time = datetime.now()
        previous_out_count = len(itemMatrix)
        five_percent_counter += 1

# Create openpyxl workbook (wb) and worksheet (ws)
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
