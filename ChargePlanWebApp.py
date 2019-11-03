######################################################################################
# ChargePlanWebApp.py
# Web application for the usage of ChargePlan
#
######################################################################################


import threading
import ChargePlan
from flask import Flask, render_template

GUIstates = ["NULL", "Initialisierung", "Warten", "Laden", "Fertig", "Fehler"]

app = Flask(__name__)

cp = ChargePlan.ChargePlanEngine()

@app.route("/")
def home():
    global cp
    GUIstate = GUIstates[int(cp.state)]
    GUIdeadline = cp.deadline.strftime("%d.%m. um %H:%M Uhr")
    return render_template("home.html", state=GUIstate, power=cp.power, deadline=GUIdeadline)
    
@app.route("/settings")
def settings():
    return render_template("settings.html")
    
@app.route("/logfile")
def logfile():
    return render_template("logfile.html")

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