######################################################################################
# ChargePlanWebApp.py
# Web application for the usage of ChargePlan
#
######################################################################################


import threading
import ChargePlan
import datetime
import json
from flask import Flask, render_template, request

# This enum must correlate to the class ChargePlanState
GUIstates = ["NULL", "Initialisierung", "Kein Auto", "Auto verbunden", "Fertig", "Fehler"]

app = Flask(__name__)

cp = ChargePlan.ChargePlanEngine()

# load configuration from JSON file
with open('config.json') as configFile:
    config = json.load(configFile)

@app.route("/",  methods=["GET", "POST"])
def home():
    global cp
    # load data and show webpage
    GUIstate = GUIstates[int(cp.state)]
    if cp.getGoal() != None :
        GUIdeadline = cp.deadline.strftime("%d.%m. um %H:%M Uhr")
        GUIgoal = cp.getGoal().strftime("%d.%m. um %H:%M Uhr")
    else:
        GUIdeadline = None
        GUIgoal = None
    if cp.state == ChargePlan.ChargePlanState.STATE_CHARGING:
        if cp.allowCharging == True:
            GUIallowCharging = ", freigegeben"
        else:
            GUIallowCharging = ", gesperrt"
    else :
        GUIallowCharging = None

    GUImode = config["modes"][cp.mode - 1]["name"] #-1 to convert from ID to list index
    GUIpower = "{:.1f}".format(cp.power)
    GUIenergy = "{:.1f}".format(cp.energy)
    GUIlimitToMaxEnergy = cp.limitToMaxEnergy
    GUImaxenergy = "{:.0f}".format(cp.maxEnergy / config["cars"][0]["batterysizekWh"] * 100)
    GUImaxenergykwh = "{:.1f}".format(cp.maxEnergy)
    return render_template("home.html", state=GUIstate, allowCharging=GUIallowCharging, power=GUIpower, deadline=GUIdeadline, energy=GUIenergy, goal=GUIgoal, limitmaxenergy=GUIlimitToMaxEnergy, maxenergy=GUImaxenergy, maxenergykwh=GUImaxenergykwh, mode=GUImode)

@app.route("/settings",  methods=["GET", "POST"])
def settings():
    global cp
    # if form is submitted   
    if request.method == 'POST':
        # if "Charge now" button is clicked
        if request.form.get('chargeInstantly') != None :
            cp.setMaxEnergy(False, 0)
            dateObjectNow = datetime.datetime.now()
            cp.setNewGoal(dateObjectNow.date().strftime("%d.%m.%Y"), dateObjectNow.time().strftime("%H:%M"))
        else :
            try:
                limit = float(request.form.get('limit'))
                limit = limit * config["cars"][0]["batterysizekWh"] / 100
                limit = round(limit, 1)
            except ValueError:
                limit = 0

            # translate from "on" to "True"
            if request.form.get('use_limit') == "on" :
                cp.setMaxEnergy(True, limit)
            else :
                cp.setMaxEnergy(False, limit)

            if request.form.get('use_goal') == None :
                cp.setNewGoal(None, None)
            else :
                cp.setNewGoal(request.form.get('goal_date'), request.form.get('goal_time'))

            if request.form.get('mode') != None :
                cp.setMode(int(request.form.get('mode')))
            
        return render_template("settings.html", formPosted=True)
    else : #Form not posted
        GUIModeList = config["modes"]
        GUINumberOfModes = len(GUIModeList)
        GUImodeSelected = cp.mode
        return render_template("settings.html", formPosted=None, modeList=GUIModeList, numberOfModes=GUINumberOfModes, modeSelected=GUImodeSelected)

class ChargePlanThread(threading.Thread):
    def run(self):
        global cp
        cp.start()

if __name__ == "__main__":
    t = ChargePlanThread()
    t.start()

    # Flask must run in main thread to support debug mode and reloader

    #use for application in network. ##TODO make IP adress configurable
    app.run(host='192.168.178.23', debug=False)

    #use for local debugging
    #app.run(debug=False)