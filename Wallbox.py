######################################################################################
# Wallbox.py
# Interface to different wallboxes. At the moment:
#
# goEcharger: Connection to go-Echarger via local REST API
# goEchargerSimulation: simulates a go-Echarger for offline testing

######################################################################################

#requests is the defacto standard library for using REST
import requests
import json
from enum import IntEnum

# State of wallbox, PWM signalisation according to type2 definition
class WallboxState(IntEnum):
        STATE_UNDEFINED = 0
        STATE_READY_NO_CAR = 1
        STATE_CHARGING = 2
        STATE_WAITING_FOR_CAR = 3
        STATE_FINISHED_CAR_STILL_CONNECTED = 4


##################################################################################################
# Wallbox goEcharger
##################################################################################################
class goEcharger:

    def __init__(self, baseURL, absolutMaxCurrent):
        #Initialize variables
        self.allowsCharging = False
        self.absolutMaxCurrent = absolutMaxCurrent
        self.maxCurrent = 0
        self.currentPower = 0
        self.baseURL = baseURL
        self.state = WallboxState.STATE_UNDEFINED
        self.energy = 0
        self.error = 0
        self.maxEnergy = 0
        self.limitToMaxEnergy = False

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

    def setMaxEnergy(self, limitToMaxEnergy, maxEnergy):
        if limitToMaxEnergy == True :
            payload = {'payload': 'dwo=' + '{:d}'.format(int(maxEnergy * 10)) + ',stp=2'} #Energy is configured as 0.1 kWh
        else :
            payload = {'payload': 'dwo=0,stp=0'} #Energy is configured as 0.1 kWh
        #Send the data to the wallbox
        try:
            requests.get(self.baseURL +'/mqtt', params=payload)
        except requests.exceptions.RequestException:
            raise IOError

        self.limitToMaxEnergy = limitToMaxEnergy
        self.maxEnergy = maxEnergy

    def readStatus(self):
        #Connect to wallbox and read some stuff
        try:
            resp = requests.get(self.baseURL + '/status')
            self.maxCurrent = resp.json()["amp"]
            self.currentPower = resp.json()["nrg"][11] / 100 # power is returned as 0.01kW
            if resp.json()["alw"] == 0 :
                self.allowsCharging = False
            else :
                self.allowsCharging = True
            self.energy = int(resp.json()["dws"]) / 360000 # Energy is returned as Deka-Watt-Seconds
            self.error = int(resp.json()["err"])
            self.state = WallboxState(int(resp.json()["car"]))
            self.maxEnergy = float(resp.json()["dwo"]) / 10 # Energy is returned as 0.1 kWh
            if resp.json()["stp"] == 0 :
                self.limitToMaxEnergy = False
            else :
                self.limitToMaxEnergy = True
        except requests.exceptions.RequestException: 
            raise IOError
        except json.decoder.JSONDecodeError:
            raise IOError


##################################################################################################
# Wallbox goEchargerSimulation
# can be used if testing the software without a real wallbox
##################################################################################################
class goEchargerSimulation:

    def __init__(self, baseURL, absolutMaxCurrent):
        #Initialize variables
        self.allowsCharging = False
        self.absolutMaxCurrent = absolutMaxCurrent
        self.maxCurrent = 0
        self.currentPower = 0
        self.baseURL = baseURL
        self.state = WallboxState.STATE_CHARGING
        self.energy = 0
        self.error = 0
        self.maxEnergy = 0
        self.limitToMaxEnergy = False

    def allowCharging(self, allow):
        self.allowsCharging = allow

    def setMaxCurrent(self, maxCurrent):
        self.maxCurrent = maxCurrent

    def readStatus(self):
        self.energy = self.energy + 0.5