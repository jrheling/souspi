#!/usr/bin/python

# SousPi - a raspberry PI based Sous Vide controller
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
# <FIXME: more pydoc here>
#

import signal
import os
import time
import sys
import ConfigParser
import logging
import tempfile
import threading
import json

import RPi.GPIO as GPIO

from pid_controller import PID
from pid_controller import PID_ATune
from souspi import SousPiStatus
from souspi import *
            
class SousPi(object):

    # pylint: disable=E0202
    #    (pylint 0.25.1 can't handle property assignment from init - see http://www.logilab.org/ticket/89786)
    
    # config defaults FIXME - needs updating
    config_defaults = {
        ## general
        'temperature_file': '"/var/souspi/temptracker.dat"', 
        'setpoint_file': "/var/souspi/spsetpoint",
        ## PID
        'kp': '174.81', 
        'ki': '29.80', 
        'kd': '256.32', 
        ## hardware
        'output_control_port': '23', 
        ## autotune
        'noise_band': '1', 
        'output_step': '50', 
        'lookback_sec': '20', 
        'stable_time_goal': '100',
        'stabilization_output': '600',
        ## pid internals
        'control_window_size': '10', 
        'alarm_interval': '10',
    }
    
    def __init__(self, cfgfile="/etc/souspi.cfg"):
        
        self._init_complete = False
                
        self.p = PID.PID()
        self.status = None  
        
        self._PID_running = False
        self.heater_is_on = False
        self._last_temp_read_time = 0
        self._last_setpoint_read_time = 0
        self._setpoint = None

        ## won't actually do anything until self._init_complete is True
        signal.signal(signal.SIGALRM, self._drive_output)        

        self._window_start = time.time()
        self._on_time = 0.0   # this is the output of the PID, converted to seconds (treating PID output like ms)

        self._last_command_check = time.time() 

        self._config_file = cfgfile
        self._configure()

        try:
            os.unlink(self.start_file)
            os.unlink(self.stop_file)
        except OSError:
            # it's OK if these files don't exist
            pass

        self._get_temp()   # might throw BadTempValueError
        self._setup_raspi()

        # this could raise an exception if the file can't be written
        self.status = SousPiStatus.SousPiStatus(spobj=self, tofile=self.status_file)
        self.status.file_uid = self._file_uid
        self.status.file_gid = self._file_gid
                
        self.status.refresh()
        
        self._init_complete = True

    @property
    def PID_running(self):
        return self._PID_running
        
    @PID_running.setter
    def PID_running(self, arg):
        self._PID_running = arg
        self.status.refresh()

    @property
    def in_water(self):
        if GPIO.input(self._water_sensor_port):
            return True
        return False

    @property
    def last_temp(self):
        return self._current_temp
    
    # def register_UI(self, UI, handle=None):
    #     """ Add a UI. Returns handle, which is generated if not provided. """
    # pass
    #
    # def unregister_UI(self, handle):
    #     """ Remove the UI with the specified handle. """
    # pass
    
    def do_auto_tune(self):
        logging.info("tuning")

        if self.in_water is False:
            logging.error("Refusing to auto-tune in absence of detected water.")
            return

        at = PID_ATune.PID_ATune(self._get_temp, self.p.manual_override)

        # config  
        at.noise_band = self._autotune_noise_band
        at.output_step = self._autotune_output_step
        at.lookback_sec = self._autotune_lookback_sec
        
        ## before we can call the PID's AutoTuner, we need to get in a stable state
        #
        stable = False
        stable_since = None
        stable_time_goal = self._autotune_stable_time_goal  
        
        ## normally, the PID figures out how to drive the heaters in order to hit a target
        #   temp (the "setpoint", or "process variable").  Here, we don't care what the 
        #   temp is, but just that it (and the driver value we call the 'output' here) 
        #   are stable in relation to each other.  So we pick an output and stay with 
        #   it until a temp settles in.
        self.p.manual_override(self._autotune_stabilization_output)    # peg heater output 
        while (not stable) or (time.time() < stable_since + self._autotune_stable_time_goal):
            logging.info("stable: %s" % str(stable))
            if stable:
                logging.debug("%f < %f + %f : %s" % (time.time(), stable_since, 
                                                self._autotune_stable_time_goal, 
                                                str(time.time() < stable_since + 
                                                self._autotune_stable_time_goal)))
            try:
                logging.debug("calling at.verify_stability()")
                at.verify_stability()
            except PID_ATune.PIDNotStableError, e:
                stable = False
                logging.debug("still not stable: %s" % e)
            else:
                if not stable:
                    stable = True
                    logging.debug("**** updating stable_since")
                    stable_since = time.time()
        
        try:
            at.Tune()
        except PID_ATune.PIDNotStableError, e:
            logging.warning("Instability detected in at.Tune(): %s" % e)
            return self.do_auto_tune()   # FIXME - refactor this loop to avoid the need for this
        
        print "values: Kp = %f, Ki = %f, Kd = %f" % (at.Kp, at.Ki, at.Kd)
        # FIXME - should save results, rather than just print to screen ;) 

    def process_commands(self):
        """ Check for command files or setpoint changes. """
        self._last_command_check = time.time()

        # setpoint changes 
        self._update_setpoint()
        
        # start file
        if os.path.isfile(self.start_file):
            self.start()
            os.unlink(self.start_file)  # intentionally don't catch exceptions
        
        # stop file
        if os.path.isfile(self.stop_file):
            self.stop()
            os.unlink(self.stop_file)

    def _start_pump(self):
        """ Turn the water pump on. """
        GPIO.output(self._pump_control_port, 0)
        
    def _stop_pump(self):
        """ Turn the water pump on. """
        GPIO.output(self._pump_control_port, 1)    

    def start(self):
        """ Initiate operations. 
        
            This starts the command and control loops.
            Note: the signal handler is installed at object creation time, but
            doesn't do anything until start() is called. 
        """
        if self.setpoint is None:
            raise SetpointNotSetError("Can't start without defined temperature target.")

        if self.in_water is False:
            logging.error("Not starting in absence of detected water.")
            self.status.refresh()
            return
        else:
            logging.info("Starting PID.")
            self._start_pump()
            self.PID_running = True
    
    def stop(self):
        """ Stop PID control.
        
            Turns off the heaters and stops the PID logic.  
        """
        self._turn_off()
        self._stop_pump()
        self.PID_running = False   
        logging.info("Stopping PID.")
    
    def cleanup(self, signum=None, frame=None): # FIXME - is it desirable to hook this into object destruction?
        """docstring for cleanup"""
        self.alarm_interval = 0         # un-set itimer
        GPIO.cleanup()
        logging.info("Shutting down SousPi instance.")
        try:
            self._datalogf.close()
        except:   ## FIXME lazy 
            pass
    
    @property
    def setpoint(self): 
        return self._setpoint
        
    @setpoint.setter
    def setpoint(self, arg):
        """ Setpoint can be set either via this accessor or by an async update to a control file. 
        
            We always keep the control file current, so that on restart we'll keep the same setpoint. 
            So when updating via the accessor, we need to (atomically) write that file, too.
            
            Raises ImpossibleSetpointError.
        """
        if arg == self._setpoint:
            return
            
        # leave the time un-updated if we're setting to None (which we do from __init__())
        if arg is not None:
            self._last_setpoint_read_time = time.time()      
        
        if arg is None:
            logging.info("Setting setpoint (temp target) to None.")
            self._setpoint = None
            return
        
        try:
            new_setpoint_val = float(arg)
        except ValueError:
            raise ImpossibleSetpointError("Can't convert %s to a float to use as setpoint." % arg)
        
        if new_setpoint_val <= 0:
            raise ImpossibleSetpointError("Setpoint must be positively signed and non-zero")
        
        logging.info("Setting new temp target: %s (was %s)" % (arg, self._setpoint))
        
        try:
            atomic_file_write(self.setpoint_file, arg, self._file_uid, self._file_gid)
        except OSError, e:
            msg = "Failed to update %s: %s" % (self.setpoint_file, e.strerror)
            raise SetpointFileError("did not update setpoint! " + msg)
        
        self._setpoint = arg
        self.p.setpoint = self._setpoint
        if self.status is not None:
            self.status.refresh()

    def _restore_setpoint(self):
        """ Set setpoint at startup based on value in file. 
        
            When we first start, default the setpoint to whatever was in the control file.
        """
        try:
            self._update_setpoint()
        except (TemperatureFileError, SetpointFileError, BadTempValueError) as e:
            """ If there is no file or if its contents are unparseable, that's OK (it'll get replaced
                by the next setpoint update).  
            """
            pass
            

    def _configure(self):
        """ Set up configuration, based on file or hardcoded defaults if no file. """
        cp = ConfigParser.ConfigParser(self.config_defaults)
        cp.read(self._config_file)  
        
        self._set_window_size(cp.getfloat("PID Internals", "control_window_size"))
        self._set_alarm_interval(cp.getfloat("PID Internals", "alarm_interval"))
        self.temperature_file = cp.get("general", "temperature_file")
        self.setpoint_file = cp.get("general", "setpoint_file")

        self.p.Kp = cp.getfloat("PID", "Kp")
        self.p.Ki = cp.getfloat("PID", "Ki")
        self.p.Kd = cp.getfloat("PID", "Kd")
        
        self.p.out_max = self._window_size * 1000
        self.p.out_min = 0
        
        self._file_uid = cp.getint("general", "file_uid")
        self._file_gid = cp.getint("general", "file_gid")
        
        self._output_control_port = cp.getint("hardware", "output_control_port")
        self._water_sensor_port = cp.getint("hardware", "water_sensor_port")
        self._pump_control_port = cp.getint("hardware", "pump_control_port")
        
        self._autotune_noise_band = cp.getfloat("AutoTune", "noise_band")
        self._autotune_output_step = cp.getfloat("AutoTune", "output_step")
        self._autotune_lookback_sec = cp.getfloat("AutoTune", "lookback_sec")
        self._autotune_stable_time_goal  = cp.getfloat("AutoTune", "stable_time_goal")
        self._autotune_stabilization_output = cp.getfloat("AutoTune", "stablization_output")

        self._command_check_interval = cp.getfloat("internal", "command_check_interval")

        self._log_dir = cp.get("general", "log_dir")
        self._debug_log_enabled = cp.getboolean("general", "debug_log_enabled")

        if self._debug_log_enabled:
            datalogf_name = self._log_dir + "/" + ("debug.log-%s" % time.strftime("%Y-%m-%d_%X"))
            self._datalogf = open(datalogf_name, 'w')  
            self._datalog("time, setpoint, self._get_temp(), error, onTime, p, i, d\n")

        self._restore_setpoint()

        self.status_file = cp.get("general", "command_dir") + "/" \
                                    + cp.get("internal", "status_file_name")
        self.start_file = cp.get("general", "command_dir") + "/" \
                                    + cp.get("internal", "start_file_name")
        self.stop_file = cp.get("general", "command_dir") + "/" \
                                    + cp.get("internal", "stop_file_name")


    def _datalog(self, logline):
        if self._debug_log_enabled:
            self._datalogf.write(logline)

    def _setup_raspi(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._output_control_port, GPIO.OUT)
        GPIO.setup(self._water_sensor_port, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self._pump_control_port, GPIO.OUT)
        # pump control pin must be immediately brought high to stay off
        self._stop_pump()
            
    def _drive_output(self, signum, frame):
        """ Called by timer interrupt every alarmIntervalMS
    
            NB: conceptually based on adafruit arduino-based sous-vide controller
        """
        # Power is modulated via a changing duty cycle within the window between
        #   windowStart ... (_window_start + window_size)
        #
        # The output of the PID is stored in _on_time, and indicates how many ms of that
        #  window we'll have the heaters on for.
        #

        # nothing happens until we're all set up -- this is a (potentially non-optimal) way
        #  to handle startup-time ordering of various interrelated bits
        if not self._init_complete:
            return

        # periodically check for new commands or setpoint changes (even if the PID is off)
        if time.time() > self._last_command_check + self._command_check_interval:
            self.process_commands()

        # if the PID controller isn't actually doing anything, we're done
        if not self.PID_running:
            return

        if not self.in_water:
            #logging.ERROR("Turning self off due to lack of detected water.")
            self._turn_off()
            self.PID_running = False
            return

        ##### Remember: time math is in seconds, not ms

        t1 = time.time()
        t2 = (self._window_start + self._on_time)
        if time.time() <= (self._window_start + self._on_time):
            if self._turn_on():
                logging.debug("debugON: time.time() = %f" % t1)
                logging.debug("debugON: (self._window_start + self._on_time) = %f " % t2)
                pass
        else:
            if self._turn_off():
                logging.debug("debugOFF: time.time() = %f" % t1)
                logging.debug("debugOFF: (self._window_start + self._on_time) = %f" % t2)
                pass
        
        if (time.time() + self._alarm_interval) > (self._window_start + self._window_size):
            # it's time to push the window down and refresh the PID
            self._window_start = time.time()

            # we take this opportunity to make sure status is current
            self.status.refresh()
            
            if not self.p.manual_mode:
                logging.debug("(p=%f, i=%d, d=%d)" % (self.p.Cp, self.p.Ci, self.p.Cd))
                logging.debug("calling PID")
            self._on_time = self.p.gen_out(self._get_temp()) / 1000.0
            assert (self._on_time <= 10.0), "PID just produced an impossible output value"

            # log line reference: time, setpoint, current_temp, error, self._on_time, p, i, d
            if self.p.manual_mode:
                logline = "%s, -, -, -, %.3f, -, -, -\n" % (time.time(), self._on_time)
                logging.debug("in manual mode, self._on_time = %f" % self._on_time)
            else:            
                logline = "%s, %.3f, %.3f, %.3f, %.3f, %f, %f, %f\n" % (time.time(), self.setpoint, self._get_temp(), self.setpoint - self._get_temp(), self._on_time, self.p.Cp, self.p.Ci, self.p.Cd)
                logging.debug("error = %.3f, output = %.3f" % (self.setpoint - self._get_temp(), self._on_time))
                logging.debug("(p=%f, i=%d, d=%d)" % (self.p.Cp, self.p.Ci, self.p.Cd))
            self._datalog(logline)        
            
    def _turn_on(self):
        """ Ensure heating element is on.
    
            returns 1 if a change was made
        """
        if (self.in_water is True) and (self.heater_is_on is False):
            logging.debug("turning heater on")
            self.heater_is_on = True
            GPIO.output(self._output_control_port,1)
            return(1)
        return(0)
    
    def _turn_off(self):
        """ Ensure heating element is off.
    
            returns 1 if a change was made 
        """
        if self.heater_is_on:
            logging.debug("turning heater off")
            self.heater_is_on = False
            GPIO.output(self._output_control_port,0)
            return(1)
        return(0)
    
    @staticmethod
    def _read_file_if_newer(fname, last_read):
        """ Utility function to read a file iff it's been changed since we last read it.
        
            Returns a tuple (read_time, file_contents) where:
             * file_contents will be None if the file wasn't read
             * read_time will be unchanged if the file wasn't read (obviously)
             
            Raises OSError if mod time checking failed, and IOError if reading failed (and
            potentially other things in certain failure conditions).  Calls to this method
            should be appropriately wrapped in a 'try'.
        """

        fdata = None
        # if the file hasn't been changed since we last read it, there's no need to open/read            
        if os.path.getmtime(fname) > last_read:
            last_read = time.time()
            try:
                f = open(fname,'r')
                fdata = f.read()
            except IOError as e:
                # just here so we can get the finally
                raise IOError(e)
            else:
                f.close()

        return(last_read, fdata)
    
    def _get_temp(self):
        """ Returns the current temp value (a/k/a PV). 
    
            side effect: updates self._current_temp
    
            We expect the temp to be a single float in a file, e.g. as written by TempTracker.
            Note: raises BadTempValueError if file contents are not formatted as expected. 
        """
        try:
            (self._last_temp_read_time, tdata) = self._read_file_if_newer(self.temperature_file, 
                                                                           self._last_temp_read_time)
        except OSError as e:
            raise TemperatureFileError("Couldn't check modification time of %s: %s" % (self.temperature_file, e.strerror))            
        except IOError as e:
            raise SetpointFileError("Error opening or reading %s: %s" % (self.temperature_file, e.strerror))

        if tdata is not None:            
            # interpret the data in the file
            try:
                tempval = float(tdata)
            except ValueError, e:
                raise BadTempValueError("Couldn't parse temperature from %s: %s" % (self.temperature_file, e.strerror))
            self._current_temp = tempval
        
        return self._current_temp

    def _update_setpoint(self):
        """ Refresh the setpoint value, based on contents of the setpoint file. 
        
            side effect: updates self.setpoint
            
            This is not the only way to change setpoint, since you could update target_temp
            programmatically via the accessors.  But we don't want to miss file-related errors,
            either, so unless self.setpoint_file is None, they will raise SetpointFileError.
            
            Raises TemperatureFileError, SetpointFileError, and BadTempValueError
        """            
        if self.setpoint_file is None:
            return
            
        try:
            (self._last_setpoint_read_time, spdata) = self._read_file_if_newer(self.setpoint_file, 
                                                                               self._last_setpoint_read_time)

        # if the setpoint is None, it might be OK to have no setpoint file - for example, this 
        #   is the case at initial first-time start 
        except OSError as e:
            if self._setpoint is not None:
                raise SetpointFileError("Couldn't check modification time of %s: %s" % (
                    self.setpoint_file, e.strerror))            
            else:
                return
        except IOError as e:
            if self._setpoint is not None:
                raise SetpointFileError("Error opening or reading %s: %s" % (
                    self.setpoint_file, e.strerror))
            else:
                return

        if spdata is not None:
            # interpret the data in the file
            try:
                spval = float(spdata)
            except ValueError, e:
                raise BadTempValueError("Couldn't parse setpoint from %s: %s" % (self.setpoint_file, e.message))
            self.setpoint = spval  


    
    def _set_window_size(self, arg):
        """ The number of seconds within which we control heat output.
        
            A given output level will cause the heaters to be on for some 
            portion of the each window_size seconds.
        """
        newval = None
        if type(arg) in (int, float):
            newval = arg
        elif type(arg) is str:
            ## Try to get a float out of a string
            ## Note: we don't catch ValueError here, since there's nothing
            ##   we can do about it.
            newval = float(arg)
        else:
            raise ValueError("Can't get float out of input:" % arg)
            
        if newval is not None:
            if newval <= 0:
                raise ValueError("window_size must be positive")
            self._window_size = newval

    def _set_alarm_interval(self, arg):
        """ Set the alarm interval, or change it if already set. 
        
            The alarm interval is the time interval (in seconds) on which we'll adjust 
            the output based on PID values.
            
            This implicitly sets the interrupt timer.  If set to 0, the timer is disabled.
        """
        try:
            signal.setitimer(signal.ITIMER_REAL, arg, arg)
        except signal.ItimerError, e:
            raise ValueError("Invalid timer value: %s" % e.strerror)
        self._alarm_interval = arg

    def command_loop(self):  # FIXME get real impl
        """Wait for commands from the UI"""
        print "starting command loop"
        while True:
            raw_input("")  # just sit here
    

