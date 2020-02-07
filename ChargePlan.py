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
        STATE_WAITING = 2
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
            self.printToLogfile("No Goal set" )

    
    def getGoal(self):
        return self._goal

    def start(self):

        self.state = ChargePlanState.STATE_INIT

        # main state machine
        while True:
            self.printToLogfile("State: " + str(self.state) )

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
                    weatherSensor = Measurement.Swissmeteo(self.config["measurements"][1]["station"], self.config["measurements"][1]["thresholds"])
                    #weatherSensor = Measurement.SolarLog(self.config["measurements"][0]["url"], self.config["measurements"][0]["username"], self.config["measurements"][0]["password"], self.config["measurements"][0]["thresholds"])

                    #weatherSensorList = list()
                    #for measurement in self.config["measurements"]:
                    #    if measurement["type"] == "Swissmeteo" :
                    #        weatherSensorList.append(Measurement.Swissmeteo(measurement["station"], measurement["thresholds"]))
                    #    elif measurement["type"] == "Solarlog" :
                    #        weatherSensorList.append(Measurement.SolarLog(measurement["url"], measurement["username"], measurement["password"], measurement["thresholds"]))
                    #    else :
                    #        self.printToLogfile("Invalid weatherSensor definition")

                    charger.allowCharging(False)
                    self.deadline = datetime.datetime.now() + datetime.timedelta(days=2)
                    new_state = ChargePlanState.STATE_WAITING
                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                    new_state = ChargePlanState.STATE_INIT

            elif self.state == ChargePlanState.STATE_WAITING :
                #Two reasons for starting charge: enough solar power or deadline reached
                dateObjectNow = datetime.datetime.now()
                try:
                    charger.readStatus()
                    self.printToLogfile("Charger state: " + str(charger.state))
                    self.power = charger.currentPower
                    self.energy = charger.energy
                    try:
                        maxAllowedCurrent = weatherSensor.getMaxAllowedCurrent()
                    except IOError:
                        # probably connection error to sensor
                        self.printToLogfile("WeatherSensor IOError")
                        maxAllowedCurrent = 0
                    if maxAllowedCurrent > 0:
                        self.printToLogfile("Allow charging: getMaxAllowedCurrent: " + str(maxAllowedCurrent))
                        charger.setMaxCurrent(maxAllowedCurrent)
                        charger.allowCharging(True)
                        time.sleep(self.config["timing"]["waitChargingSeconds"])
                        new_state = ChargePlanState.STATE_CHARGING

                    elif self.deadline != None:
                        if  dateObjectNow > self.deadline:
                            # Too late, start charging now
                            self.printToLogfile("Allow charging: too late")
                            charger.setMaxCurrent(self.config["wallbox"]["absolutMaxCurrent"])
                            charger.allowCharging(True)
                            time.sleep(self.config["timing"]["waitChargingSeconds"])
                            new_state = ChargePlanState.STATE_CHARGING

                        else:
                            self.printToLogfile("Don't allow, wait 120s")
                            time.sleep(self.config["timing"]["waitWithoutSunSeconds"])
                            new_state = ChargePlanState.STATE_WAITING
                    else :
                            self.printToLogfile("Don't allow, wait 120s")
                            time.sleep(self.config["timing"]["waitWithoutSunSeconds"])
                            new_state = ChargePlanState.STATE_WAITING

                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                    new_state = ChargePlanState.STATE_WAITING

                
            elif self.state == ChargePlanState.STATE_CHARGING :
                try:
                    charger.readStatus()
                    self.printToLogfile("Charger state: " + str(charger.state))
                    self.power = charger.currentPower
                    self.energy = charger.energy
                    if charger.state == 4 :
                        #charging finished
                        new_state = ChargePlanState.STATE_FINISHED
                    else:
                        dateObjectNow = datetime.datetime.now()
                        try:
                            maxAllowedCurrent = weatherSensor.getMaxAllowedCurrent()
                        except IOError:
                            # probably connection error to sensor
                            self.printToLogfile("WeatherSensor IOError")
                            maxAllowedCurrent = 0
                            
                        if maxAllowedCurrent > 0:
                            self.printToLogfile("Continue charging: getMaxAllowedCurrent: " + str(maxAllowedCurrent))
                            charger.setMaxCurrent(maxAllowedCurrent)
                            time.sleep(self.config["timing"]["waitChargingSeconds"])
                            new_state = ChargePlanState.STATE_CHARGING

                        elif self.deadline != None:
                            if dateObjectNow > self.deadline:
                                charger.setMaxCurrent(self.config["wallbox"]["absolutMaxCurrent"])
                                self.printToLogfile("Continue charging: too late")
                                time.sleep(self.config["timing"]["waitChargingSeconds"])
                                new_state = ChargePlanState.STATE_CHARGING

                            else:
                                #sun gone, stop charging
                                charger.allowCharging(False)
                                self.printToLogfile("Stop charging, wait 120s")
                                time.sleep(self.config["timing"]["waitWithoutSunSeconds"])
                                new_state = ChargePlanState.STATE_WAITING

                        else:
                                #sun gone, stop charging
                                charger.allowCharging(False)
                                self.printToLogfile("Stop charging, wait 120s")
                                time.sleep(self.config["timing"]["waitWithoutSunSeconds"])
                                new_state = ChargePlanState.STATE_WAITING

                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                    new_state = ChargePlanState.STATE_CHARGING


            elif self.state == ChargePlanState.STATE_FINISHED :
                try:
                    charger.readStatus()
                    self.printToLogfile("Charger state: " + str(charger.state))
                    if charger.state == 4 :
                        # If state is 4, the car is full but still connected
                        self.printToLogfile("Charging finished, car still connected")
                        time.sleep(self.config["timing"]["waitAfterFinishedSeconds"])
                    elif charger.state == 1 :
                        # If state isn't 4 anymore, the car has been disconnected
                        self.printToLogfile("Charging finished, car disconnected")
                        time.sleep(self.config["timing"]["waitAfterFinishedSeconds"])
                    elif charger.state == 3  or charger.state == 2 :
                        self.printToLogfile("Car connected")
                        self._goal = None
                        self.deadline = None
                        new_state = ChargePlanState.STATE_WAITING
                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(self.config["timing"]["waitAfterErrorSeconds"])
                    new_state = ChargePlanState.STATE_FINISHED

            elif self.state == ChargePlanState.STATE_ERROR :
                self.printToLogfile("Statemachine stuck in STATE_ERROR")
                time.sleep(self.config["timing"]["waitAfterErrorSeconds"])

            else:
                self.printToLogfile("Error: Invalid state")
                time.sleep(self.config["timing"]["waitAfterFinishedSeconds"])

            self.state = new_state


#If file is called as script, not used as module
if __name__ == "__main__":
    cp = ChargePlanEngine()
    cp.start()