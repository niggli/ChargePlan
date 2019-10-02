######################################################################################
# Measurement.py
# Interface to different solarpower measurement classes. At the moment:
#
# Swissmeteo: gets duration of sunshine in minutes withing the last 10 minutes
######################################################################################

#requests is the defacto standard library for using REST
import requests

class Swissmeteo:

    def __init__(self, stationID):
        self.stationID = stationID

    def getSunshineDuration(self):
        # For offline testing:
        # with open('ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json', 'r') as f:
        #    datastore = json.load(f)

        resp = requests.get('https://data.geo.admin.ch/ch.meteoschweiz.messwerte-sonnenscheindauer-10min/ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json')
        if resp.status_code != 200:
            # This means something went wrong.
            raise resp.ApiError('GET /status/ {}'.format(resp.status_code))
        else:
            datastore = resp.json()

        for station in datastore['features']:
                if station['id'] == self.stationID :
                    #print('Station name:' + station['properties']['station_name'])
                    #print('Value:' + str(station['properties']['value']) )
                    return station['properties']['value']