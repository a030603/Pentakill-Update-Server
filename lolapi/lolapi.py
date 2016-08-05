# Pentakill LOL API 1.0
#
# This is actuall terminal which connects to Riot official LOL API
# 
# There are three connections, main connection for retrieving general
# purpose data such as summoners, runes, games. Another is static connection
# for static data. The other is status connection for shards data.
#
# each connection should be initialized before you retrieve data related
# to the connection.
# But although you don't initialize explicitly, when you call api method,
# it will initialize automatically.
#
# after you do all the things, you must close the connection.

from pentakill.lolapi import http
from pentakill.lolapi.config import *
import json

'''
states
'''
S_IDLE = 1
S_CONNECTED = 2

'''
constants
'''
H_MAIN = 1
H_STATIC = 2
H_STATUS = 3

class LOLAPI(object):
    def __init__(self, host=None, port=None, key=None, region=None, platform=None, timeout=None
                 , static_host=None, static_port=None, status_host=None, status_port=None
                , season=None):
        
        self.key = key or KEY
        self.region = region or REGION
        self.platform = platform or PLATFORM
        # main host data
        self.host = (host or HOST) % (self.region,)
        self.port = port or PORT
        self.main_conn = None
        self.timeout = timeout or TIMEOUT
        
        # static data host
        self.static_host = static_host or STATIC_HOST
        self.static_port = static_port or STATIC_PORT
        self.static_conn = None
        
        # status data host
        self.status_host = status_host or STATUS_HOST
        self.status_port = status_port or STATUS_PORT
        self.status_conn = None
        
        self.season = season or SEASON
        
        self.debugMode = 0
        
        self.states = {H_MAIN:S_IDLE,
                       H_STATUS:S_IDLE,
                       H_STATIC:S_IDLE}
        
    def init(self):
        if self.states[H_MAIN] != S_IDLE:
            raise NotClosed('close connection before you do init', E_NOT_CLOSED)
        
        try:
            if not self.main_conn:
                self.main_conn = http.HTTPS(self.host, self.port, timeout=self.timeout)
        except Exception:
            raise InitializationFail('init failed', E_INITIALIZATION_FAIL)
        
        self.states[H_MAIN] = S_CONNECTED
    
    def init_status(self):
        if self.states[H_STATUS] != S_IDLE:
            raise NotClosed('close connection before you do init', E_NOT_CLOSED)
        
        try:
            if not self.status_conn:
                self.status_conn = http.HTTP(self.status_host, self.status_port, timeout=self.timeout)
        except Exception:
            raise InitializationFail('init failed', E_INITIALIZATION_FAIL)            
        
        self.states[H_STATUS] = S_CONNECTED
        
    def init_static(self):
        if self.states[H_STATIC] != S_IDLE:
            raise NotClosed('close connection before you do init', E_NOT_CLOSED)
        
        try:
            if not self.static_conn:
                self.static_conn = http.HTTPS(self.static_host, self.static_port, timeout=self.timeout)
        except Exception:
            raise InitializationFail('init failed', E_INITIALIZATION_FAIL)            
        
        self.states[H_STATIC] = S_CONNECTED
        
    def _init_type(self, type):
        if type == H_MAIN:
            self.init()
        elif type == H_STATUS:
            self.init_status()
        elif type == H_STATIC:
            self.init_static()
        
    # DEPRECATED: re-initialize LOLAPI forcely to S_CONNECTED state
    # after Error is raised, call this to re-use LOLAPI 
    # but you don't need to use this cause calling api method automatically
    # re-initialize connection.
    # If this fails and raises exception, LOLAPI will be in IDLE state before init
    # in which it raise exception if you call any API method
    def force_init(self):
        inited = self.state.copy()
        self.close()
        try:
            if inited[H_MAIN]:
                self.init()
            if inited[H_STATUS]:
                self.init_status()
            if inited[H_STATIC]:
                self.init_static()
        except Exception as err:
            self.close()
            raise err
        
    # get connection of type 'type'
    def _get_conn(self, type):
        if type == H_MAIN:
            return self.main_conn
        elif type == H_STATIC:
            return self.static_conn
        elif type == H_STATUS:
            return self.status_conn
        return None
    
    # check if status of type 'type' is 'status'.
    # if not, raise InvalidUse exception with messsage 'msg'
    def _check_status(self, type, status, msg):
        try:
            if self.states[type] != status:
                if status == S_CONNECTED:
                    raise InvalidUse(msg, E_INVALID_USE)
                elif status == S_IDLE:
                    raise InvalidUse(msg, E_INVALID_USE)
                
                raise Error('Unknown state', E_UNKNOWN)
            
        except KeyError:
            raise UnknownType('unknown connection type', E_UNKNOWN_TYPE)
        
    def _set_headers(self, type, method='GET', loc='/'):
        self._check_status(type, S_CONNECTED, 'connection not made')

        conn = self._get_conn(type)
        conn.setRequest(method, loc)
        
        # set headers
        if C_CONNECTION:
            conn.putHeader('Connection', C_CONNECTION)
        if C_ACCEPT:
            conn.putHeader('Accept', C_ACCEPT)
        else:
            conn.putHeader('Accept', 'application/json')
        if C_USER_AGENT:
            conn.putHeader('User-Agent', C_USER_AGENT)
        if C_ACCEPT_ENCODING:
            conn.putHeader('Accept-Encoding', C_ACCEPT_ENCODING)
        else:
            conn.putHeader('Accept-Encoding', 'gzip')
        
    # close functions will never raise exception
    def close_main(self):
        if self.main_conn:
            self.main_conn.close()
            self.main_conn = None
        self.states[H_MAIN] = S_IDLE
        
    def close_static(self):
        if self.static_conn:
            self.static_conn.close()
            self.static_conn = None
        self.states[H_STATIC] = S_IDLE
        
    def close_status(self):
        if self.status_conn:
            self.status_conn.close()
            self.status_conn = None
        self.states[H_STATUS] = S_IDLE
        
    def close(self):
        self.close_main()
        self.close_static()
        self.close_status()
        
    def _close_type(self, type):
        if type == H_MAIN:
            return self.close_main()
        elif type == H_STATIC:
            return self.close_static()
        elif type == H_STATUS:
            return self.close_status()
            
    def set_debug_mode(self, mode):
        self.debugMode = mode
        
    def _debug_print(self, name, msg):
        if self.debugMode:
            print 'Debug mode (%s): %s' % (name, msg)
        
    def _send_request(self, type, loc):
        self._debug_print('Reuqest path', loc)
            
        conn = self._get_conn(type)
        if self.states[type] != S_CONNECTED or conn == None:
            self._close_type(type)
            self._init_type(type)
            
        self._set_headers(type=type, loc=loc)
        try:
            conn.sendRequest()
        
            msg = conn.getResponse()
            status = msg.getStatus()
        
            try:
                content = msg.readDecompress()
                #print msg.getHeaders()
            # let's parse json string into python dictionary
            except http.InvalidUseException as err:
                raise HTTPFail(str(err), E_HTTP)
                
        except Exception as err:
            # re-initialize faulty connection
            # it should never raise exception
            self._close_type(type)
            self._init_type(type)
            
            try:
                raise err
            except http.Timeout as err:
                raise Timeout(str(err), E_TIMEOUT)
            except http.Error as err:
                raise HTTPFail(str(err), E_HTTP)
        else:
            try:
                if content:
                    content = json.loads(content)
            except ValueError:
                # not json content, just return it
                #raise JSONParseFail('wrong json string', E_JSON_FAIL)       
                pass
        # message must be closed
        msg.close()
            
        return (status, content)
    
    # This function gets request path, dictionary arguments for that path, and
    # dictionary arguments args for 'GET' method argument in uri.
    # It requests and returns tuple of status message and content
    def _set_and_request(self, type, path, patharg=None, args=None):
        self._check_status(type, S_CONNECTED, 'connection not made')
        
        loc = path
        if patharg != None:
            loc = path.format(**patharg)
        if args != None:
            loc = '%s%s' % (loc, self._combine_args(args))
            
        return self._send_request(type, loc)
        
    # it combines all name and values in dictionary so that
    # arguments are in the form '?%s=%s&%s=%s...' in uri
    def _combine_args(self, args):
        data = []
    
        for name in args:
            data.append('%s=%s' % (name, args[name]))
        
        arg = '&'.join(data)
        return '?' + arg
    
    # ###############################################################
    #                         CHAMPION
    # ###############################################################  
    
    # get champions' enabled information
    # Option :
    # free_to_play = if true, it retrieves only free-to-play champions
    def get_champions_status(self):
        patharg = {'region':self.region,
                   'version':V_CHAMPION}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_CHAMPIONS_ENABLED, patharg, args)
    
    # get champions' enabled information by champion id
    # c_id = int or long champion id
    # Option :
    # free_to_play = if true, it retrieves only free-to-play champions
    def get_champions_status_by_id(self, c_id):
        patharg = {'region':self.region,
                   'version':V_CHAMPION,
                   'id':c_id}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_CHAMPIONS_ENABLED_BY_ID, patharg, args)
    
    # ###############################################################
    #                       CURRENT-GAME
    # ###############################################################  
    
    # get summoners current game by summoner id
    # s_id = int or long summoner id 
    def get_current_game(self, s_id):
        patharg = {'platformId':self.platform,
                   'summonerId':s_id}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_CURRENT_GAME, patharg, args)
        
    
    # ###############################################################
    #                      FEATURED-GAMES
    # ###############################################################  
    
    # get featured games
    def get_featured_games(self):
        patharg = {}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_FEATURED_GAMES, patharg, args)
    
    # ###############################################################
    #                           GAME
    # ###############################################################  
    
    # get summoner's recent 10 games by summoner id
    # arg : int or str representing summoenr id
    def get_recent_games(self, arg):
        patharg = {'region':self.region,
                   'version':V_GAME,
                   'summonerId':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_RECENT_GAMES, patharg, args)
    
    # ###############################################################
    #                          LEAGUE
    # ###############################################################  
    
    # get summoners' leagues by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_leagues(self, arg):
        patharg = {'region':self.region,
                   'version':V_LEAGUE,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_LEAGUE_BY_SUMMONER_IDS, patharg, args)
    
    # get summoners' league entries by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_league_entries(self, arg):
        patharg = {'region':self.region,
                   'version':V_LEAGUE,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_LEAGUE_ENTRY_BY_SUMMONER_IDS, patharg, args)
    
    # get teams' leagues by team ids
    # arg = team id ([',' team id])*
    def get_leagues_of_teams(self, arg):
        patharg = {'region':self.region,
                   'version':V_LEAGUE,
                   'teamIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_LEAGUE_BY_TEAM_IDS, patharg, args)
    
    # get teams' league entries by team ids
    # arg = team id ([',' team id])*
    def get_league_entries_of_teams(self, arg):
        patharg = {'region':self.region,
                   'version':V_LEAGUE,
                   'teamIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_LEAGUE_ENTRY_BY_TEAM_IDS, patharg, args)
    
    # get challenger's league
    # Required : 
    # type = one of 'RANKED_SOLO_5x5'
    #               'RANKED_TEAM_3x3'
    #               'RANKED_TEAM_5x5'
    #        default is 'RANKED_SOLO_5x5'
    def get_leagues_of_challengers(self, type='RANKED_SOLO_5x5'):
        patharg = {'region':self.region,
                   'version':V_LEAGUE}
        args = {'api_key':self.key}
        if type != None:
            args['type'] = type
        return self._set_and_request(H_MAIN, P_CHALLENGER_LEAGUE, patharg, args)
        
    
    # ###############################################################
    #                     LOL-STATIC-DATA
    #      Requests to this API do not consume your rate limit
    # ###############################################################   
    
    # Common meaning of two option parameters are here
    
    # locale = Locale code for returned data (e.g., en_US, es_ES). 
    #(optional) If not specified, the default locale for the region is used.
    # version = Data dragon version for returned data. If not specified, 
    #(optional) the latest version for the region is used. 
    #           List of valid versions can be obtained from the /versions endpoint.
    
    # get champion lists and information
    # Options : 
    # locale
    # version
    # data_by_id = If specified as true, the returned data map will use the champions' IDs as the keys.
    #              If not specified or specified as false, the returned data map will 
    #              use the champions' keys instead.
    # champ_data = Tags to return additional data. Only type, version, data, id, 
    #              key, name, and title are returned by default if this parameter isn't specified.
    #              To return all additional data, use the tag 'all'.
    def get_static_champions(self, locale=None, version=None, data_by_id=None,
                             champ_data=None):
        patharg = {'region':self.region,
                   'version':V_STATIC}
        
        args = {'api_key':self.key}
        if locale != None:
            args['locale'] = locale
        if version != None:
            args['version'] = version
        if data_by_id != None:
            args['dataById'] = data_by_id
        if champ_data != None:
            args['champData'] = champ_data
        return self._set_and_request(H_STATIC, P_CHAMPIONS, patharg, args)
    
    # get champion data by champion id 
    # c_id = champion id
    # Options : 
    # locale
    # version
    # champ_data = same meaning as above
    def get_static_champion_by_id(self, c_id, locale=None, version=None,
                                  champ_data=None):
        patharg = {'region':self.region,
                   'version':V_STATIC}
        
        args = {'api_key':self.key}
        if locale != None:
            args['locale'] = locale
        if version != None:
            args['version'] = version
        if champ_data != None:
            args['champData'] = champ_data
        return self._set_and_request(H_STATIC, P_CHAMPION_BY_ID, patharg, args)
    
    # get list of item data
    # Options : 
    # locale
    # version
    # item_list_data = Tags to return additional data.
    def get_static_items(self, locale=None, version=None, item_list_data=None):
        patharg = {'region':self.region,
                   'version':V_STATIC}
        
        args = {'api_key':self.key}
        if locale != None:
            args['locale'] = locale
        if version != None:
            args['version'] = version
        if item_list_data != None:
            args['itemListData'] = item_list_data
        return self._set_and_request(H_STATIC, P_ITEMS, patharg, args)
    
    # ###############################################################
    #                       LOL-STATUS
    #      Requests to this API do not consume your rate limit
    # ###############################################################   
    
    # get shards info
    def get_shards(self):
        return self._send_request(H_STATUS, P_STATUS_SHARD)
    
    # get shards info by region
    def get_shards_by_region(self, region=None):
        region = region or self.region
        patharg = {'region':region}
        return self._set_and_request(H_STATUS, P_STATUS_SHARD_BY_REGION, patharg)
    
    # ###############################################################
    #                          MATCH
    # ###############################################################     
    
    # get statistics of match by match id
    # match_id : match id int or long
    # Options :
    # timeline : string one of 'true' and 'false'
    def get_match(self, match_id, timeline=None):
        patharg = {'region':self.region,
                   'version':V_MATCH,
                   'matchId':match_id}
        
        args = {'api_key':self.key}
        if timeline != None:
            args['includeTimeline'] = timeline
        
        return self._set_and_request(H_MAIN, P_MATCH, patharg, args)
    
    # ###############################################################
    #                         MATCH LIST
    # ###############################################################  
    
    # get summoners' match list
    # s_id = int or str representing summoenr id
    # Options :
    # champ_ids = Comma-separated champion ids
    # ranked_queue = Comma-separated queue types
    #                       'RANKED_SOLO_5x5'
    #                       'RANKED_TEAM_3x3'
    #                       'RANKED_TEAM_5x5'
    # seasons = Comma-separated seasons 
    #                       'PRESEASON3'
    #                       'SEASON3'
    #                       'PRESEASON2014'
    #                       'SEASON2014'
    #                       'PRESEASON2015'
    #                       'SEASON2015'
    #                       'PRESEASON2016'
    #                       'SEASON2016'
    # beginIndex = The begin index to use for fetching games
    # endIndex = The end index to use for fetching games
    # beginTime = The begin time to use for fetching games specified as epoch milliseconds
    # endTime = The end time to use for fetching games specified as epoch milliseconds
    def get_match_history(self, s_id, champ_ids=None,
                          ranked_queue=None, seasons=None, beginIndex=None,
                          endIndex=None, beginTime=None, endTime=None):
        patharg = {'region':self.region,
                   'version':V_MATCHLIST,
                   'summonerId':s_id}
        
        args = {'api_key':self.key}
        if champ_ids != None:
            args['championIds'] = champ_ids
        if ranked_queue != None:
            args['rankedQueues'] = ranked_queue
        if seasons != None:
            args['seasons'] = seasons
        if beginIndex != None:
            args['beginIndex'] = beginIndex
        if endIndex != None:
            args['endIndex'] = endIndex
        if beginTime != None:
            args['beginTime'] = beginTime
        if endTime != None:
            args['endTime'] = endTime
            
        return self._set_and_request(H_MAIN, P_MATCH_LIST, patharg, args)
    
    # ###############################################################
    #                          STATS
    # ###############################################################
    
    # get summoner's champion stats in ranked game by summoner id and season
    # s_id : int or str representing summoenr id
    # season : season info
    def get_rank_stats(self, s_id, season=None):
        season = season or self.season
        patharg = {'region':self.region,
                   'version':V_STATS,
                   'summonerId':s_id}
        args = {'season':season, 'api_key':self.key}
        return self._set_and_request(H_MAIN, P_RANK_STATS, patharg, args)
    
    # get summoner's stats for all types of game by summoner id
    # s_id : int or str representing summoenr id
    # season : season info
    def get_stats_summary(self, s_id, season=None):
        season = season or self.season
        patharg = {'region':self.region,
                   'version':V_STATS,
                   'summonerId':s_id}
        args = {'season':season, 'api_key':self.key}
        return self._set_and_request(H_MAIN, P_PLAYER_STAT_SUMMARY, patharg, args)    
    
    # ###############################################################
    #                          SUMMONERS
    # ###############################################################
    
    # get summoner information by summoner names
    # arg = summoner name ([',' summoner name])*
    def get_summoners_by_names(self, arg):
        patharg = {'region':self.region,
                   'version':V_SUMMONER,
                   'summonerNames':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_SUMMONERS_BY_NAME, patharg, args)
    
    # get summoner information by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_summoners_by_ids(self, arg):
        patharg = {'region':self.region,
                   'version':V_SUMMONER,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_SUMMONERS_BY_IDS, patharg, args)
    
    # get summoners' rune pages by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_summoner_runes(self, arg):
        patharg = {'region':self.region,
                   'version':V_SUMMONER,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_SUMMONER_RUNES, patharg, args)
    
    # get summoners' masteries by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_summoner_masteries(self, arg):
        patharg = {'region':self.region,
                   'version':V_SUMMONER,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_SUMMONER_MASTERIES, patharg, args)
    
    # get summoners' names by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_summoner_names(self, arg):
        patharg = {'region':self.region,
                   'version':V_SUMMONER,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_SUMMONER_NAMES_BY_IDS, patharg, args)
    
    # ###############################################################
    #                          TEAM
    # ###############################################################
    
    # get rank teams by summoner ids
    # arg = summoner id ([',' summoner id])*
    def get_teams_by_ids(self, arg):
        patharg = {'region':self.region,
                   'version':V_TEAM,
                   'summonerIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_TEAMS_BY_SUMMONER_IDS, patharg, args)
    
    # get rank teams by team ids
    # arg = team id ([',' team id])*
    def get_teams_by_team_ids(self, arg):
        patharg = {'region':self.region,
                   'version':V_TEAM,
                   'teamIds':arg}
        args = {'api_key':self.key}
        return self._set_and_request(H_MAIN, P_TEAMS_BY_TEAM_IDS, patharg, args)
    

'''
errno
'''
E_PYTHON_ERROR = -1
E_UNKNOWN = 0
E_NOT_CLOSED = 1
E_JSON_FAIL = 2
E_TIMEOUT = 3
E_HTTP = 4
E_INVALID_USE = 5
E_UNKNOWN_TYPE = 6
E_INITIALIZATION_FAIL = 7

class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
    
    
class PythonBuiltInError(Error):
    pass    

class NotClosed(Error):
    pass

class JSONParseFail(Error):
    pass

class Timeout(Error):
    pass

class HTTPFail(Error):
    pass

class InvalidUse(Error):
    pass

class UnknownType(Error):
    pass

class InitializationFail(Error):
    pass

# tests
if __name__ == '__maing__':
    import time 
    api = LOLAPI()
    api.init()
    api.set_debug_mode(1)
    begin = time.time()
    
    print '########## summoner info ##############'
    while True:
        try:
            content = api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
            print content[0]
            content = content[1]
        except Error as err:
            print err
        finally:
            time.sleep(2)
    
if __name__ == '__maign__':
    api = LOLAPI()
    api.init()
    content = api.get_match_history(2576538, seasons='SEASON2015,SEASON2014')
    #print content[1]
    api.close()
    
# tests
if __name__ == '__main__':
    import time 
    api = LOLAPI()
    api.init()
    api.set_debug_mode(1)
    begin = time.time()
    
    print '########## summoner info ##############'
    content = api.get_summoners_by_names(",".join((u'\uba38\ud53c93'.encode('utf8'),u'\uba38\ud53c94'.encode('utf8'))))
    print content[0]
    content = content[1]
    s_id = content[u'\uba38\ud53c93']['id']
    print content[u'\uba38\ud53c93']['id']
    print content[u'\uba38\ud53c94']['id']

    print '########## summoner info ##############'
    content = api.get_summoners_by_ids(2576538)
    print content[0]
    content = content[1]
    #s_id = content[u'\uba38\ud53c93']['id']
    print s_id
    #print content
    
    print '########## recent game ##############'
    content = api.get_recent_games(s_id)
    print content[0]
    content = content[1]
    #print content
    
    print '########## league entry ##############'
    content = api.get_league_entries(s_id)
    print content[0]
    content = content[1]
    #print content    
    
    print '########## ranked stats ##############'
    content = api.get_rank_stats(s_id)
    print content[0]
    content = content[1]
    #print content    
    
    print '########## summoner runes ##############'
    content = api.get_summoner_runes(s_id)
    print content[0]
    content = content[1]
    #print content    
    
    print '########## summoner masteries ##############'
    content = api.get_summoner_masteries(s_id)
    print content[0]
    content = content[1]
    #print content    
    
    print '########## current game ##############'
    content = api.get_current_game(s_id)
    print content[0]
    content = content[1]
    print content    
    
    #print '########## challenger league ##############'
    #content = api.get_leagues_of_challengers()
    #print content[0]
    #content = content[1]
    ##print content    
    
    #print '########## featued games ##############'
    #content = api.get_featured_games()
    #print content[0]
    #content = content[1]
    ##print content    

    
    #api.init_static()
    #print '########## static champions ##############'
    #content = api.get_static_champions()
    #print content[0]

    
    #print '########## shards by region ##############'
    #api.status_init()
    #content = api.get_shards_by_region('na')
    #print content[0]
    #content = content[1]
    ##print content    
    
    #print '########## match ##############'
    #api.init_status()
    #content = api.get_match(1736835012, timeline='true')
    #print content[0]
    #content = content[1]
    #print str(content)[:1024]
    end = time.time()
    
    print end-begin, 'sec taken'
    api.close()
    
    
if __name__ == '__main3__':
    import time
    import threading
    
    #print "???"
    api = LOLAPI()
    api.set_debug_mode(0)
    api.init()
    #api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
    begin = time.time()
    try:
        for i in range(200):
            content = api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
            time.sleep(0.1)
            print content[0]
            content = content[1]
            end = time.time()
            print end-begin,'sec taken'
        time.sleep(11)
        for i in range(100):
            #time.sleep(0.2)
            content = api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
            print content[0]
            content = content[1]
            end = time.time()
            print end-begin,'sec taken'
    finally:
        api.close()
        
    s1 = threading.Semaphore(1)
    s2 = threading.Semaphore(1)
    s3 = threading.Semaphore(1)
    s4 = threading.Semaphore(1)
    class test(threading.Thread):
        def __init__(self, s):
            threading.Thread.__init__(self)
            
            self.s = s
        def run(self):
            api = LOLAPI()
            api.set_debug_mode(0)
            api.init()
            api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
            begin = time.time()
            try:
                for i in range(50):
                    self.s.acquire()
                    content = api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
                    print content[0]
                    content = content[1]
                    end = time.time()
                    print end-begin,'sec taken', i
                    self.s.release()
            finally:
                api.close()
    
    a = test(s1)
    a.start()
    b = test(s1)
    b.start()
    c = test(s2)
    c.start()
    d = test(s2)
    d.start()
    
#e = test(2)