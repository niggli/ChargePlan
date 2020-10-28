# ChargePlan
Optimizes the charging of electrical car under an ecological (not financial) point of view. Currently supports the wallbox "goEcharger" and measurement data from Swissmeteo or SolarLog, but is made to be expanded with more "drivers". The web GUI shows state information and allows control of the functionality. Tested and running on Python 3.5

First priority: charge only during solar energy production
Second priority: charge immediately to ensure car is full

Future:
- grid load dependency (charge when grid is under light load)
- new modules for measurement

Modules
- ChargePlanWebApp.py: Flask based multithreading web application
- ChargePlan.py: Main businesslogic statemachine
- Measurement.py: Classes for measuring the solar energy
- Wallbox.py: Classes for connecting to wallboxes