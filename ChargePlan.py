######################################################################################
# ChargePlan.py
# Optimizes the charging of electrical car under an ecological (not financial) point
# of view
#
# First priority: charge only during solar energy production
# Second priority: charge immediately to ensure car is full
#
# Future: grid load dependency (charge when grid is under light load)
######################################################################################

import time
import datetime
from enum import Enum
import json

import Wallbox
import Measurement

class ChargePlanState(Enum):
        STATE_INIT = 1
        STATE_WAITING = 2
        STATE_CHARGING = 3
        STATE_FINISHED = 4
        STATE_ERROR = 5


def printToLogfile(logstring):
    dateObjectNow = datetime.datetime.now()
    timeString = dateObjectNow.isoformat()
    print(timeString + ": " + logstring)

def main():

    #load configuration from JSON file
    with open('config.json') as configFile:
        config = json.load(configFile)

    #Initialize Wallbox
    charger = Wallbox.goEcharger(config["wallbox"]["IP"])
    #charger = Wallbox.goEchargerSimulation(config["wallbox"]["IP"])

    #Initialize Measurement
    weatherSensor = Measurement.Swissmeteo(config["measurement"]["station"])
    
    state = ChargePlanState.STATE_INIT

    printToLogfile("Main initialized")

    # main state machine
    while True:
        printToLogfile("State: " + str(state) )

        if state == ChargePlanState.STATE_INIT :
            try:
                charger.allowCharging(False)
                #Deadline is the latest possible charging start time
                dateObjectNow = datetime.datetime.now()
                dateObjectGoal = dateObjectNow + datetime.timedelta(hours=24) # to be defined in GUI...
                dateObjectDeadline = dateObjectGoal - datetime.timedelta(hours=int(config["timing"]["deadlineHours"]))
                printToLogfile("Deadline: " + str(dateObjectDeadline))
                new_state = ChargePlanState.STATE_WAITING
            except IOError:
                # probably connection error to wallbox, try again
                printToLogfile("Wallbox IOError")
                time.sleep(int(config["timing"]["waitAfterError"]))
                new_state = ChargePlanState.STATE_INIT

        elif state == ChargePlanState.STATE_WAITING :
            #Two reasons for starting charge: enough solar power or deadline reached
            dateObjectNow = datetime.datetime.now()
            if weatherSensor.getSunshineDuration() >= int(config["measurement"]["minSunshineDuration"]):
                printToLogfile("Allow charging: Sunshine >= minSunshineDuration")
                try:
                    charger.allowCharging(True)
                    time.sleep(int(config["timing"]["waitWithSunSeconds"]))
                    new_state = ChargePlanState.STATE_CHARGING
                except IOError:
                    # probably connection error to wallbox, try again
                    printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
                    new_state = ChargePlanState.STATE_WAITING

            elif dateObjectNow > dateObjectDeadline:
                #sofort einschalten
                printToLogfile("Allow charging: too late")
                try:
                    charger.allowCharging(True)
                    new_state = ChargePlanState.STATE_CHARGING
                except IOError:
                    # probably connection error to wallbox, try again
                    printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
                    new_state = ChargePlanState.STATE_WAITING

            else:
                printToLogfile("Don't allow, wait 120s")
                time.sleep(int(config["timing"]["waitWithoutSunSeconds"]))
                new_state = ChargePlanState.STATE_WAITING

            
        elif state == ChargePlanState.STATE_CHARGING :
            charger.readStatus()
            printToLogfile("Charger state: " + str(charger.state))
            if charger.state == 4 :
                #charging finished
                try:
                    charger.allowCharging(False)
                    new_state = ChargePlanState.STATE_FINISHED
                except IOError:
                     # probably connection error to wallbox, try again
                    printToLogfile("Wallbox IOError")
                    time.sleep(int(config["timing"]["waitAfterError"]))
                    new_state = ChargePlanState.STATE_CHARGING

            else:
                dateObjectNow = datetime.datetime.now()
                if weatherSensor.getSunshineDuration() >= int(config["measurement"]["minSunshineDuration"]):
                    printToLogfile("Continue charging: Sunshine >= minSunshineDuration")
                    time.sleep(int(config["timing"]["waitWithSunSeconds"]))
                    new_state = ChargePlanState.STATE_CHARGING
                elif dateObjectNow > dateObjectDeadline:
                    printToLogfile("Continue charging: too late")
                    time.sleep(int(config["timing"]["waitWithSunSeconds"]))
                    new_state = ChargePlanState.STATE_CHARGING
                else:
                    #sun gone, stop charging
                    try:
                        charger.allowCharging(False)
                        printToLogfile("Stop charging, wait 120s")
                        time.sleep(int(config["timing"]["waitWithoutSunSeconds"]))
                        new_state = ChargePlanState.STATE_WAITING
                    except IOError:
                        # probably connection error to wallbox, try again
                        printToLogfile("Wallbox IOError")
                        time.sleep(int(config["timing"]["waitAfterError"]))
                        new_state = ChargePlanState.STATE_CHARGING

        elif state == ChargePlanState.STATE_FINISHED :
            printToLogfile("Charging finished, restart ChargePlan")
            time.sleep(int(config["timing"]["waitAfterFinished"]))

        elif state == ChargePlanState.STATE_ERROR :
            printToLogfile("Statemachine stuck in STATE_ERROR")
            time.sleep(int(config["timing"]["waitAfterError"]))

        else:
            printToLogfile("Error: Invalid state")
            time.sleep(int(config["timing"]["waitAfterFinished"]))

        state = new_state



#If file is called as script, not used as module
if __name__ == "__main__":
    main()