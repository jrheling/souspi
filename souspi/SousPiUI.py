#
# Copyright 2014-2015 Joshua Heling <jrh@netfluvia.org>
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

import time

import ConfigParser

import SousPiStatus
from souspi import *

class SousPiUIBase(object):
    
    def __init__(self, cfgfile="/etc/souspi.cfg"):
        """docstring for __init__"""
        
        cp = ConfigParser.ConfigParser()
        cp.read(cfgfile)  
        self.setpoint_file = cp.get("general", "setpoint_file")
        self.cmd_start_file = cp.get("general", "command_dir") + "/" \
                                    + cp.get("internal", "start_file_name")
        self.cmd_stop_file = cp.get("general", "command_dir") + "/" \
                                    + cp.get("internal", "stop_file_name")
                                    
        self.status_file = cp.get("general", "command_dir") + "/" \
                                    + cp.get("internal", "status_file_name")

        self._command_check_interval = cp.getfloat("internal", "command_check_interval")
        self.at_temp_threshold = cp.getfloat("PID", "at_temp_threshold")
        # this could raise an exception if the file is missing / bad
        try:
            self.status = SousPiStatus.SousPiStatus(fromfile=self.status_file)
        except StatusFileError, e:
            # make an empty status object, then hook up the fromfile so that if/when things
            #  are functional later it will work upon refresh
            self.status = SousPiStatus.SousPiStatus()
            self.status.fromfile = self.status_file
            self.status.error = True
    
    def change_setpoint(self, arg):
        """ Change the setpoint of the connected SousPi controller.
        
            This is done by updating the control file shared with the controller.
        """
        try:
            atomic_file_write(self.setpoint_file, arg)
        except OSError, e:
            msg = "Failed to update %s: %s" % (self.setpoint_file, e.strerror)
            raise SetpointFileError("did not update setpoint! " + msg)
        else:
            time.sleep(self._command_check_interval)  # same rationale as in start()
            
    def start(self):
        atomic_file_write(self.cmd_start_file, None)
        ## it might take the controller this long to pick up on our change.  Waiting here is better than confusing 
        ##   the user with what would look like a failed change that later worked.
        time.sleep(self._command_check_interval)
    
    def stop(self):
        atomic_file_write(self.cmd_stop_file, None)
        time.sleep(self._command_check_interval)  # same rationale as in start()
        
    # here to remind subclasses that they should implement this
    def runloop(self):
        # runloop should include calls to self.status.refresh() before getting new values
        pass
    
class SousPiCLI(SousPiUIBase):
    """ Simple command-line interface for a terminal.
    
        This is not really useful for more than testing / reference.
    """
    def runloop(self):
        while True:
            self.status.refresh()
            # print status
            no_setpoint = False
            if self.status.setpoint is None:
                no_setpoint = True
                print "(setpoint not set) Current temp: %.2f" % self.status.temp
                print "[s] to set setpoint, [enter] to refresh"
            else:
                print "(%s) Current temp: %.2f / Setpoint: %.2f" % (
                            "running" if self.status.running else "not running",
                            self.status.temp, self.status.setpoint)
                print "[x] to turn %s, [s] to change setpoint, [enter] to refresh" % (
                            "off" if self.status.running else "on")
            c = raw_input("") 
            if c.lower() == 'x':              # toggle PID on/off
                if no_setpoint:
                    continue
                if self.status.running:
                    self.stop()
                else:
                    self.start()
            elif c.lower() == 's':            # try to change/set setpoint
                sp = raw_input("enter%s setpoint: " % ("" if no_setpoint else " new"))
                try:
                    newsp = float(sp)
                    assert(newsp > 0.0)
                    self.change_setpoint(newsp)
                except (ValueError, AssertionError, ImpossibleSetpointError):
                    print "setpoint must be positive number - try again"
                    continue                    
            else:
                continue   

class SousPiWebUI(SousPiUIBase):
    """ Core logic to be wrapped by a simple Flask app. """
    @property
    def current_status(self):
        self.status.refresh()
        return self.status
    
