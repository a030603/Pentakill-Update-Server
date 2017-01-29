# Errors raised by pentakill update server and pentakill lol apis are defined here

# Parent class of all errors
class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
    
# Error numbers
E_UNKNOWN = 0
E_INVALID_ARG_ERROR = 1
E_PYTHON_ERROR = 2
E_NOT_FOUND_ERROR = 3           # Cannot find summoner or match
E_DB_ERROR = 4
E_API_ERROR = 5                 # API Error
E_API_TIMEOUT = 6               # API Error (timeout)
E_API_UNAVAILABLE = 7           # API problem (config or api server)
E_TYPE_CONVERT_ERROR = 8
E_COOLDOWN_TIME_ERROR = 9       # Wait time for next update remaining
E_UNSUPPORTED_MATCH_ERROR = 10  # Unsupported match type
E_TYPE_CONVERT_ERROR = 8

class UnknownError(Error):
    def __init__(self, msg):
            Error.__init__(self, msg, E_UNKNOWN)
            
class InvalidArgumentError(Error):
    def __init__(self, msg):
            Error.__init__(self, msg, E_INVALID_ARG_ERROR)
            
class PythonBuiltInError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_PYTHON_ERROR)
        
class NotFoundError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_NOT_FOUND_ERROR)

class DBError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_DB_ERROR)
        
class APIError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_API_ERROR)
        
class APITimeout(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_API_TIMEOUT)

class APIUnavailable(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_API_UNAVAILABLE)
        
class TypeConvertError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_TYPE_CONVERT_ERROR)
        
class CoolTimeError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_COOLDOWN_TIME_ERROR)
       
class UnsupportedMatchError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_UNSUPPORTED_MATCH_ERROR)

# Inherited Error classes
class TypeConvertError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_TYPE_CONVERT_ERROR)