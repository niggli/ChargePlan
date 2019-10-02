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

state = ChargePlanState.STATE_INIT


def printToLogfile(logstring):
    dateObjectNow = datetime.datetime.now()
    timeString = dateObjectNow.isoformat()
    print(timeString + ": " + logstring)

def main():
    global state

    #load configuration from JSON file
    with open('config.json') as configFile:
        config = json.load(configFile)
        print(config["measurement"]["station"])

    #Initialize Wallbox
    charger = Wallbox.goEcharger(config["wallbox"]["IP"])
    #charger = Wallbox.goEchargerSimulation(config["wallbox"]["IP"])

    #Initialize Measurement
    weatherSensor = Measurement.Swissmeteo(config["measurement"]["station"])
    
    printToLogfile("Main initialized")

    while True:
        # main state machine
        printToLogfile("State: " + str(state) )

        if state == ChargePlanState.STATE_INIT :
            charger.allowCharging(False)
            #Deadline is the latest possible charging start time
            dateObjectNow = datetime.datetime.now()
            dateObjectGoal = dateObjectNow + datetime.timedelta(days=1) # to be definid in GUI...
            dateObjectDeadline = dateObjectGoal - datetime.timedelta(hours=int(config["timing"]["deadlineHours"]))
            printToLogfile("Deadline: " + str(dateObjectDeadline))

            new_state = ChargePlanState.STATE_WAITING

        elif state == ChargePlanState.STATE_WAITING :
            #Two reasons for starting charge: enough solar power or deadline reached
            dateObjectNow = datetime.datetime.now()
            if weatherSensor.getSunshineDuration() >= int(config["measurement"]["minSunshineDuration"]):
                printToLogfile("Allow charging: Sunshine >= minSunshineDuration")
                charger.allowCharging(True)
                time.sleep(int(config["timing"]["waitWithSunSeconds"]))
                new_state = ChargePlanState.STATE_CHARGING
            elif dateObjectNow > dateObjectDeadline:
                #sofort einschalten
                printToLogfile("Allow charging: too late")
                charger.allowCharging(True)
                new_state = ChargePlanState.STATE_CHARGING
            else:
                printToLogfile("Don't allow, wait 120s")
                time.sleep(int(config["timing"]["waitWithoutSunSeconds"]))
                new_state = ChargePlanState.STATE_WAITING

            
        elif state == ChargePlanState.STATE_CHARGING :
            charger.readStatus()
            print("Charger state: " + str(charger.state))
            if charger.state == 4 :
                #charging finished
                charger.allowCharging(False)
                new_state = ChargePlanState.STATE_FINISHED
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
                    charger.allowCharging(False)
                    printToLogfile("Don't allow, wait 120s")
                    time.sleep(int(config["timing"]["waitWithoutSunSeconds"]))
                    new_state = ChargePlanState.STATE_WAITING

        elif state == ChargePlanState.STATE_FINISHED :
            printToLogfile("Charging finished, restart ChargePlan")
            time.sleep(int(config["timing"]["waitAfterFinished"]))
        else:
            printToLogfile("Error: Invalid state")

        state = new_state




#If file is called as script, not used as module
if __name__ == "__main__":
    main()