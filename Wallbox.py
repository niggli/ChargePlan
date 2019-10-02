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

    def __init__(self, baseURL):
        #Initialize variables
        self.allowsCharging = False
        self.maxPower = 0
        self.baseURL = baseURL
        self.state = 0 # 0 = undefined, 1 = wallbox ready no car,  2 = charging, 3 = waiting for car, 4 = Finished
        self.kWh = 0
        self.error = 0

    def allowCharging(self, allow):
        if allow == True:
            payload = {'payload': 'alw=1'}
        elif allow == False:
            payload = {'payload': 'alw=0'}
        resp = requests.get(self.baseURL +'/mqtt', params=payload)
        if resp.status_code != 200:
            raise resp.ApiError('GET /status/ {}'.format(resp.status_code))
        else:
            self.allowsCharging = allow


    def setMaxPower(self, maxPower):
        payload = {'payload': 'amp=' + str(maxPower)}
        resp = requests.get(self.baseURL +'/mqtt', params=payload)
        if resp.status_code != 200:
            raise resp.ApiError('GET /status/ {}'.format(resp.status_code))
        else:
            self.maxPower = maxPower

    def readStatus(self):
        #Connect to wallbox and read some stuff
        resp = requests.get(self.baseURL + '/status')
        if resp.status_code != 200:
            # This means something went wrong.
            raise resp.ApiError('GET /status/ {}'.format(resp.status_code))
        else:
            self.maxPower = resp.json()["amp"]
            self.allowsCharging = resp.json()["alw"]
            self.kWh = int(resp.json()["dws"])
            self.error = int(resp.json()["err"])
            self.state = int(resp.json()["car"])


# Wallbox goEchargerSimulation
# can be used if testing the software without a real wallbox
class goEchargerSimulation:

    def __init__(self, baseURL):
        #Initialize variables
        self.allowsCharging = False
        self.maxPower = 0
        self.baseURL = baseURL
        self.state = 0 #enum?
        self.kWh = 0
        self.error = 0

    def allowCharging(self, allow):
        self.allowsCharging = allow


    def setMaxPower(self, maxPower):
        self.maxPower = maxPower

    def readStatus(self):
            self.kWh = self.kWh + 0.5