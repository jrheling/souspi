#!/usr/bin/python

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

import os
import sys
import tempfile
from w1thermsensor import W1ThermSensor

class TempTrackerError(Exception):
    """ Exception base class. """
    def __str__(self):
        return self.msg

class TempTrackerDirNotWritable(TempTrackerError):
    def __init__(self, dir):
        self.msg = "Directory %s is not writabe" % dir
  
class TempTrackerFileUpdateFailed(TempTrackerError):
    def __init__(self, msg):
        self.msg = msg

class TempTracker(W1ThermSensor):
    """ Track temperature of a DS18B20 in a file. """
    
    def __init__(self, dir, unit=W1ThermSensor.DEGREES_C, fname="temptracker.dat"):
        """docstring for __init__"""
        self._unit = unit
        super(TempTracker, self).__init__()
        self._last_val = None
        self.directory = dir
        self.filename = fname

    @property
    def directory(self):
        return self._directory
    
    @directory.setter
    def directory(self, dir):
        """ Make sure we can write in directory, raise TempTrackerDirNotWritable if not. """
        try:
            (t, tnam) = tempfile.mkstemp(dir=dir)
            os.close(t)
            os.unlink(tnam)
            self._directory = dir
        except OSError:
            raise TempTrackerDirNotWritable(dir)
    
    @property
    def unit(self):
        return self._unit
        
    @unit.setter
    def unit(self, val):
        """ Set unit to one of the options defined in W1thermsensor.
        
            Valid options: DEGREES_C, DEGREES_F, KELVIN 
            Note: raises w1thermsensor.UnsupportedUnitError 
        """
        try:
            self.UNIT_FACTORS[val]
        except KeyError:
            raise self.UnsupportedUnitError()
        self._unit = val
        print "set to %s" % self._unit
        
    def _commit_value(self, val):
        """ Atomically commit new temp value. """
        (tmp_fh, tmp_name) = tempfile.mkstemp(dir=self.directory)
        os.write(tmp_fh,bytes(val))
        os.close(tmp_fh)
        newname = os.path.normpath(self._directory + "/" + self.filename)
        #print "writing %s to %s" % (val, newname)
        try:
            os.rename(tmp_name, newname)
        except OSError, e:
            os.unlink(tmp_name)
            msg = "Failed to update %s: %s" % (newname, e.strerror)
            raise TempTrackerFileUpdateFailed(msg)
        
    def runloop(self):
        """ Loop indefinitely, updating temp value as it changes. """
        while True:
            current_val = self.get_temperature(self.unit)
            if current_val != self._last_val:
                self._commit_value(current_val)
                self._last_val = current_val
    
    
