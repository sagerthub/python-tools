import arcpy
from os import path
from datetime import datetime

start = datetime.now()

table_gdb = [path.normpath('D:/Staging/acs2019/Geodatabase_Tables/Tables_for_Tracts.gdb'), path.normpath('D:/Staging/acs2019/Geodatabase_Tables/Tables_for_BlockGroups.gdb')]
features_gdb = [path.normpath('D:/Staging/acs2019/Tracts_NM_ACS2019.gdb'), path.normpath('D:/Staging/acs2019/BlockGroups_MRCOG_ACS2019.gdb')]
fd = ['NM_Tracts_2019', 'MRCOG_BlockGroups_2019']
fc = ['NM_Tracts_2019', 'MRCOG_BlockGroups_2019']

fjoin = 'GeoID_Join_text'
tjoin = 'GIS_Join_Match_Code'

for i in range(len(table_gdb)):
    print('Starting GDB {} of {}'.format(i+1, len(table_gdb)))
    arcpy.env.workspace = table_gdb[i]
    #arcpy.env.overwriteOutput = True
    features = path.join(features_gdb[i], fd[i], fc[i])
    table_list = [str(t) for t in arcpy.ListTables()]
    print('Found {} tables in GDB {}'.format(len(table_list), i))
    for t in table_list:
    	out_fc = path.join(features_gdb[i], t)
    	arcpy.CopyFeatures_management(features, out_fc)
    	join_fields = [str(f.name) for f in arcpy.ListFields(t)][2:]
    	arcpy.JoinField_management(out_fc, fjoin, t, tjoin, join_fields)
    print('Finished GDB {} of {}'.format(i+1, len(table_gdb)))

print (datetime.now() - start)