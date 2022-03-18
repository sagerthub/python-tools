"""
1. Request

2. "Process Columns"
    a. def columnCategories(df):
            categorize
            sort
            return aCols, eCols, mCols, placeCols
    b. def shortGeoId(df, geoid='GEO_ID').........    ????, to_new_column=True, new_column_name='GeoID'): ???
            return df
    c. def mrcogRegionCheck(df):
            add column of 'Yes' and 'No'
    d. def ampaRegionCheck(df):
            add column of 'Yes' and 'No' (should these be the same function?)
    e. def regionCheck(df, region='Both', list_of_GeoIDs=None)
            return df
    f. nameCounty(...)
            ...
    g. order output? or order as they go by checking column position and inserting +1?
"""

"""
- do annotation replace AFTER splitting out annotation table, just in case
    https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.replace.html
    def replaceAnnotation(df):
        df.replace(to_replace=annotation_all_types, value='')
        return df


"""
