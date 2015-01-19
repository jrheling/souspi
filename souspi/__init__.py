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
import tempfile

def atomic_file_write(file_to_write, data, uid=None, gid=None):
    """ Atomically (via a tempfile) write data to file at specified path.
    
        If data is None, this creates an empty file.
        If uid/gid are specified, chown accordingly. 
        Raises OSError if file rename fails.
    """
    (tmp_fh, tmp_name) = tempfile.mkstemp(dir=os.path.dirname(os.path.realpath(file_to_write)),
                                          prefix=os.path.basename(os.path.realpath(file_to_write)))
    if data is not None:
        os.write(tmp_fh,bytes(data))
    os.close(tmp_fh)
    
    if (uid is not None) or (gid is not None):
        if uid is None:
            new_uid = -1
        else:
            new_uid = uid
        if gid is None:
            new_gid = -1
        else:
            new_gid = gid
        os.chown(tmp_name, new_uid, new_gid)
    
    try:
        os.rename(tmp_name, os.path.realpath(file_to_write))
    except OSError, e:
        os.unlink(tmp_name)
        msg = "Failed to update %s: %s" % (os.path.realpath(file_to_write), e.strerror)
        raise OSError(e)

class SousPiError(Exception):
    """ Exception base class. """
    def __str__(self):
        return self.msg

class BadTempValueError(SousPiError):
    def __init__(self, msg):
        self.msg = msg

class SetpointFileError(SousPiError):
    def __init__(self, msg):
        self.msg = msg

class StatusFileError(SousPiError):
    def __init__(self, msg):
        self.msg = msg

class TemperatureFileError(SousPiError):
    def __init__(self, msg):
        self.msg = msg

class SetpointNotSetError(SousPiError):
    def __init__(self, msg):
        self.msg = msg

class ImpossibleSetpointError(SousPiError):
    def __init__(self, msg):
        self.msg = msg
