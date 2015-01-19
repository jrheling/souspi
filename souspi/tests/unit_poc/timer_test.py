#!/usr/bin/python

import signal
from time import sleep

def handleALRM(signum, frame):
    if not hasattr(handleALRM, "count"):
        handleALRM.count = 0
    handleALRM.count += 1
    # print every 2s
    if (handleALRM.count % 40) == 0:
        print "two seconds have passed"


def prompt():
    raw_input("press enter")


## send a SIGALRM every 250 ms
signal.setitimer(signal.ITIMER_REAL, 0.05, 0.05)

signal.signal(signal.SIGALRM, handleALRM)

prompt()
print "foo"
prompt()
print "bar"
prompt()
print "baz"

# disable the signal
signal.setitimer(signal.ITIMER_REAL, 0)