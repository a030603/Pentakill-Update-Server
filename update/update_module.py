# Pentakill update module
# 
# Update module contains methods to update
# summoner data, match data and statistics data
#
# How to use is easy
# 1. call init() method to initialize database and LOL API
# 2. call update methods to update data
# 3. call close() method to close db connection and LOL API

from pentakill.lolapi import lolapi
from pentakill.update import lolfastapi
from pentakill.db import connector

class UpdateModule(object):
    def __init__(self):
        self.db = connector.PentakillDB()
        self.api = lolfastapi.LOLFastAPI()
    
    def init(self):
        self.db.init()
        self.api.start_multiple_get_mode()
        self.api.set_keep_alive(True)
        
    def close(self):
        self.api.close_multiple_get_mode()
        self.db.close()
        
    # Update summoner data by id or name
    # at least one of two must be not None.
    # If both are not None, id is used for identifying summoner
    def updateSummoner(self, id=None, name=None):
        reqs = lolfastapi.FastRequest()
        if id:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_names, (u'\uba38\ud53c93'.encode('utf8'),)))
        

        
'''
errno
'''
E_PYTHON_ERROR = -1
E_UNKNOWN = 0
    
class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
    
class PythonBuiltInError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_PYTHON_ERROR)
        

if __name__ == '__main__':
    print 'test update'
    module = UpdateModule()
    module.init()
    module.close()
    