######################################################################################
# ChargePlan.py
# Main statemachine for chargeplan. Can be used as script or within ChargePlanWebApp
# as a web application.
######################################################################################

import time
import datetime
from enum import IntEnum
import json

import Wallbox
import Measurement


class ChargePlanState(IntEnum):
        STATE_INIT = 1
        STATE_NO_CAR = 2
        STATE_CHARGING = 3
        STATE_FINISHED = 4
        STATE_ERROR = 5

class ChargePlanEngine:

    def __init__(self):
        self.state = ChargePlanState.STATE_INIT
        self.power = 0
        self.energy = 0
        self._goal = None
        self.deadline = None
        self.config = None
        self.allowCharging = False # internal state, not the same as the Wallbox state which can change through the Wallbox itself
        self.maxEnergy = 0
        self.limitToMaxEnergy = False
        self.mode = 1

        self.printToLogfile("Main initialized")

    def printToLogfile(self, logstring):
        dateObjectNow = datetime.datetime.now()
        timeString = dateObjectNow.isoformat()
        print(timeString + ": " + logstring)

    def setNewGoal(self, dateString, timeString):
        if dateString != None and timeString != None :
            #try to convert strings to datetime object
            try :
                datetimeString = dateString + " " + timeString
                self._goal = datetime.datetime.strptime(datetimeString, "%d.%m.%Y %H:%M")
                #Deadline is the latest possible charging start time
                self.deadline = self._goal - datetime.timedelta(hours=self.config["timing"]["deadlineHours"])
                self.printToLogfile("Goal: " + str(self._goal))
                self.printToLogfile("Deadline: " + str(self.deadline))
            except ValueError:
                #possibly because of usage of mobile device with date picker, which returns YYYY-MM-DD
                try :
                    datetimeString = dateString + " " + timeString
                    self._goal = datetime.datetime.strptime(datetimeString, "%Y-%m-%d %H:%M")
                    #Deadline is the latest possible charging start time
                    self.deadline = self._goal - datetime.timedelta(hours=self.config["timing"]["deadlineHours"])
                    self.printToLogfile("Goal: " + str(self._goal))
                    self.printToLogfile("Deadline: " + str(self.deadline))
                except ValueError:
                    # Typerror is raised if both arguments are None
                    self._goal = None
                    self.deadline = None
                    self.printToLogfile("ValueError, no Goal. dateString: " + dateString + " timeString: " + timeString)
        else :
            self._goal = None
            self.deadline = None
            self.printToLogfile("No Goal set")

    def setMaxEnergy(self, limitToMaxEnergy, maxEnergy):
        #Only store data, don't send to wallbox directly
        if limitToMaxEnergy == True :
            self.limitToMaxEnergy = True
            self.maxEnergy = maxEnergy
            self.printToLogfile("Energy limit set: " + str(maxEnergy) + " kWh")
        else :
            self.limitToMaxEnergy = False
            self.maxEnergy = 0
            self.printToLogfile("No energy limit set" )

    def setMode(self, mode):
        #Only store data, don't send to wallbox directly
        self.mode = mode
        self.printToLogfile("Mode set: " + str(mode))

    
    def getGoal(self):
        return self._goal

    def start(self):

        self.state = ChargePlanState.STATE_INIT

        # main state machine
        while True:
            self.printToLogfile("State: " + str(self.state) )

##################################################################################################
# STATE_INIT
##################################################################################################
            if self.state == ChargePlanState.STATE_INIT :
                try:
                    # load configuration from JSON file
                    with open('config.json') as configFile:
                        self.config = json.load(configFile)

                    # Initialize Wallbox
                    charger = Wallbox.goEcharger(self.config["wallbox"]["IP"], self.config["wallbox"]["absolutMaxCurrent"])
                    
                    # Uncomment this to use wallbox simulator for developing
                    #charger = Wallbox.goEchargerSimulation(self.config["wallbox"]["IP"], self.config["wallbox"]["absolutMaxCurrent"])

                    # Initialize Measurement
                    weatherSensorList = list()
                    for measurement in self.config["measurements"]:
                        if measurement["type"] == "Swissmeteo" :
                            weatherSensorList.append(Measurement.Swissmeteo(measurement["station"], measurement["modes"]))
                        elif measurement["type"] == "Solarlog" :
                            weatherSensorList.append(Measurement.SolarLog(measurement["url"], measurement["username"], measurement["password"], measurement["modes"]))
                        elif measurement["type"] == "Fronius" :
                            weatherSensorList.append(Measurement.Fronius(measurement["url"], measurement["deviceID"], measurement["modes"]))
                        elif measurement["type"] == "Smartfox" :
                            weatherSensorList.append(Measurement.Smartfox(measurement["ip"], measurement["modes"]))
                        else :
                            self.printToLogfile("Invalid weatherSensor definition")

                    charger.allowCharging(False)
                    self.allowCharging = False # internal state
                    new_state = ChargePlanState.STATE_NO_CAR
                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                    new_state = ChargePlanState.STATE_INIT

##################################################################################################
# STATE_NO_CAR
##################################################################################################
            elif self.state == ChargePlanState.STATE_NO_CAR :
                try:
                    charger.readStatus()
                    self.printToLogfile("Charger state: " + str(charger.state))
                    if charger.state == Wallbox.WallboxState.STATE_READY_NO_CAR :
                        self.printToLogfile("Still no car connected, wait.")
                        time.sleep(self.config["timing"]["waitWithoutCarSeconds"])
                    elif (charger.state == Wallbox.WallboxState.STATE_WAITING_FOR_CAR) or (charger.state == Wallbox.WallboxState.STATE_CHARGING):
                        self.printToLogfile("Car connected.")
                        self._goal = None
                        self.deadline = None
                        self.maxEnergy = 0
                        self.limitToMaxEnergy = False
                        new_state = ChargePlanState.STATE_CHARGING
                    elif charger.state == Wallbox.WallboxState.STATE_FINISHED_CAR_STILL_CONNECTED :
                        if self.allowCharging == False :
                            self.printToLogfile("Car connected but probably not really finished")
                            new_state = ChargePlanState.STATE_CHARGING
                        else : 
                            self.printToLogfile("Car connected but already finished")
                            new_state = ChargePlanState.STATE_FINISHED
                    IOerror_count = 0
                except IOError:
                    # probably connection error to wallbox, try again
                    IOerror_count = IOerror_count + 1
                    self.printToLogfile("Wallbox IOError")
                    # if error count is too high, re-init everything
                    if (IOerror_count > self.config["timing"]["connectionMaxRetrys"]) :
                        new_state = ChargePlanState.STATE_INIT
                    else :
                        time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                        new_state = ChargePlanState.STATE_NO_CAR

##################################################################################################
# STATE_CHARGING
##################################################################################################                
            elif self.state == ChargePlanState.STATE_CHARGING :
                try:
                    charger.readStatus()
                    self.printToLogfile("Wallbox state: " + str(charger.state))
                    self.power = charger.currentPower
                    self.energy = charger.energy

                    # check state of car and decide on consequences
                    if charger.state == Wallbox.WallboxState.STATE_READY_NO_CAR :
                        # car disconnected
                        new_state = ChargePlanState.STATE_FINISHED
                    elif charger.state == Wallbox.WallboxState.STATE_FINISHED_CAR_STILL_CONNECTED :
                        if self.allowCharging == True :
                            # Car says it's finished during charging, so battery is full
                            new_state = ChargePlanState.STATE_FINISHED
                        else :
                            # Car says it's finished when charging is not allowed, so battery is NOT full.
                            new_state = ChargePlanState.STATE_CHARGING
                    else:
                        new_state = ChargePlanState.STATE_CHARGING

                    # take further actions if state should not be left
                    if new_state == ChargePlanState.STATE_CHARGING :
                        dateObjectNow = datetime.datetime.now()

                        # Get maximum current from weather sensors. If multiple sensors are configured,
                        # try all of them but stop as soon as one of them returns a valid value
                        maxAllowedCurrent = None
                        for weatherSensor in weatherSensorList:
                            if maxAllowedCurrent == None:
                                try:
                                    maxAllowedCurrent = weatherSensor.getMaxAllowedCurrent(self.power, self.mode)
                                except IOError:
                                    # probably connection error to sensor
                                    self.printToLogfile("WeatherSensor IOError: " + str(weatherSensor))
                        
                        # Check returned value from weather sensors and react
                        if maxAllowedCurrent == None:
                            self.printToLogfile("No weathersensor has returned a value.")
                            maxAllowedCurrent = 0
                            time.sleep(self.config["timing"]["waitWithoutSunSeconds"])
                            new_state = ChargePlanState.STATE_CHARGING
                        else:
                            # Check if deadline is reached
                            if self.deadline != None:
                                if dateObjectNow > self.deadline:
                                    deadlineReached = True
                                else:
                                    deadlineReached = False
                            else:
                                deadlineReached = False

                            # Decide on charging depending on deadline and measurements
                            if deadlineReached:
                                    # Deadline reached, charge
                                    charger.allowCharging(True)
                                    self.allowCharging = True # internal state
                                    self.printToLogfile("Charge: deadline reached. Power: " + str(self.power))
                                    charger.setMaxCurrent(self.config["wallbox"]["absolutMaxCurrent"])
                                    charger.setMaxEnergy(self.limitToMaxEnergy, self.maxEnergy)
                                    time.sleep(self.config["timing"]["waitChargingSeconds"])
                                    new_state = ChargePlanState.STATE_CHARGING
                            else :
                                if maxAllowedCurrent > 0:
                                    charger.allowCharging(True)
                                    self.allowCharging = True # internal state
                                    charger.setMaxCurrent(maxAllowedCurrent)
                                    charger.setMaxEnergy(self.limitToMaxEnergy, self.maxEnergy)
                                    self.printToLogfile("Charge: getMaxAllowedCurrent: " + str(maxAllowedCurrent) + " power: " + str(self.power))
                                    time.sleep(self.config["timing"]["waitChargingSeconds"])
                                    new_state = ChargePlanState.STATE_CHARGING
                                else:
                                    charger.allowCharging(False)
                                    self.allowCharging = False # internal state
                                    self.printToLogfile("No sun, don't charge, wait.")
                                    time.sleep(self.config["timing"]["waitWithoutSunSeconds"])
                                    new_state = ChargePlanState.STATE_CHARGING
                    IOerror_count = 0
                except IOError:
                    # probably connection error to wallbox, try again
                    IOerror_count = IOerror_count + 1
                    self.printToLogfile("Wallbox IOError")
                    # if error count is too high, re-init everything
                    if (IOerror_count > self.config["timing"]["connectionMaxRetrys"]) :
                        new_state = ChargePlanState.STATE_INIT
                    else :
                        time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                        new_state = ChargePlanState.STATE_CHARGING

##################################################################################################
# STATE_FINISHED
##################################################################################################  
            elif self.state == ChargePlanState.STATE_FINISHED :
                try:
                    charger.readStatus()
                    charger.setMaxCurrent(self.config["wallbox"]["absolutMaxCurrent"])
                    self.printToLogfile("Charger state: " + str(charger.state))
                    if charger.state == Wallbox.WallboxState.STATE_FINISHED_CAR_STILL_CONNECTED :
                        self.printToLogfile("Charging finished, car still connected")
                        time.sleep(self.config["timing"]["waitAfterFinishedSeconds"])
                    elif charger.state == Wallbox.WallboxState.STATE_READY_NO_CAR :
                        charger.allowCharging(False)
                        self.allowCharging = False # internal state
                        self.printToLogfile("Charging finished, car disconnected")
                        new_state = ChargePlanState.STATE_NO_CAR
                        time.sleep(self.config["timing"]["waitWithoutCarSeconds"])
                    elif charger.state == Wallbox.WallboxState.STATE_WAITING_FOR_CAR  or charger.state == Wallbox.WallboxState.STATE_CHARGING :
                        self.printToLogfile("Car starts charging again, probably pre-Heat")
                        new_state = ChargePlanState.STATE_FINISHED
                        time.sleep(self.config["timing"]["waitAfterFinishedSeconds"])
                    IOerror_count = 0
                except IOError:
                    # probably connection error to wallbox, try again
                    IOerror_count = IOerror_count + 1
                    self.printToLogfile("Wallbox IOError")
                    # if error count is too high, re-init everything
                    if (IOerror_count > self.config["timing"]["connectionMaxRetrys"]) :
                        new_state = ChargePlanState.STATE_INIT
                    else :
                        time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                        new_state = ChargePlanState.STATE_FINISHED

##################################################################################################
# STATE_ERROR
##################################################################################################  
            elif self.state == ChargePlanState.STATE_ERROR :
                self.printToLogfile("Statemachine stuck in STATE_ERROR")
                time.sleep(self.config["timing"]["waitAfterErrorSeconds"])

##################################################################################################
# Undefined states
##################################################################################################
            else:
                self.printToLogfile("Error: Invalid state")
                time.sleep(self.config["timing"]["waitAfterFinishedSeconds"])

            self.state = new_state


#If file is called as script, not used as module
if __name__ == "__main__":
    cp = ChargePlanEngine()
    cp.start()