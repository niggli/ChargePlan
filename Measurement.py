######################################################################################
# Measurement.py
# Interface to different solarpower measurement classes. At the moment:
#
# Swissmeteo: gets duration of sunshine in minutes withing the last 10 minutes
######################################################################################

# requests is the defacto standard library for using REST
import requests
# re is used for regex
import re
# attrgetter is used for sorting list
from operator import attrgetter

class Swissmeteo:

    def __init__(self, stationID, thresholds):
        self.stationID = stationID

    def getSunshineDuration(self):
        # For offline testing:
        # with open('ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json', 'r') as f:
        #    datastore = json.load(f)
        try:
            resp = requests.get('https://data.geo.admin.ch/ch.meteoschweiz.messwerte-sonnenscheindauer-10min/ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json')
        except requests.exceptions.RequestException:
            return 0
        
        datastore = resp.json()

        for station in datastore['features']:
                if station['id'] == self.stationID :
                    #print('Station name:' + station['properties']['station_name'])
                    #print('Value:' + str(station['properties']['value']) )
                    return station['properties']['value']

    # def getMaxAllowedPower(self, thresholds):
    #     try:
    #         resp = requests.get('https://data.geo.admin.ch/ch.meteoschweiz.messwerte-sonnenscheindauer-10min/ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json')
    #     except requests.exceptions.RequestException:
    #         raise IOError

    #     ssss
        
    #     datastore = resp.json()

    #     for station in datastore['features']:
    #             if station['id'] == self.stationID :
    #                 #print('Station name:' + station['properties']['station_name'])
    #                 #print('Value:' + str(station['properties']['value']) )
    #                 return station['properties']['value']
    #     # Sort list so the maximum power is first
    #     self.thresholds = sorted(self.thresholds, key=attrgetter("minSunshineDuration"), reverse=True)
    #     for threshold in self.thresholds :
    #         if currentPower >= threshold.minKwProduction :
    #             return threshold.ampereCharge
    #     else :
    #         return 0


class SolarLog:

    def __init__(self, url, username, password, thresholds):
        self.url = url
        self.username = username
        self.password = password
        self.thresholds = thresholds

    def getMaxAllowedCurrent(self):
        #get current power
        try:
            with requests.Session() as s:
                payload = {"username": self.username, "password": self.password, "submit": "Login", "action": "login"}
                s.post(self.url, data=payload)

                # An authorised request.
                website = s.get("https://solvatec.solarlog-web.ch/emulated_main_13343.html")
                powerPatternList = re.findall(r"P<sub>AC</sub>: [0-9]{1,6} W", website.text)
                if len(powerPatternList) > 0 :
                    powerStringList = re.findall(r"[0-9]{1,6}", powerPatternList[0])
                else :
                    powerStringList = ["0"]

            # Convert to number and convert from W to kW
            currentPowerkW = int(powerStringList[0]) / 1000
            print("currentPowerkW: " + str(currentPowerkW))

            # The maximum allowed charging power is dependant on the current solar power. Since we only know
            # about production but not about other consumption, this can often not be a 1 to 1 relationship

            # Sort list so the maximum power is first
            self.thresholds.sort(key=lambda x: x["minPowerProductionKW"], reverse=True)
            for threshold in self.thresholds :
                if currentPowerkW >= threshold["minPowerProductionKW"] :
                    return threshold["chargeCurrentAmpere"]
            else :
                return 0

            

        except requests.exceptions.RequestException:
            return 0



