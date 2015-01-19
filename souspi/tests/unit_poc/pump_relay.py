#!/usr/bin/python

# wiring:
#
# relay board, with control line connected to port 25
#
# expected behavior - relay is off before this runs, and stays off after it starts, then
#   turns on three times for 0.5s each, with 1s in between

import sys
import time
import RPi.GPIO as GPIO

relay = 25

GPIO.setmode(GPIO.BCM)

GPIO.setup(relay, GPIO.OUT)
GPIO.output(relay,1)

def on():
    print "on"
    GPIO.output(relay,0)

def off():
    print "off"
    GPIO.output(relay,1)

def loop(num):
    i = 0
    while (i < num):
        on()
        time.sleep(0.5)
        off()
        time.sleep(1)
        i += 1
    
if __name__ == "__main__":
    loop(3)