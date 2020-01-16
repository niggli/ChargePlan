######################################################################################
# Wallbox.py
# Interface to different wallboxes. At the moment:
#
# goEcharger: Connection to go-Echarger via local REST API
# goEchargerSimulation: simulates a go-Echarger for offline testing

######################################################################################

#requests is the defacto standard library for using REST
import requests


# Wallbox goEcharger
class goEcharger:

    def __init__(self, baseURL, absolutMaxCurrent):
        #Initialize variables
        self.allowsCharging = False
        self.absolutMaxCurrent = absolutMaxCurrent
        self.maxCurrent = 0
        self.currentPower = 0
        self.baseURL = baseURL
        self.state = 0 # 0 = undefined, 1 = wallbox ready no car,  2 = charging, 3 = waiting for car, 4 = Finished
        self.energy = 0
        self.error = 0

    def allowCharging(self, allow):
        if allow == True:
            payload = {'payload': 'alw=1'}
        elif allow == False:
            payload = {'payload': 'alw=0'}
        try:
            requests.get(self.baseURL +'/mqtt', params=payload)
        except requests.exceptions.RequestException:
            raise IOError
        self.allowsCharging = allow

    def setMaxCurrent(self, maxCurrent):
        # Don't allow to high currents due to misconfiguration
        if (maxCurrent <= self.absolutMaxCurrent) :
            payload = {'payload': 'amp=' + str(maxCurrent)}
        else:
            payload = {'payload': 'amp=' + str(self.absolutMaxCurrent)}
        try:
            requests.get(self.baseURL +'/mqtt', params=payload)
        except requests.exceptions.RequestException:
            raise IOError
        self.maxCurrent = maxCurrent

    def readStatus(self):
        #Connect to wallbox and read some stuff
        try:
            resp = requests.get(self.baseURL + '/status')
        except requests.exceptions.RequestException: 
            raise IOError
        self.maxCurrent = resp.json()["amp"]
        self.currentPower = resp.json()["nrg"][11] / 100 # power is returned as 0.01kW
        self.allowsCharging = resp.json()["alw"]
        self.energy = int(resp.json()["dws"]) / 360000 # Energy is returned as Deka-Watt-Seconds
        self.error = int(resp.json()["err"])
        self.state = int(resp.json()["car"])


# Wallbox goEchargerSimulation
# can be used if testing the software without a real wallbox
class goEchargerSimulation:

    def __init__(self, baseURL, absolutMaxCurrent):
        #Initialize variables
        self.allowsCharging = False
        self.absolutMaxCurrent = absolutMaxCurrent
        self.maxCurrent = 0
        self.baseURL = baseURL
        self.state = 0 #enum?
        self.kWh = 0
        self.error = 0

    def allowCharging(self, allow):
        self.allowsCharging = allow

    def setMaxCurrent(self, maxCurrent):
        self.maxCurrent = maxCurrent

    def readStatus(self):
        self.kWh = self.kWh + 0.5