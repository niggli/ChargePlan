# ChargePlan
Optimizes the charging of electrical car under an ecological (not financial) point of view. Currently supports the wallbox "goEcharger" and measurement data from Smartfox Pro, Swissmeteo, SolarLog and Fronius inverters, but is made to be expanded with more "drivers". The web GUI shows state information and allows control of the functionality. Tested and running on Python 3.8

First priority: charge only during solar energy production
Second priority: charge immediately to ensure car is full

Modules
- ChargePlanWebApp.py: Flask based multithreading web application
- ChargePlan.py: Main businesslogic statemachine
- Measurement.py: Classes for measuring the solar energy
- Wallbox.py: Classes for connecting to wallboxes