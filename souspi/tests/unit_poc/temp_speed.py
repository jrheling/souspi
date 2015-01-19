#!/usr/bin/python

# query temp in tight timed loop
#
# assumes hw setup as in protoSV.py

import RPi.GPIO as GPIO
import time
import sys
from w1thermsensor import W1ThermSensor

## output control
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)

## thermocouple
try:
    sensor = W1ThermSensor()
except W1ThermSensor.NoSensorFoundError as e:
    print "Unable to find sensor."
    print "(remember, w1-* modules must be loaded as root before this will work!)"
    sys.exit(1)

try:
    # slop - just make sure we clean up    
    print "current temp is %f" % sensor.get_temperature(W1ThermSensor.DEGREES_C)

    f = lambda: sensor.get_temperature(W1ThermSensor.DEGREES_C)
    
    n = 10
    runtimes = []
    print "getting temp 10 times, as fast as possible"
    for i in range(0,n):
        start_t = time.time()
        f()
        end_t = time.time()
        runtimes.append(end_t - start_t)
    print "fastest runtime: %f" % min(runtimes)
    print "slowest runtime: %f" % max(runtimes)
    print "average runtime: %f" % (sum(runtimes) / float(len(runtimes)))
    
except:
    raise
finally:
    GPIO.cleanup()
