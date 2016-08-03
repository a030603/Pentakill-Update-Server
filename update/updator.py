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
from pentakill.lolapi import lolfastapi
from pentakill.db import connector
from pentakill.db import error

# Simple configuration
T_WAIT = 10.0      # timeout for api data

# Number of trial
C_SUMMONER_TRY = 1

# Status codes
SC_OK = '200'
SC_NOT_FOUND = '404'

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
    
# Collection of functions frequently used
class Utility(object):
    # Transfrom unicode string of summoner names
    def transform_names(self, names):
        return names.lower().replace(" ", "").encode('utf8')
    
    # Get abbrevation names
    def abbre_names(self, names):
        return names.replace(" ", "")
    
Util = Utility()

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
                    errtmp = err
                except error.Error as err:
                    errtmp = DBError(str(err))
                except Exception as err:
                    errtmp = UnknownError(str(err))
                # rollback everything from here
                try:
                    self.db.rollback()
                    self._rollback()
                except error.Error as err:
                    raise DBError(str(err))
                # rollback end
                trial += 1
                if trial >= self.trial:
                    raise errtmp
                else:
                    continue
            else:
                try:
                    #self.db.commit()
                    self.db.rollback()
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
        
    def _wait_response(self, respond):
        if not respond.wait_response(T_WAIT):
            raise APITimeout("Sever do not respond too long")
        
    def _check_response(self, res):
        if res[0] == lolfastapi.FS_TIMEOUT:
            raise APITimeout("Sever do not respond too long")
        elif res[0] == lolfastapi.FS_SERVICE_UNAVAILABLE:
            raise APIUnavailable("Server is not available now")
        elif res[0] != lolfastapi.FS_OK:
            raise APIError("Problem with API server")
        
        if res[1][0][0] != SC_OK:
            raise NotFoundError("Cannot find such summoner")
            
        
        
# Update summoner data by id or name
# data dictionary must contain "id" or "name" key
# at least one of two must be given.
# If both are given, "id" is used to identify summoner
# name : string, unicode encoded string name
# id : int, summoner id
class SummonerUpdator(PentakillUpdator):
    def __init__(self, module):
        PentakillUpdator.__init__(self, module, C_SUMMONER_TRY)
        
    def _update(self):
        self._update_summoner()
        self._get_api_data()
        self._update_league()
        
    def _update_summoner(self):
        data = self.data
        if "name" in data:
            data["name"] = Util.transform_names(data["name"])
            
        reqs = lolfastapi.FastRequest()
        if "id" in data:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_ids, (data["id"],)))
        elif "name" in data:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_names, (data["name"],)))
        else:
            raise InvalidArgumentError("id or name must be given")
        
        respond = self.api.get_multiple_data(reqs)
        self._wait_response(respond)
        res = respond.get_response('summoner')
        
        self._check_response(res)
        #print res
        if "id" in data:
            apidat = res[1][1][str(data["id"])]
        else:
            apidat = res[1][1][data["name"].decode('utf8')]
                         
        id = apidat["id"]
        name = apidat["name"].encode('utf8')
        nameAbbre = Util.abbre_names(name)
        profileIconId = apidat["profileIconId"]
        summonerLevel = apidat["summonerLevel"]
        revisionDate = apidat["revisionDate"]

        result = self.db.query("select s_id from summoners where s_name_abbre = %s and live = 1", (nameAbbre,))
        row = result.fetchRow()
        result.close()
        print row
        if row:
            if row[0] != id:
                # set current one to dead summoner
                result = self.db.query("update summoners set live = 0 where s_id = %s", (row[0],))
                result.close()
                print "dead summoner found"
        else:
            print "row not found"
            print row
        print name.decode('utf8').encode("cp949")
        print (id, profileIconId, summonerLevel, revisionDate)
        
        # check if summoner name has been changed
        result = self.db.query("select s_name from summoners where s_id = %s", (id,))
        row = result.fetchRow()
        result.close()
        if row and row[0].encode('utf8') != name:
            print "new name"
            query = ("insert into summoner_name_changes(s_id, s_name, confirmed_time) "
                     "values (%s, %s, UNIX_TIMESTAMP(now()))")
            result = self.db.query(query, (id, name))
            result.close()
            
        # update summoner data
        query = ("insert into summoners (s_id, s_name, s_name_abbre, s_icon, level, last_update, enrolled, live) "
                 "values (%s, %s, %s, %s, %s, UNIX_TIMESTAMP(now()), true, true) "
                 "on duplicate key update "
                 "s_name = values(s_name), "
                 "s_name_abbre = values(s_name_abbre), "
                 "s_icon = values(s_icon), "
                 "level = values(level), "
                 "last_update = values(last_update), "
                 "enrolled = values(enrolled), "
                 "live = 1")
        result = self.db.query(query, (id, name, nameAbbre, profileIconId, summonerLevel))
        result.close()
        
        # data update
        self.data["id"] = id
    
    def _get_api_data(self):
        id = self.data["id"]
        
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('leagues', (lolapi.LOLAPI.get_league_entries, (id,)))
        reqs.add_request_name('games', (lolapi.LOLAPI.get_recent_games, (id,)))
        reqs.add_request_name('stats', (lolapi.LOLAPI.get_rank_stats, (id,)))
        reqs.add_request_name('runes', (lolapi.LOLAPI.get_summoner_runes, (id,)))
        reqs.add_request_name('masteries', (lolapi.LOLAPI.get_summoner_masteries, (id,)))
        
        respond = self.api.get_multiple_data(reqs)
        if not respond.wait_response(T_WAIT):
                    raise APITimeout("Sever do not respond too long")
                
        for name, res in respond:
            #if res[0] = lolfastapi.
            pass
                
    def _update_league(self):
        id = self.data["id"]
        
        
        
        
    
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
E_API_ERROR = 7
E_API_UNAVAILABLE = 8
    
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

class APIError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_API_ERROR)

class APIUnavailable(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_API_UNAVAILABLE)
        
if __name__ == '__main__':
    print 'test update'
    import time
    module = UpdateModule()
    module.init()
    for i in range(1):
        updator = module.getSummonerUpdator()
        updator.init()
        updator.put_data({"name":'SKT T1 F  aker  '})
        updator.put_data({"name":u'   \uba38 \ud53c   9  3'})
        #updator.put_data({"name":'zzz'})
        begin = time.time()
        updator.update()
        end = time.time()
        print end - begin, 'sec elapsed'
    module.close()
    print 'test passed'