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
        self.deadline = datetime.datetime.now() ##TODO start value?
        self.printToLogfile("Main initialized")

    def printToLogfile(self, logstring):
        dateObjectNow = datetime.datetime.now()
        timeString = dateObjectNow.isoformat()
        print(timeString + ": " + logstring)

    def start(self):
        #load configuration from JSON file
        with open('config.json') as configFile:
            config = json.load(configFile)

        #Initialize Wallbox
        charger = Wallbox.goEcharger(config["wallbox"]["IP"])
        #charger = Wallbox.goEchargerSimulation(config["wallbox"]["IP"])

        #Initialize Measurement
        weatherSensor = Measurement.Swissmeteo(config["measurement"]["station"])

        self.state = ChargePlanState.STATE_INIT

        # main state machine
        while True:
            self.printToLogfile("State: " + str(self.state) )

            if self.state == ChargePlanState.STATE_INIT :
                try:
                    charger.allowCharging(False)
                    #Deadline is the latest possible charging start time
                    dateObjectNow = datetime.datetime.now()
                    dateObjectGoal = dateObjectNow + datetime.timedelta(days=10) # to be defined in GUI...
                    self.deadline = dateObjectGoal - datetime.timedelta(hours=int(config["timing"]["deadlineHours"]))
                    self.printToLogfile("Deadline: " + str(self.deadline))
                    new_state = ChargePlanState.STATE_WAITING
                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
                    new_state = ChargePlanState.STATE_INIT

            elif self.state == ChargePlanState.STATE_WAITING :
                #Two reasons for starting charge: enough solar power or deadline reached
                dateObjectNow = datetime.datetime.now()
                try:
                    charger.readStatus()
                    self.printToLogfile("Charger state: " + str(charger.state))
                    self.power = charger.currentPower
                    self.energy = charger.energy
                    if weatherSensor.getSunshineDuration() >= int(config["measurement"]["minSunshineDuration"]):
                        self.printToLogfile("Allow charging: Sunshine >= minSunshineDuration")
                        charger.allowCharging(True)
                        time.sleep(int(config["timing"]["waitCharging"]))
                        new_state = ChargePlanState.STATE_CHARGING

                    elif dateObjectNow > self.deadline:
                        # Too late, start charging now
                        self.printToLogfile("Allow charging: too late")
                        charger.allowCharging(True)
                        time.sleep(int(config["timing"]["waitCharging"]))
                        new_state = ChargePlanState.STATE_CHARGING

                    else:
                        # Don't actively stop charging so manual activation doesn't get overridden ???
                        self.printToLogfile("Don't allow, wait 120s")
                        time.sleep(int(config["timing"]["waitWithoutSunSeconds"]))
                        new_state = ChargePlanState.STATE_WAITING

                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
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
                        if weatherSensor.getSunshineDuration() >= int(config["measurement"]["minSunshineDuration"]):
                            self.printToLogfile("Continue charging: Sunshine >= minSunshineDuration")
                            time.sleep(int(config["timing"]["waitCharging"]))
                            new_state = ChargePlanState.STATE_CHARGING
                        elif dateObjectNow > self.deadline:
                            self.printToLogfile("Continue charging: too late")
                            time.sleep(int(config["timing"]["waitCharging"]))
                            new_state = ChargePlanState.STATE_CHARGING
                        else:
                            #sun gone, stop charging
                            charger.allowCharging(False)
                            self.printToLogfile("Stop charging, wait 120s")
                            time.sleep(int(config["timing"]["waitWithoutSunSeconds"]))
                            new_state = ChargePlanState.STATE_WAITING

                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
                    new_state = ChargePlanState.STATE_CHARGING


            elif self.state == ChargePlanState.STATE_FINISHED :
                try:
                    charger.readStatus()
                    self.printToLogfile("Charger state: " + str(charger.state))
                    if charger.state == 1 or charger.state == 3 :
                        # If state isn't 4 anymore, the car has been disconnected
                        self.printToLogfile("Charging finished, car disconnected")
                    else:
                        self.printToLogfile("Charging finished, restart ChargePlan")
                    time.sleep(int(config["timing"]["waitAfterFinished"]))
                except IOError:
                    # probably connection error to wallbox, try again
                    self.printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
                    new_state = ChargePlanState.STATE_FINISHED

            elif self.state == ChargePlanState.STATE_ERROR :
                self.printToLogfile("Statemachine stuck in STATE_ERROR")
                time.sleep(int(config["timing"]["waitAfterError"]))

            else:
                self.printToLogfile("Error: Invalid state")
                time.sleep(int(config["timing"]["waitAfterFinished"]))

            self.state = new_state


#If file is called as script, not used as module
if __name__ == "__main__":
    cp = ChargePlanEngine()
    cp.start()