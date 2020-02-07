######################################################################################
# ChargePlanWebApp.py
# Web application for the usage of ChargePlan
#
######################################################################################


import threading
import ChargePlan
from flask import Flask, render_template, request

GUIstates = ["NULL", "Initialisierung", "Warten", "Laden", "Fertig", "Fehler"]

app = Flask(__name__)

cp = ChargePlan.ChargePlanEngine()

@app.route("/")
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
    GUIpower = "{:.1f}".format(cp.power)
    GUIenergy = "{:.1f}".format(cp.energy)
    return render_template("home.html", state=GUIstate, power=GUIpower, deadline=GUIdeadline, energy=GUIenergy, goal=GUIgoal)

@app.route("/settings",  methods=["GET", "POST"])
def settings():
    global cp
    # if form is submitted
    if request.method == 'POST':
        if request.form.get('use_goal') == None :
            cp.setNewGoal(None, None)
            return render_template("settings.html", formPosted=True)
        else :
            cp.setNewGoal(request.form.get('goal_date'), request.form.get('goal_time'))
            return render_template("settings.html", formPosted=True)
    else :
        return render_template("settings.html", formPosted=None)
    
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