import arcpy
import xlrd
from os import path

## File paths to input tables and output location for tracts
#workbook_folder = 'J:/acs2012/Excel_Workbooks_by_Tract'
#exportGBD = 'J:/acs2012/ACS_5yr_2012_Tract_Tables.gdb'
#
#### File paths to input tables and output location for block groups
###workbook_folder = '.../Excel_Workbooks_by_BlockGroup'
###exportGBD = '.../ACS_5yr_BlockGroup_Tables.gdb'
#
## Set workspace to table source in order to iterate through tables
#arcpy.env.workspace = workbook_folder
## List of excel workbooks (which are considered workspaces)
#workbook_list = arcpy.ListWorkspaces()
#
## Iterate through list
#for workbook in workbook_list:  # Each item in list is u-string of file path
#    desc = arcpy.Describe(workbook)  # Geoprocessing object
#    workbook_name = desc.basename  # u-string of workbook name without extension
#	# Open workbook with xlrd
#    open_book = xlrd.open_workbook(workbook)
#	# Get sheets in workbook
#    workbook_sheets = open_book.sheet_names()
#	# "Data_Dictionary" is in every workbook, but shouldn't be copied
#    for sheet in workbook_sheets:
#        if sheet != 'Data_Dictionary':
#			# Copy data sheet into geodatabase
#            arcpy.ExcelToTable_conversion(workbook, os.path.join(exportGBD, workbook_name), sheet)

# Done!

arcpy.env.overwriteOutput = True

working = path.normpath('D:/Staging/acs2019/')
twb = path.join(working, 'Excel_Workbooks_for_Tracts')
bwb = path.join(working, 'Excel_Workbooks_for_BlockGroups')
tgdb = path.join(working, path.normpath('Geodatabase_Tables/Tables_for_Tracts.gdb'))
bgdb = path.join(working, path.normpath('Geodatabase_Tables/Tables_for_BlockGroups.gdb'))

exports = {twb: tgdb, bwb: bgdb}

for k in exports.keys():
    arcpy.env.workspace = k
    workbook_list = [i for i in arcpy.ListWorkspaces() if path.basename(i) != 'XLSX_format_tables']
    for workbook in workbook_list:
        desc = arcpy.Describe(workbook)
        workbook_name = desc.basename
        open_book = xlrd.open_workbook(workbook)
        workbook_sheets = open_book.sheet_names()
        for sheet in workbook_sheets:
            if sheet != 'Data_Dictionary':
                arcpy.ExcelToTable_conversion(workbook, path.join(exports[k], workbook_name), sheet)