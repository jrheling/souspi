#!/usr/bin/python

# blinky.py 
#
# playground / PoC for basic GPIO on the RPi

# wiring - instructions in comments below

# references:
# http://makezine.com/projects/tutorial-raspberry-pi-gpio-pins-and-python/
# http://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/



import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

## output, connected to anode (+) side of an LED 
#         (cathode (-) side of resistor to GND) via a 1k resistor
GPIO.setup(23, GPIO.OUT)

## touch switch
##  port's pull-down resistor enabled; other side of switch to 3.3v
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# callback handlers
def handleButtonPress(channel):
    print "pressed"

# utility functions
def timer():
    '''Returns time since last called (float).
    
    NB: this is imprecise to the extent of its own runtime.'''
    if not hasattr(timer, "last"):
        timer.last = time.time()
    r = time.time() - timer.last
    timer.last = time.time()
    return r

# main

print "press button to start"

# debug
print "port 24 is %d" % GPIO.input(24)

## wait for button-press to start
GPIO.wait_for_edge(24, GPIO.RISING)

## now set up a callback to handle future button press
GPIO.add_event_detect(24, GPIO.RISING, callback=handleButtonPress, bouncetime=300)

try:
    while True:
        GPIO.output(23,1)
        print("blink ON (%f)") % timer()
        time.sleep(1)
        GPIO.output(23,0)
        print("blink OFF (%f)") % timer()
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()

GPIO.cleanup()
