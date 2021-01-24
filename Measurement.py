######################################################################################
# Measurement.py
# Interface to different solarpower measurement classes. 
######################################################################################

# requests is the defacto standard library for using REST
import requests
# re is used for regex
import re
# attrgetter is used for sorting list
from operator import attrgetter


######################################################################################
# Class Swissmeteo
#
# Interface to the openly available measurement data from the Swissmeteo measurement
# stations. Gets the duration of sunshine in minutes within the last 10 minutes.
######################################################################################
class Swissmeteo:

    def __init__(self, stationID, thresholds):
        self.stationID = stationID
        self.thresholds = thresholds

    def getMaxAllowedCurrent(self):
        try:
            resp = requests.get('https://data.geo.admin.ch/ch.meteoschweiz.messwerte-sonnenscheindauer-10min/ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json', timeout=5)

            datastore = resp.json()

            for station in datastore['features']:
                if station['id'] == self.stationID :
                    print('Station name:' + station['properties']['station_name'])
                    print('Value:' + str(station['properties']['value']) )
                    sunshineduration = station['properties']['value']

            # Sort list so the maximum power is first
            self.thresholds.sort(key=lambda x: x["minSunshineDuration"], reverse=True)
            for threshold in self.thresholds :
                if sunshineduration >= threshold["minSunshineDuration"] :
                    return threshold["chargeCurrentAmpere"]
                    
            # If no threshold is reached, return 0
            return 0

        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            raise IOError


######################################################################################
# Class SolarLog
#
# Interface to the web interface of a Solar-Log installation. Does not use the API as
# this requires a separate licence. Only tested with a certain instance, not
# garanteed to work with every instance/version.
######################################################################################
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
                s.post(self.url, data=payload, timeout=5)

                # An authorised request.
                website = s.get(self.url, timeout=5)
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
            # If no threshold is reached, return 0
            return 0

        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            raise IOError


######################################################################################
# Class Fronius
#
# Interface to a Fronius PV inverter which follows the "Fronius Solar API V1". Targets
# and is tested with a Fronius Symo 3.7-3 S
######################################################################################
class Fronius:

    def __init__(self, baseURL, deviceID, thresholds):
        self.baseURL = baseURL
        self.deviceID = deviceID
        self.thresholds = thresholds

    def getMaxAllowedCurrent(self):
        try:
            payload = {"Scope": "Device", "DeviceID" : str(self.deviceID), "DataCollection" : "CommonInverterData"}
            resp = requests.get(self.baseURL + "/solar_api/v1/GetInverterRealtimeData.cgi", data=payload, timeout=5)

            datastore = resp.json()

            currentPowerkW = datastore['Body']['Data']['PAC']['Value'] / 1000
            print('currentPowerkW:' + str(currentPowerkW))

            # The maximum allowed charging power is dependant on the current solar power.

            # Sort list so the maximum power is first
            self.thresholds.sort(key=lambda x: x["minPowerProductionKW"], reverse=True)
            for threshold in self.thresholds :
                if currentPowerkW >= threshold["minPowerProductionKW"] :
                    return threshold["chargeCurrentAmpere"]
            # If no threshold is reached, return 0
            return 0

        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            raise IOError
