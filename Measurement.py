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

# Socket, umodbus and struct is used for modbus TCP (Smartfox)
import socket
from umodbus import conf
from umodbus.client import tcp
import struct


######################################################################################
# Class Swissmeteo
#
# Interface to the openly available measurement data from the Swissmeteo measurement
# stations. Gets the duration of sunshine in minutes within the last 10 minutes.
######################################################################################
class Swissmeteo:

    def __init__(self, stationID, modes):
        self.stationID = stationID
        self.modes = modes

    def getMaxAllowedCurrent(self, powerWallbox, modeID):
        try:
            resp = requests.get('https://data.geo.admin.ch/ch.meteoschweiz.messwerte-sonnenscheindauer-10min/ch.meteoschweiz.messwerte-sonnenscheindauer-10min_de.json', timeout=5)

            datastore = resp.json()

            for station in datastore['features']:
                if station['id'] == self.stationID :
                    print('Station name:' + station['properties']['station_name'])
                    print('Value:' + str(station['properties']['value']) )
                    sunshineduration = station['properties']['value']

            # Select correct mode and thresholds
            for mode in self.modes :
                if mode["id"] == modeID :
                    thresholds = mode["thresholds"]

            # Sort list so the maximum power is first
            thresholds.sort(key=lambda x: x["minSunshineDuration"], reverse=True)
            for threshold in thresholds :
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

    def __init__(self, url, username, password, modes):
        self.url = url
        self.username = username
        self.password = password
        self.modes = modes

    def getMaxAllowedCurrent(self, powerWallbox, modeID):
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
            print("currentPowerkW Solarlog: " + str(currentPowerkW))

            # The maximum allowed charging power is dependant on the current solar power. Since we only know
            # about production but not about other consumption, this can often not be a 1 to 1 relationship

            # Select correct mode and thresholds
            for mode in self.modes :
                if mode["id"] == modeID :
                    thresholds = mode["thresholds"]

            # Sort list so the maximum power is first
            thresholds.sort(key=lambda x: x["minPowerProductionKW"], reverse=True)
            for threshold in thresholds :
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

    def __init__(self, baseURL, deviceID, modes):
        self.baseURL = baseURL
        self.deviceID = deviceID
        self.modes = modes

    def getMaxAllowedCurrent(self, powerWallbox, modeID):
        try:

            payload = {"Scope": "Device", "DeviceId" : str(self.deviceID), "DataCollection" : "CommonInverterData"}
            resp = requests.get(self.baseURL + "/solar_api/v1/GetInverterRealtimeData.cgi", params=payload, timeout=5)
            
            datastore = resp.json()

            # If no power is currently produced, the following field is not in the json which will generate an exception
            currentPowerkW = datastore['Body']['Data']['PAC']['Value'] / 1000
            print('currentPowerkW Fronius:' + str(currentPowerkW))

            # The maximum allowed charging power is dependant on the current solar power.

            # Select correct mode and thresholds
            for mode in self.modes :
                if mode["id"] == modeID :
                    thresholds = mode["thresholds"]

            # Sort list so the maximum power is first            

            thresholds.sort(key=lambda x: x["minPowerProductionKW"], reverse=True)
            for threshold in thresholds :
                if currentPowerkW >= threshold["minPowerProductionKW"] :
                    return threshold["chargeCurrentAmpere"]
                    
            # If no threshold is reached, return 0
            return 0

        except :
            raise IOError


######################################################################################
# Class Smartfox
#
# Interface to a Smartfox Pro energy management device.
######################################################################################
class Smartfox:

    def __init__(self, IPaddress, modes):
        self.IPaddress = IPaddress
        self.modes = modes

    def getMaxAllowedCurrent(self, powerWallbox, modeID):

        try:
            # Enable values to be signed (default is False).
            conf.SIGNED_VALUES = False

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.IPaddress, 502))

            # Request the current total power
            message = tcp.read_holding_registers(slave_id=1, starting_address=41017, quantity=2)
            response_totalPower = tcp.send_message(message, sock)

            # Request the current power sent to the analog output
            message = tcp.read_holding_registers(slave_id=1, starting_address=41041, quantity=2)
            response_analogOutPower = tcp.send_message(message, sock)

            sock.close()

            # Convert response of total power in INT32 to a normal number in kW
            temp = struct.pack(">HH", response_totalPower[0], response_totalPower[1])
            totalPowerTuple = struct.unpack(">l", temp)
            totalPowerkW = totalPowerTuple[0] / 1000

            # Convert response of analogout power in UINT32 to a normal number in kW
            temp = struct.pack(">HH", response_analogOutPower[0], response_analogOutPower[1])
            analogOutPowerTuple = struct.unpack(">L", temp)
            analogOutPowerkW = analogOutPowerTuple[0] / 1000

            # Add both powers in the correct way to get the current power produced and available
            currentPowerkW = analogOutPowerkW + ((-1) * totalPowerkW) + powerWallbox
            
            print('currentPowerkW Smartfox:' + str(currentPowerkW))

            # Select correct mode and thresholds
            for mode in self.modes :
                if mode["id"] == modeID :
                    thresholds = mode["thresholds"]
            
            if thresholds != None :
                # Sort list so the maximum power is first
                thresholds.sort(key=lambda x: x["minPowerProductionKW"], reverse=True)
                for threshold in thresholds :
                    if currentPowerkW >= threshold["minPowerProductionKW"] :
                        return threshold["chargeCurrentAmpere"]
                # If no threshold is reached, return 0
                return 0
            else :
                print("Smartfox Error: Mode not found")
                return 0

        except :
            raise IOError

