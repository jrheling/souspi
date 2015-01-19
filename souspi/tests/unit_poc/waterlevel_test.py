#!/usr/bin/python

# trivial test driver to show operation of DS18B20 sensor on raspi
#

# wiring:
#
# water level sensor to 5v and a raspi port configured for GPIO input with the
#  pull-down resistor enabled 
#
# sensor consists of a brass tube soldered to one lead and an insulated 18ga solid
#  wire in the tube, with a small bit of the wire exposed ~1/8" past the end of 
#  the tube.
#
# will light an LED when water is detected (also print to screen)

import sys
import time
import RPi.GPIO as GPIO

led = 23
waterlevel = 24

GPIO.setmode(GPIO.BCM)

# sensor value -- HIGH means water detected
GPIO.setup(waterlevel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

## output, connected to anode (+) side of an LED
#         (cathode (-) side of resistor to GND) via a 1k resistor
GPIO.setup(led, GPIO.OUT)

GPIO.output(led,0)
print "initial sensor reading is %d" % GPIO.input(waterlevel)

while True:
    if GPIO.input(waterlevel) == 1:
        print "water detected"
        GPIO.output(led,1)
    else:
        print "no water detected"
        GPIO.output(led,0)
    time.sleep(1)

    # GPIO.wait_for_edge(waterlevel, GPIO.FALLING)
    # print "water detected"
    # GPIO.output(led, 1)
    # time.sleep(0.5)
    #
    # GPIO.wait_for_edge(waterlevel, GPIO.RISING)
    # print "no water detected"
    # GPIO.output(led, 0)
    # time.sleep(0.5)

