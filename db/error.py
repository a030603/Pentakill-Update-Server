# This file contains every errors can occur in DB connection

'''
Error constants
'''

E_PYTHON_ERROR = -1
E_UNKNOWN = 0
E_CONNECTION_FAIL = 1
E_SYNTAX_ERROR = 2
E_QUERY_ERROR = 3
E_DB_NOT_CLOSED = 4
# Main error class which is parent of every specific error class
class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return "ERROR : " + self.msg + " (" + str(self.errno) + ")"


# List of explicit error returned by pentakillDB object and correspondants
class PythonBuiltInError(Error):
    """ Any error raised by bulit-in python errors (AtrributeError, ... etc) """
    pass

class ConnectionFailure(Error):
    pass

class QueryError(Error):
    """ Any error raised when querying """
    pass

class SQLSyntaxError(Error):
    """ Syntax error of query """
    pass

class NotClosed(Error):
    pass
