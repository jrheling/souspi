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

class SousPiStatus(object):
    """ Provides read-only access to key properties of a SousPi instance. 
    
        From the controller, we write the status json via the class.  In this case spobj 
        and tofile are needed.
        
        From the client/UI side, we use the class to read the file and get a status object.
        In this case, spobj and tofile are meaningless, but fromfile is required.
    """
    
    status_items = ("temp", "setpoint", "running", "in_water", "time_at_setpoint", "PID_p", "PID_i", "PID_d", "error")

    def __init__(self, spobj=None, tofile=None, fromfile=None):
        self._sp = spobj
        self.fromfile = fromfile
        self.tofile = tofile
        
        self.file_uid = None
        self.file_gid = None
        
        self.error = False
        
        if self._sp is not None:
            self._refresh_from_obj()
        elif self.fromfile is not None:
            # might raise StatusFileError - we're letting that propagate on purpose
            self.from_JSON()
        else:
            # debug mock for dev purposes # FIXME REMOVE
            self.temp = 26.3
            self.setpoint = 32.0
            self.running = False
            self.in_water = False
            #self.time_at_setpoint = FIXME - IMPLEMENT
            self.time_at_setpoint = None # FIXME along with above line
            self.PID_p = 174.81
            self.PID_i = 29.80
            self.PID_d = 256.32
    
    def _refresh_from_obj(self):
        """ Update status attributes based on attached SousPi object. """
        # Improve: this might be better done on the fly via accessor methods.  Need to think 
        #  about the implications of that on the case where we're reading status rather than 
        #  writing it.  (Maybe those cases should be handled by separate classes?)
        if self._sp is not None:
            self.temp = self._sp.last_temp
            self.setpoint = self._sp.setpoint
            self.running = self._sp.PID_running
            self.in_water = self._sp.in_water
            #self.time_at_setpoint = FIXME - IMPLEMENT
            self.time_at_setpoint = None # FIXME along with above line
            self.PID_p = self._sp.p.Kp
            self.PID_i = self._sp.p.Ki
            self.PID_d = self._sp.p.Kd
    
    @staticmethod
    def _as_value_object(obj):
        """ Returns object with the serializable subset of attributes appropriate for JSONification. """
        dict = {}
        for i in obj.status_items:
            dict[i] = getattr(obj,i)
        return dict
    
    def to_JSON(self):
        return json.dumps(self, default=self._as_value_object, sort_keys=True, indent=4)
    
    def write_status_file(self):
        self._refresh_from_obj()
        atomic_file_write(self.tofile, self.to_JSON(), self.file_uid, self.file_gid)

    def refresh(self):
        """ Get the most current data into the status object/file. 
        
            If we're tied to an object (i.e. when SousPiStatus is connected to a controller), update 
            the fields from correspdonding object properties and write a fresh status file.  If
            we're getting data from a file (i.e. we're a UI), update the object from the file.
            
            On error, status values are all set to None and the 'error' member to True.
        """
        if self._sp is not None:
            self._refresh_from_obj()
            self.write_status_file()
        elif self.fromfile is not None:
            try:
                self.from_JSON()
            except StatusFileError, e:
                for i in self.status_items:   # status read failed, so current status vals are wrong
                    setattr(self, i, None)
                self.error = True
            else:
                if self.error:
                    self.error = False
        
    def from_JSON(self):
        """ Read status from fromfile, setting missing values to None. """
        status_vals = None
        try:
            fromfp = open(self.fromfile,"r")
        except IOError, e:
            logging.error("Couldn't read status file %s: %s" % (self.fromfile, e.strerror))
            raise StatusFileError("Couldn't read status from file %s: %s" % (self.fromfile, e.strerror))
        else:
            try:
                status_vals = json.load(fromfp)
            except ValueError, e:
                logging.error("Couldn't parse JSON from status file %s: %s" % (self.fromfile, e.message))
                raise StatusFileError("No status object in file %s" % self.fromfile)
            finally:
                fromfp.close()
            
        if status_vals is not None:
            for i in self.status_items:
                if status_vals.has_key(i):
                    setattr(self, i, status_vals[i])
                else:
                    setattr(self, i, None)
        else:
            raise StatusFileError("Didn't find any status in file %s" % self.fromfile)
    