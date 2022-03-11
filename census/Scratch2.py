https://api.census.gov/data/
                            2020
                                /acs
                                    /acs5
                                         /variables.json
                                         ?get=
                                              group(B05002)
                                              ...
                                              ...
                                              ...
                                                           &for=
                                                                tract:
                                                                block group:
                                                                      *
                                                                       &in=
                                                                           state:
                                                                                 35
                                                                                 ...
                                                                                 ...
                                                                                 ...
                                                                                   &in=
                                                                                       county:
                                                                                              001
                                                                                              043
                                                                                              ...
                                                                                              ...
                                                                                                 &key=
                                                                                                      ljslkfjal;kdjfl;akjdflajkd
                                                                                                      
class APIKeyError

class CensusAPI(object):
    base_url = 'https://api.census.gov/data/{}/{}/{}'
    def __init__(self, api_key):
        self.api_key = api_key
        if type(self.api_key) != str or len(self.api_key) != 40:
            raise APIKeyError
        return

class CensusYear(CensusAPI):
    inheret...
        make int/str/float variations

class ACS(CensusYear):
    inheret...
        
class 

