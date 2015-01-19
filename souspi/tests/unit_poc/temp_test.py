#!/usr/bin/python

# trivial test driver to show operation of DS18B20 sensor on raspi
#

# wiring:
#
# blue / black lead from DS18B20 to GND
# yellow lead (data) from DS18B20 to BCM port #4 on RPi   
#                - also have resistor (~4.7k-10k) to 3.3v
# red led from DS18B20 to 3.3V

# software prereq
# python package w1thermsensor installed

# references
# https://github.com/timofurrer/w1thermsensor
# https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing

import sys
from w1thermsensor import W1ThermSensor

try:
    sensor = W1ThermSensor()
except W1ThermSensor.NoSensorFoundError as e:
    print "Unable to find sensor."
    print "(remember, w1-* modules must be loaded as root before this will work!)"
    sys.exit(1)

temperature_in_fahrenheit = sensor.get_temperature(W1ThermSensor.DEGREES_F)
print "it is %.2f degrees celsius" % sensor.get_temperature(W1ThermSensor.DEGREES_C)
print "it is %.2f degrees fahrenheit" % temperature_in_fahrenheit
