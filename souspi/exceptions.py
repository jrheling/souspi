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
