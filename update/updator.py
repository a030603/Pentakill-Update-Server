# Pentakill update module
# 
# Update module contains methods to update
# summoner data, match data and statistics data
#
# How to use is easy
# 1. call init() method to initialize database and LOL API
# 2. call put_data() method to configure data needed to update
# 3. call update methods to update data
# 4. call close() method to close db connection and LOL API

from pentakill.lolapi import lolapi
from pentakill.update import lolfastapi
from pentakill.db import connector
from pentakill.db import error

# Simple configuration
T_WAIT = 10.0      # timeout for api data

# Number of trial
C_SUMMONER_TRY = 1

class UpdateModule(object):
    def __init__(self):
        self.api = lolfastapi.LOLFastAPI()
    
    def init(self):
        self.api.start_multiple_get_mode()
        self.api.set_keep_alive(True)
        
    def close(self):
        self.api.close_multiple_get_mode()

    def getSummonerUpdator(self):
        return SummonerUpdator(self)
    
# Collection of functions frequently used for DB
### We do not use it anymore
class DBUtilizer(object):
    def __init__(self):
        pass
    
    def DBInit(self, db):
        try:
            db.init()
            cursor = db.query("set names utf8; set AUTOCOMMIT=0;", multi=True, buffered=False)
            cursor.close()
        except error.Error as e:
            raise DBError(str(e))
DBUtil = DBUtilizer()

# Generic class for all updator
class Updator(object):
    def init(self):
        pass
    
    def put_data(self, data):
        pass
    
    def update(self):
        pass
    
    def close(self):
        pass
    
# Pentakill updator type
class PentakillUpdator(Updator):
    def __init__(self, module, trial=1):
        self.module = module
        self.api = module.api
        self.db = connector.PentakillDB()
        self.trial = trial
        self.data = {}
        
    def init(self):
        try:
            self.db.init()
            cursor = self.db.query("set names utf8; set AUTOCOMMIT=0;", multi=True, buffered=False)
            cursor.close()
        except error.Error as e:
            raise DBError(str(e))
        
    # puts dictionary 'data' containing data for update
    # data can be accessed from self.data in _update method
    # data is shallow copied.
    def put_data(self, data):
        self.data = data.copy()
        
    # pentakill generic update routine
    # returns true for success, raise Error for failure
    def update(self):
        trial = 0
        while True:
            try:
                self.db.begin()
                self._update()
            except (Error, error.Error, Exception) as err:
                try:
                    raise err
                except Error as err:
                    error = err
                except errorError as err:
                    error = DBError(str(err))
                except Exception as err:
                    error = UnknownError(str(err))
                # rollback everything from here
                try:
                    self.db.rollback()
                    self._rollback
                except error.Error as err:
                    raise DBError(str(err))
                # rollback end
                trial += 1
                if trial >= self.trial:
                    raise error
                else:
                    continue
            else:
                try:
                    self.db.commit()
                except error.Error as err:
                    raise DBError(str(err))
                break
        return True
    
    # update routine except transaction control
    # when exception is raised in this function,
    # _rollback method is called to return to initial state 
    def _update(self):
        pass
    
    # rollback routine to go back to initial state
    # this function don't need to query DB rollback
    def _rollback(self):
        pass
    
    def close(self):
        self.db.close()    
        
# Update summoner data by id or name
# data dictionary must contain "id" or "name" key
# at least one of two must be given.
# If both are given, "id" is used to identify summoner
# name : string, utf8 encoded string name
# id : int, summoner id
class SummonerUpdator(PentakillUpdator):
    def __init__(self, module):
        PentakillUpdator.__init__(self, module, C_SUMMONER_TRY)
        
    def _update(self):
        data = self.data
        reqs = lolfastapi.FastRequest()
        if "id" in data:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_ids, (data["id"],)))
        elif "name" in data:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_names, (data["name"],)))
        else:
            raise InvalidArgumentError("id or name must be given")
        
        respond = self.api.get_multiple_data(reqs)
        if not respond.wait_response(T_WAIT):
            raise APITimeout("Sever do not respond too long")
        res = respond.get_response('summoner')
        print res
    
'''
errno
'''
E_UNKNOWN = 0
E_INVALID_ARG_ERROR = 1
E_PYTHON_ERROR = 2
E_NOT_FOUND_ERROR = 3           # Cannot find summoner or match
E_SERVICE_UNAVAILABLE_ERROR = 4 # API problem (config or api server)
E_API_TIMEOUT = 5               # API Error (timeout)
E_DB_ERROR = 6
    
class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
            
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

class ServiceUnavailableError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_SERVICE_UNAVAILABLE_ERROR)
        
class APITimeout(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_API_TIMEOUT)
        
class DBError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_DB_ERROR)

if __name__ == '__main__':
    print 'test update'
    module = UpdateModule()
    module.init()
    updator = module.getSummonerUpdator()
    updator.init()
    updator.put_data({"name":u'\uba38\ud53c93'.encode('utf8')})
    updator.update()
    module.close()
    print 'test passed'