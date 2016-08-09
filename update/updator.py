# Pentakill update module
# 
# Update module contains methods to update
# summoner data, match data and statistics data
#
# How to use is easy
# First, call methods for UpdateModule
# 1. call init() method to module to initialize LOL API
# 2. call get___Updator() method to get updator object
# Second, call methods of updator object
# 1. call init() to initialize DB connection
# 2. call put_data() method to configure data needed to update
# 3. call update() methods to update data
# 4. call close() method to close DB connection

from pentakill.lolapi import lolapi
from pentakill.lolapi import lolfastapi
from pentakill.lolapi import config
from pentakill.db import connector
from pentakill.db import error
from pentakill.update import constant
from pentakill.lib import servant
import threading

# Simple configuration
T_WAIT = 22.0      # timeout for api data

# Number of trial
C_SUMMONER_TRY = 1

# Number of background updator(servants)
C_BG_UPDATOR_NUMBER = 2

class UpdateModule(object):
    def __init__(self):
        self.api = lolfastapi.LOLFastAPI()
        self.api.set_debug(1)
        self.bg_num = C_BG_UPDATOR_NUMBER
        self.bg_next = 0
        self.bgs = []
        self.mutex = threading.Lock()
    
    def init(self):
        self.api.start_multiple_get_mode()
        self.api.set_keep_alive(True)
        
        for i in range(self.bg_num):
            bg = self._backgroundUpdator(self)
            self.bgs.append(bg)
            bg.daemon = True
            bg.start()
        
    def close(self):
        self.api.close_multiple_get_mode()
        self.api = None
        
        for i in range(self.bg_num):
            bg = self.bgs[i]
            bg.order((self.CMD_EXIT, None))
            
        for i in range(self.bg_num):
            bg = self.bgs[i]
            bg.join(60)
            
        self.bgs = None
        self.bg_num = 0
        
    # ####################################
    #     Foreground Update Methods
    # ####################################
    def getSummonerUpdator(self):
        return SummonerUpdator(self)
    
    def getRuneMasteryUpdator(self):
        return RuneMasteryUpdator(self)
    
    def getMatchUpdator(self):
        return MatchUpdator(self)
    
    # ####################################
    #     Background Update Methods
    # ####################################
    def orderRuneMasteryUpdate(self, id):
        self.mutex.acquire()
        bg = self.bgs[self.bg_next]
        self.bg_next += 1
        self.bg_next %= self.bg_num
        bg.order((self.CMD_RUNEMASTERY, id))
        self.mutex.release()
        
    # background updator commands
    CMD_EXIT = 0
    CMD_RUNEMASTERY = 1
    class _backgroundUpdator(servant.Servant):
        def __init__(self, module):
            servant.Servant.__init__(self)
            self.module = module
        
        def routine(self):
            while True:
                self.cond.acquire()
                while True:
                    try:
                        req = self.requests.popleft()
                    except IndexError:
                        self.cond.wait()
                    else:
                        break
                self.cond.release()
                
                cmd = req[0]
                if cmd == self.module.CMD_EXIT:
                    return
                elif cmd == self.module.CMD_RUNEMASTERY:
                    id = req[1]
                    try:
                        updator = self.module.getRuneMasteryUpdator()
                        updator.init()
                        updator.put_data({'id':id})
                        updator.update()
                    except Exception:
                        pass
    
# Collection of functions frequently used
class Utility(object):
    # Transfrom unicode string of summoner names
    def transform_names(self, names):
        return names.lower().replace(" ", "").encode('utf8')
    
    # Get abbrevation names
    def abbre_names(self, names):
        return names.replace(" ", "")
    
    def league_queue_convertor(self, type):
        if type == 'RANKED_SOLO_5x5':
            return constant.S_RANKED_SOLO_5x5
        elif type == 'RANKED_TEAM_3x3':
            return constant.S_RANKED_TEAM_3x3 
        elif type == 'RANKED_TEAM_5x5':
            return constant.S_RANKED_TEAM_5x5
        
        raise TypeConvertError("league queue conversion fail")
    
    def league_division_convertor(self, division):
        if division == 'I':
            return 1
        elif division == 'II':
            return 2
        elif division == 'III':
            return 3
        elif division == 'IV':
            return 4
        elif division == 'V':
            return 5
        
        raise TypeConvertError("division conversion fail")
    
    def game_mode_convertor(self, mode):
        if mode == 'CLASSIC':
            return constant.M_CLASSIC
        elif mode == 'ODIN':
            return constant.M_ODIN
        elif mode == 'ARAM':
            return constant.M_ARAM
        elif mode == 'TUTORIAL':
            return constant.M_TUTORIAL
        elif mode == 'ONEFORALL':
            return constant.M_ONEFORALL
        elif mode == 'FIRSTBLOOD':
            return constant.M_FIRSTBLOOD
        elif mode == 'ASCENSION':
            return constant.M_ASCENSION
        elif mode == 'KINGPORO':
            return constant.M_KINGPORO
        elif mode == 'SIEGE':
            return constant.M_SIEGE
        
        raise TypeConvertError("game mode conversion fail")
    
    def game_type_convertor(self, type):
        if type == 'CUSTOM_GAME':
            return constant.T_CUSTOM_GAME
        elif type == 'TUTORIAL_GAME':
            return constant.T_TUTORIAL_GAME
        elif type == 'MATCHED_GAME':
            return constant.T_MATCHED_GAME
        
        raise TypeConvertError("game type conversion fail")
    
    def subtype_convertor(self, subtype):
        if subtype == 'NONE':
            return constant.S_NONE
        elif subtype == 'NORMAL':
            return constant.S_NORMAL
        elif subtype == 'NORMAL_3x3':
            return constant.S_NORMAL_3x3
        elif subtype == 'ODIN_UNRANKED':
            return constant.S_ODIN_UNRANKED
        elif subtype == 'ARAM_UNRANKED_5x5':
            return constant.S_ARAM_UNRANKED_5x5
        elif subtype == 'BOT':
            return constant.S_BOT
        elif subtype == 'BOT_3x3':
            return constant.S_BOT_3x3
        elif subtype == 'RANKED_SOLO_5x5':
            return constant.S_RANKED_SOLO_5x5
        elif subtype == 'RANKED_TEAM_3x3':
            return constant.S_RANKED_TEAM_3x3
        elif subtype == 'RANKED_TEAM_5x5':
            return constant.S_RANKED_TEAM_5x5
        elif subtype == 'ONEFORALL_5x5':
            return constant.S_ONEFORALL_5x5
        elif subtype == 'FIRSTBLOOD_1x1':
            return constant.S_FIRSTBLOOD_1x1
        elif subtype == 'FIRSTBLOOD_2x2':
            return constant.S_FIRSTBLOOD_2x2
        elif subtype == 'SR_6x6':
            return constant.S_SR_6x6
        elif subtype == 'CAP_5x5':
            return constant.S_CAP_5x5
        elif subtype == 'URF':
            return constant.S_URF
        elif subtype == 'URF_BOT':
            return constant.S_URF_BOT
        elif subtype == 'NIGHTMARE_BOT':
            return constant.S_NIGHTMARE_BOT
        elif subtype == 'ASCENSION':
            return constant.S_ASCENSION
        elif subtype == 'HEXAKILL':
            return constant.S_HEXAKILL
        elif subtype == 'KING_PORO':
            return constant.S_KING_PORO
        elif subtype == 'COUNTER_PICK':
            return constant.S_COUNTER_PICK
        elif subtype == 'BILGEWATER':
            return constant.S_BILGEWATER
        elif subtype == 'SIEGE':
            return constant.S_SIEGE
        
        raise TypeConvertError("subtype conversion fail")
    
    def player_stat_summary_type_convertor(self, type):
        if type == 'Unranked':
            return constant.PS_Unranked
        if type == 'Unranked3x3':
            return constant.PS_Unranked3x3
        if type == 'OdinUnranked':
            return constant.PS_OdinUnranked
        if type == 'AramUnranked5x5':
            return constant.PS_AramUnranked5x5
        if type == 'CoopVsAI':
            return constant.PS_CoopVsAI
        if type == 'CoopVsAI3x3':
            return constant.PS_CoopVsAI3x3
        if type == 'RankedSolo5x5':
            return constant.PS_RankedSolo5x5
        if type == 'RankedTeam3x3':
            return constant.PS_RankedTeam3x3
        if type == 'RankedTeam5x5':
            return constant.PS_RankedTeam5x5
        if type == 'OneForAll5x5':
            return constant.PS_OneForAll5x5
        if type == 'FirstBlood1x1':
            return constant.PS_FirstBlood1x1
        if type == 'FirstBlood2x2':
            return constant.PS_FirstBlood2x2
        if type == 'SummonersRift6x6':
            return constant.PS_SummonersRift6x6
        if type == 'CAP5x5':
            return constant.PS_CAP5x5
        if type == 'URF':
            return constant.PS_URF
        if type == 'URFBots':
            return constant.PS_URFBots
        if type == 'RankedPremade3x3':
            return constant.PS_RankedPremade3x3
        if type == 'RankedPremade5x5':
            return constant.PS_RankedPremade5x5
        if type == 'NightmareBot ':
            return constant.PS_NightmareBot
        if type == 'Ascension':
            return constant.PS_Ascension
        if type == 'Hexakill':
            return constant.PS_Hexakill
        if type == 'KingPoro':
            return constant.PS_KingPoro
        if type == 'CounterPick':
            return constant.PS_CounterPick
        if type == 'Bilgewater':
            return constant.PS_Bilgewater
        if type == 'Siege':
            return constant.PS_Siege
        print type
        raise TypeConvertError("player stat summary type conversion fail")
    
    def queue_type_convertor(self, type):
        if type == 'CUSTOM':
            return constant.QT_CUSTOM
        if type == 'NORMAL_3x3':
            return constant.QT_NORMAL_3x3
        if type == 'NORMAL_5x5_BLIND':
            return constant.QT_NORMAL_5x5_BLIND
        if type == 'NORMAL_5x5_DRAFT':
            return constant.QT_NORMAL_5x5_DRAFT
        if type == 'RANKED_SOLO_5x5':
            return constant.QT_RANKED_SOLO_5x5
        if type == 'RANKED_PREMADE_5x5':
            return constant.QT_RANKED_PREMADE_5x5
        if type == 'RANKED_PREMADE_3x3':
            return constant.QT_RANKED_PREMADE_3x3
        if type == 'RANKED_TEAM_3x3':
            return constant.QT_RANKED_TEAM_3x3
        if type == 'RANKED_TEAM_5x5':
            return constant.QT_RANKED_TEAM_5x5
        if type == 'ODIN_5x5_BLIND':
            return constant.QT_ODIN_5x5_BLIND
        if type == 'ODIN_5x5_DRAFT':
            return constant.QT_ODIN_5x5_DRAFT
        if type == 'BOT_5x5':
            return constant.QT_BOT_5x5
        if type == 'BOT_ODIN_5x5':
            return constant.QT_BOT_ODIN_5x5
        if type == 'BOT_5x5_INTRO':
            return constant.QT_BOT_5x5_INTRO
        if type == 'BOT_5x5_BEGINNER':
            return constant.QT_BOT_5x5_BEGINNER
        if type == 'BOT_5x5_INTERMEDIATE':
            return constant.QT_BOT_5x5_INTERMEDIATE
        if type == 'BOT_TT_3x3':
            return constant.QT_BOT_TT_3x3
        if type == 'GROUP_FINDER_5x5':
            return constant.QT_GROUP_FINDER_5x5
        if type == 'ARAM_5x5':
            return constant.QT_ARAM_5x5
        if type == 'ONEFORALL_5x5':
            return constant.QT_ONEFORALL_5x5
        if type == 'FIRSTBLOOD_1x1':
            return constant.QT_FIRSTBLOOD_1x1
        if type == 'FIRSTBLOOD_2x2':
            return constant.QT_FIRSTBLOOD_2x2
        if type == 'SR_6x6':
            return constant.QT_SR_6x6
        if type == 'URF_5x5':
            return constant.QT_URF_5x5
        if type == 'ONEFORALL_MIRRORMODE_5x5':
            return constant.QT_ONEFORALL_MIRRORMODE_5x5
        if type == 'BOT_URF_5x5':
            return constant.QT_BOT_URF_5x5
        if type == 'NIGHTMARE_BOT_5x5_RANK1':
            return constant.QT_NIGHTMARE_BOT_5x5_RANK1
        if type == 'NIGHTMARE_BOT_5x5_RANK2':
            return constant.QT_NIGHTMARE_BOT_5x5_RANK2
        if type == 'NIGHTMARE_BOT_5x5_RANK5':
            return constant.QT_NIGHTMARE_BOT_5x5_RANK5
        if type == 'ASCENSION_5x5':
            return constant.QT_ASCENSION_5x5
        if type == 'HEXAKILL':
            return constant.QT_HEXAKILL
        if type == 'BILGEWATER_ARAM_5x5':
            return constant.QT_BILGEWATER_ARAM_5x5
        if type == 'KING_PORO_5x5':
            return constant.QT_KING_PORO_5x5
        if type == 'COUNTER_PICK':
            return constant.QT_COUNTER_PICK
        if type == 'BILGEWATER_5x5':
            return constant.QT_BILGEWATER_5x5
        if type == 'SIEGE':
            return constant.QT_SIEGE
        if type == 'DEFINITELY_NOT_DOMINION_5x5':
            return constant.QT_DEFINITELY_NOT_DOMINION_5x5
        if type == 'TEAM_BUILDER_DRAFT_UNRANKED_5x5':
            return constant.QT_TEAM_BUILDER_DRAFT_UNRANKED_5x5
        if type == 'TEAM_BUILDER_DRAFT_RANKED_5x5':
            return constant.QT_TEAM_BUILDER_DRAFT_RANKED_5x5
        
        raise TypeConvertError("queue type conversion fail")
    def season_int_convertor(self, season):
        if season == constant.SEASON2013:
            return 3
        elif season == constant.SEASON2014:
            return 4
        elif season == constant.SEASON2015:
            return 5
        elif season == constant.SEASON2016:
            return 6
        
        raise TypeConvertError("season int conversion fail")
    
    def int_season_convertor(self, int):
        if int == 3:
            return constant.SEASON2013
        elif int == 4:
            return constant.SEASON2014
        elif int == 5:
            return constant.SEASON2015
        elif int == 6:
            return constant.SEASON2016
        
        raise TypeConvertError("int season conversion fail")
    
    def event_type_convertor(self, type):
        if type == 'BUILDING_KILL':
            return constant.ET_BUILDING_KILL
        if type == 'CHAMPION_KILL':
            return constant.ET_CHAMPION_KILL
        if type == 'ELITE_MONSTER_KILL':
            return constant.ET_ELITE_MONSTER_KILL
        if type == 'WARD_KILL':
            return constant.ET_WARD_KILL
        if type == 'WARD_PLACED':
            return constant.ET_WARD_PLACED
        if type == 'ITEM_DESTROYED':
            return constant.ET_ITEM_DESTROYED
        if type == 'ITEM_PURCHASED':
            return constant.ET_ITEM_PURCHASED
        if type == 'ITEM_SOLD':
            return constant.ET_ITEM_SOLD
        if type == 'ITEM_UNDO':
            return constant.ET_ITEM_UNDO
        if type == 'SKILL_LEVEL_UP':
            return constant.ET_SKILL_LEVEL_UP
        
        raise TypeConvertError("event type conversion fail")
        
    def building_type_convertor(self, type):
        if type == 'TOWER_BUILDING':
            return constant.BT_TOWER_BUILDING
        if type == 'INHIBITOR_BUILDING':
            return constant.BT_INHIBITOR_BUILDING
        
        raise TypeConvertError("building type conversion fail")
    
    
    def tower_type_convertor(self, type):
        if type == 'OUTER_TURRET':
            return constant.TT_OUTER_TURRET
        if type == 'INNER_TURRET':
            return constant.TT_INNER_TURRET
        if type == 'BASE_TURRET':
            return constant.TT_BASE_TURRET
        if type == 'NEXUS_TURRET':
            return constant.TT_NEXUS_TURRET
        if type == 'UNDEFINED_TURRET':
            return constant.TT_UNDEFINED_TURRET
        
        raise TypeConvertError("tower type conversion fail")
    
    def lane_type_convertor(self, type):
        if type == 'TOP_LANE':
            return constant.LT_TOP_LANE
        if type == 'MID_LANE':
            return constant.LT_MID_LANE
        if type == 'BOT_LANE':
            return constant.LT_BOT_LANE
        
        raise TypeConvertError("lane type conversion fail")
    
    def monster_type_convertor(self, type):
        if type == 'BLUE_GOLEM':
            return constant.MT_BLUE_GOLEM
        if type == 'RED_LIZARD':
            return constant.MT_RED_LIZARD
        if type == 'DRAGON':
            return constant.MT_DRAGON
        if type == 'BARON_NASHOR':
            return constant.MT_BARON_NASHOR
        if type == 'VILEMAW':
            return constant.MT_VILEMAW
        
        raise TypeConvertError("monster type conversion fail")
    
    def ward_type_convertor(self, type):
        if type == 'SIGHT_WARD':
            return constant.WT_SIGHT_WARD
        if type == 'VISION_WARD':
            return constant.WT_VISION_WARD
        if type == 'YELLOW_TRINKET':
            return constant.WT_YELLOW_TRINKET
        if type == 'YELLOW_TRINKET_UPGRADE':
            return constant.WT_YELLOW_TRINKET_UPGRADE
        if type == 'TEEMO_MUSHROOM':
            return constant.WT_TEEMO_MUSHROOM
        if type == 'UNDEFINED':
            return constant.WT_UNDEFINED
        
        raise TypeConvertError("ward type conversion fail")
    
    def lane_convertor(self, type):
        if type == 'TOP':
            return constant.L_TOP
        if type == 'JUNGLE':
            return constant.L_JUNGLE
        if type == 'MIDDLE':
            return constant.L_MIDDLE
        if type == 'BOTTOM':
            return constant.L_BOTTOM
        
        raise TypeConvertError("lane conversion fail")
    
    def role_convertor(self, type):
        if type == 'DUO':
            return constant.R_DUO
        if type == 'NONE':
            return constant.R_NONE
        if type == 'SOLO':
            return constant.R_SOLO
        if type == 'DUO_CARRY':
            return constant.R_DUO_CARRY
        if type == 'DUO_SUPPORT':
            return constant.R_DUO_SUPPORT
        
        raise TypeConvertError("role conversion fail")
    
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
    def __init__(self, module, trial=C_SUMMONER_TRY):
        self.module = module
        self.api = module.api
        self.db = connector.PentakillDB()
        self.trial = trial
        self.data = {}
        
        self.debug = False
        
    def init(self):
        try:
            self.db.init()
            cursor = self.db.query("set names utf8; set AUTOCOMMIT=0;", multi=True, buffered=False)
            cursor.close()
        except error.Error as e:
            raise DBError(str(e))
        except Exception as e:
            raise UnknownError(str(e))
        
        
    # puts dictionary 'data' containing data for update
    # data can be accessed from self.data in _update method
    # data is shallow copied.
    def put_data(self, data):
        self.data = data.copy()
        
    # pentakill generic update routine
    # returns true for success, raise Error for failure
    def update(self):
        trial = 0
        import traceback
        while True:
            try:
                self.db.begin()
                self._update()
            except (Error, error.Error, Exception) as err:
                traceback.print_exc()
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
                    if not self.debug:
                        self.db.commit()
                    else:
                        print 'debug : rollback'
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
        
    def _wait_target_response(self, respond, list):
        try:
            ret = respond.wait_target_response(list, T_WAIT)
        except lolfastapi.TimeoutError:
            raise APITimeout("Sever do not respond too long")
        else:
            return ret

    def _check_response(self, res, notfound=True):
        if res[0] == lolfastapi.FS_TIMEOUT:
            raise APITimeout("Sever do not respond too long")
        elif res[0] == lolfastapi.FS_SERVICE_UNAVAILABLE:
            raise APIUnavailable("Server is not available now")
        elif res[0] != lolfastapi.FS_OK:
            raise APIError("Problem with API server")
        
        sc = res[1][0][0]
        if notfound and sc == config.SC_NOT_FOUND:
            raise NotFoundError("Cannot find such summoner")
        elif sc != config.SC_OK and sc != config.SC_NOT_FOUND:
            raise APIError("Bad status code")
            
        return sc == config.SC_OK
    
    # level is boolean. If True, enable debug mode
    # In debug mode, update is not committed
    def set_debug(self, level=True):
        self.debug = level
        
# Update summoner data by id or name
# data dictionary must contain "id" or "name" key
# at least one of two must be given.
# If both are given, "id" is used to identify summoner
# Update speed is much faster when id is given
# name : string, unicode encoded string name
# id : int, summoner id
class SummonerUpdator(PentakillUpdator):
    def __init__(self, module):
        PentakillUpdator.__init__(self, module, C_SUMMONER_TRY)
    
    def _update(self):
        self.data['season'] = season = Util.season_int_convertor(config.SEASON)
        if 'id' in self.data:
            id = self.data['id']
            res = self._get_api_response(summoner_by_id=True)
            ret = self._wait_target_response(res, ['summoner'])
            self._check_response(ret[1])
            name, dat = ret[0], ret[1][1][1]
            self.data[name] = dat[str(id)]
            self._update_summoner()
        elif 'name' in self.data:
            self._get_summoner_data_by_name()
            self._update_summoner()
            res = self._get_api_response()
        else:
            raise InvalidArgumentError("id or name must be given")
        
        target = ['leagues', 'stats', 'games', 'rank']
        while True:
            ret = self._wait_target_response(res, target)
            if not ret:
                break
            name, dat = ret[0], ret[1][1][1]
            if not self._check_response(ret[1], notfound=False):
                continue
            self.data[name] = dat
            if name == 'leagues':
                self._update_leagues()
            elif name == 'stats':
                self._update_stats()
            elif name == 'games':
                self._update_games()
            elif name == 'rank':
                self._update_rank_champions()
            else:
                raise UnknownError('unknown request name')
                
        self.module.orderRuneMasteryUpdate(self.data['id'])
        return True
    
    def _get_api_response(self, summoner_by_id=False):
        id = self.data['id']
        
        reqs = lolfastapi.FastRequest()
        if summoner_by_id:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_ids, (id,)))        
        reqs.add_request_name('leagues', (lolapi.LOLAPI.get_league_entries, (id,)))
        reqs.add_request_name('games', (lolapi.LOLAPI.get_recent_games, (id,)))
        reqs.add_request_name('stats', (lolapi.LOLAPI.get_stats_summary, (id,)))
        reqs.add_request_name('rank', (lolapi.LOLAPI.get_rank_stats, (id,)))
        
        response = self.api.get_multiple_data(reqs)
        return response
    
    def _old_update(self):
        self.data['season'] = season = Util.season_int_convertor(config.SEASON)
        if 'id' in self.data:
            print 'id'
            self._get_api_data(summoner_by_id=True)
            self._update_summoner()
        elif 'name' in self.data:
            print 'name'
            self._get_summoner_data_by_name()
            self._update_summoner()
            self._get_api_data()
        else:
            raise InvalidArgumentError("id or name must be given")
        self._update_leagues()
        self._update_stats()
        self._update_games()
        self._update_rank_champions()
        self.module.orderRuneMasteryUpdate(self.data['id'])
        return True
    
    def _get_api_data(self, summoner_by_id=False):
        id = self.data['id']
        
        reqs = lolfastapi.FastRequest()
        if summoner_by_id:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_ids, (id,)))
        reqs.add_request_name('leagues', (lolapi.LOLAPI.get_league_entries, (id,)))
        reqs.add_request_name('games', (lolapi.LOLAPI.get_recent_games, (id,)))
        reqs.add_request_name('stats', (lolapi.LOLAPI.get_stats_summary, (id,)))
        reqs.add_request_name('rank', (lolapi.LOLAPI.get_rank_stats, (id,)))
        
        response = self.api.get_multiple_data(reqs)
        self._wait_response(response)
                
        for name, res in response:
            #print name, res
            if self._check_response(res, notfound=False):
                if name == 'summoner':
                    #print res
                    self.data[name] = res[1][1][str(id)]
                else:
                    self.data[name] = res[1][1]
                    
    def _get_summoner_data_by_name(self):
        data = self.data
        name = Util.transform_names(data['name'])
        data['name'] = name
        
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_names, (name,)))
        
        response = self.api.get_multiple_data(reqs)
        self._wait_response(response)
        res = response.get_response('summoner')
        
        self._check_response(res)
        #print res
        data['summoner'] = res[1][1][name.decode('utf8')]
        
    def _get_summoner_data_by_id(self):
        data = self.data
        id = data['id']
        
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_ids, (id,)))
        
        response = self.api.get_multiple_data(reqs)
        self._wait_response(response)
        res = response.get_response('summoner')
        
        self._check_response(res)
        #print res
        data['summoner'] = res[1][1][str(id)]
        
    def _update_summoner(self):
        while True:
            apidat = self.data['summoner']
            
            id = apidat['id']
            name = apidat['name'].encode('utf8')
            nameAbbre = Util.abbre_names(name)
            profileIconId = apidat["profileIconId"]
            summonerLevel = apidat["summonerLevel"]
            revisionDate = int(apidat["revisionDate"] / 1000)
            
            print name.decode('utf8').encode('cp949')
            print (id, profileIconId, summonerLevel, revisionDate)            
            
            result = self.db.query("select s_id, last_update "
                                   "from summoners where s_name_abbre = %s and live = 1", (nameAbbre,))
            row = result.fetchRow()
            result.close()
            #print row
            if row:
                #print row[1], revisionDate
                self.data['epoch'] = row[1]
                if row[0] != id:
                    # set current one to dead summoner
                    self.db.query("update summoners set live = 0 where s_id = %s", (row[0],)).close()
                    print "dead summoner found"
                elif row[1] >= revisionDate:
                    query = (("update summoners "
                              "set last_update = UNIX_TIMESTAMP(now()), "
                              "level = %s, "
                              "s_icon = %s "
                              "where s_id = %s"))
                    print 'summoner up to date'
                    self.db.query(query, (summonerLevel, profileIconId, id)).close()
                    break
            else:
                print "row not found"
            
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
            break
        
        # data update
        self.data['id'] = id
                
    def _update_leagues(self):
        id = self.data['id']
        if not 'leagues' in self.data:
            return
        apidat = self.data['leagues'][str(id)]
        #print apidat
        
        query1 = ("insert into tier_transition (s_id, tier, division, lp, time) "
                  "values (%s, %s, %s, %s, UNIX_TIMESTAMP(now()))")
        # insert league data
        query2 = ("insert into league (s_id, league_id, player_or_team_name, "
                  "queue, name, tier, division, lp, is_fresh, is_inactive, is_veteran, "
                  "is_hot_streak, is_in_mini_series, wins, losses, target) "
                  "values (%s, %s , %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                  "on duplicate key update "
                  "player_or_team_name = values(player_or_team_name),"
                  "queue = values(queue),"
                  "name = values(name),"
                  "tier = values(tier),"
                  "division = values(division),"
                  "lp = values(lp),"
                  "is_fresh = values(is_fresh),"
                  "is_inactive = values(is_inactive),"
                  "is_veteran = values(is_veteran),"
                  "is_hot_streak = values(is_hot_streak),"
                  "is_in_mini_series = values(is_in_mini_series),"
                  "wins = values(wins),"
                  "losses = values(losses),"
                  "target = values(target)")        
        leagueId = 1
        for dic in apidat:
            queue = Util.league_queue_convertor(dic['queue'])
            if queue != constant.S_RANKED_SOLO_5x5:
                continue
            entry = dic['entries'][0]
            tier = dic['tier'].encode('utf8')
            leagueName = dic['name']
            division = Util.league_division_convertor(entry['division'])
            playerOrTeamName = entry['playerOrTeamName']
            point = entry['leaguePoints']
            fresh = entry['isFreshBlood'] if 'isFreshBlood' in entry else None
            inactive = entry['isInactive'] if 'isInactive' in entry else None
            hotStreak = entry['isHotStreak'] if 'isHotStreak' in entry else None
            veteran = entry['isVeteran'] if 'isVeteran' in entry else None
            miniSeries = entry['miniSeries'] if 'miniSeries' in entry else None
            isMiniSeries = False
            miniSeriesWins = None
            miniSeriesLosses = None
            miniSeriesTarget = None
            if miniSeries:
                isMiniSeries = True
                miniSeriesWins = miniSeries['wins'] if 'wins' in miniSeries else 0
                miniSeriesLosses = miniSeries['losses'] if 'losses' in miniSeries else 0
                miniSeriesTarget = miniSeries['target'] if 'target' in miniSeries else 0
            
            # tier transition update
            if queue == constant.S_RANKED_SOLO_5x5:
                self.db.query(query1, (id, tier, division, point)).close()
            
            arg = (id, leagueId, playerOrTeamName, queue, leagueName, tier, division,
                   point, fresh, inactive, veteran, hotStreak, isMiniSeries,
                   miniSeriesWins, miniSeriesLosses, miniSeriesTarget)
            
            self.db.query(query2, arg).close()
            # increment league id
            leagueId += 1
            
        # delete old data
        query = ("delete from league "
                 "where s_id = %s and league_id >= %s")
        self.db.query(query, (id, leagueId)).close()
        
        
    def _update_stats(self):
        id = self.data['id']
        if not 'stats' in self.data:
            return
        apidat = self.data['stats']
        #print apidat
        stats = apidat['playerStatSummaries']
        season = self.data['season']
        query = ("insert into stats (s_id, season, sub_type, win, lose) "
                 "values (%s, %s, %s, %s, %s) "
                 "on duplicate key update "
                 "win = values(win),"
                 "lose = values(lose)")   
        for stat in stats:
            modifyDate = int(stat['modifyDate'] / 1000)
            playerStatSummaryType = Util.player_stat_summary_type_convertor(
                stat['playerStatSummaryType'])
            wins = stat['wins'] if 'wins' in stat else None
            losses = stat['losses'] if 'losses' in stat else None
            
            arg = (id, season, playerStatSummaryType, wins, losses)
            self.db.query(query, arg).close()      

    def _update_games(self):
        id = self.data['id']
        if not 'games' in self.data:
            return
        apidat = self.data['games']
        #print apidat['games'][0]
        season = self.data['season']
        
        query1 = ("insert into games (game_id, create_date, time_played, "
                  "game_mode, game_type, sub_type) "
                  "values (%s, %s, %s, %s, %s, %s) "
                  "on duplicate key update "
                  "game_id = values(game_id)")
        ss = '%s, ' * 40
        # Game detail update
        query2 = ("insert into game_detail ( "
                  "s_id, game_id, champion_id, team_id, ip_earned, is_win, "
                  "spell1, spell2, level, item0, item1, item2, item3, item4, "
                  "item5, item6, gold, minions_killed, neutral_killed_your_jungle, "
                  "neutral_killed_enemy_jungle, kills, death, assist, "
                  "physical_damage_to_champions, magic_damage_to_champions, "
                  "true_damage_to_champions, total_damage_dealt, "
                  "physical_damage_taken, magic_damage_taken, true_damage_taken, "
                  "sightwards_bought, visionwards_bought, ward_placed, "
                  "ward_killed, double_kills, triple_kills, quadra_kills, "
                  "penta_kills, unreal_kills, season, lane, role) "
                  "values ({0}null, null) "
                  "on duplicate key update "
                  "s_id = values(s_id), "
                  "game_id = values(game_id)").format(*(ss,))
        # Fellow update
        query3 = ("insert into game_fellows values (%s, %s, %s, %s) "
                  "on duplicate key update "
                  "game_id = values(game_id),"
                  "s_id = values(s_id)")
        for game in apidat['games']:
            stats = game['stats']
            fellows = game['fellowPlayers'] if 'fellowPlayers' in game else None
            #print game
            gameId = game['gameId']
            championId = game['championId']
            createDate = int(game['createDate'] / 1000)
            gameMode = Util.game_mode_convertor(game['gameMode'])
            gameType = Util.game_type_convertor(game['gameType'])
            subType = Util.subtype_convertor(game['subType'])
            teamId = game['teamId']
            ipEarned = game['ipEarned']
            spell1 = game['spell1']
            spell2 = game['spell2']
            level = stats['level']
            gold = stats['goldEarned']
            minionsKilled = stats['minionsKilled'] if 'minionsKilled' in stats else 0
            neutralYourJungle = stats['neutralYourJungle'] if 'neutralYourJungle' in stats else 0
            neutralEnemyJungle = stats['neutralEnemyJungle'] if 'neutralEnemyJungle' in stats else 0
            championsKilled = stats['championsKilled'] if 'championsKilled' in stats else 0
            numDeaths = stats['numDeaths'] if 'numDeaths' in stats else 0
            assists = stats['assists'] if 'assists' in stats else 0
            physicalDamageDealtToChampions = stats['physicalDamageDealtToChampions'] if 'physicalDamageDealtToChampions' in stats else 0
            magicDamageDealtToChampions = stats['magicDamageDealtToChampions'] if 'magicDamageDealtToChampions' in stats else 0
            trueDamageDealtToChampions = stats['trueDamageDealtToChampions'] if 'trueDamageDealtToChampions' in stats else 0
            totalDamageDealt = stats['totalDamageDealt'] if 'totalDamageDealt' in stats else 0
            physicalDamageTaken = stats['physicalDamageTaken'] if 'physicalDamageTaken' in stats else 0
            magicDamageTaken = stats['magicDamageTaken'] if 'magicDamageTaken' in stats else 0
            trueDamageTaken = stats['trueDamageTaken'] if 'trueDamageTaken' in stats else 0
            sightWardsBought = stats['sightWardsBought'] if 'sightWardsBought' in stats else 0
            visionWardsBought = stats['visionWardsBought'] if 'visionWardsBought' in stats else 0
            wardPlaced = stats['wardPlaced'] if 'wardPlaced' in stats else 0
            wardKilled = stats['wardKilled'] if 'wardKilled' in stats else 0
            item0 = stats['item0'] if 'item0' in stats else None
            item1 = stats['item1'] if 'item1' in stats else None
            item2 = stats['item2'] if 'item2' in stats else None
            item3 = stats['item3'] if 'item3' in stats else None
            item4 = stats['item4'] if 'item4' in stats else None
            item5 = stats['item5'] if 'item5' in stats else None
            item6 = stats['item6'] if 'item6' in stats else None
            doubleKills = stats['doubleKills'] if 'doubleKills' in stats else 0
            tripleKills = stats['tripleKills'] if 'tripleKills' in stats else 0
            quadraKills = stats['quadraKills'] if 'quadraKills' in stats else 0
            pentaKills = stats['pentaKills'] if 'pentaKills' in stats else 0
            unrealKills = stats['unrealKills'] if 'unrealKills' in stats else 0
            timePlayed = stats['timePlayed']
            win = stats['win']
            
            # Games table update
            ##query = ("insert into games (game_id, create_date, time_played, "
                     ##"game_mode, game_type, sub_type) "
                     ##"select * from ( "
                     ##"select %s as id, %s as create_date, %s as time_played,"
                     ##"%s as game_mode, %s as game_type, %s as sub_type) AS tmp "
                     ##"where not exists ( "
                     ##"select game_id from games where game_id = %s LIMIT 1)")
        
            args = (gameId, createDate, timePlayed, gameMode, gameType, subType)
            self.db.query(query1, args).close()
            
            args = (id, gameId, championId, teamId, ipEarned, win, spell1, spell2,
                    level, item0, item1, item2, item3, item4, item5, item6, gold,
                    minionsKilled, neutralYourJungle, neutralEnemyJungle,
                    championsKilled, numDeaths, assists, physicalDamageDealtToChampions,
                    magicDamageDealtToChampions, trueDamageDealtToChampions,
                    totalDamageDealt, physicalDamageTaken, magicDamageTaken,
                    trueDamageTaken, sightWardsBought, visionWardsBought,
                    wardPlaced, wardKilled, doubleKills, tripleKills, quadraKills,
                    pentaKills, unrealKills, season)
            
            #print query % args
            self.db.query(query2, args).close()
            
            args = (gameId, id, teamId, championId)
            self.db.query(query3, args).close()
            if fellows is None:
                return
            for fellow in fellows:
                fellowId = fellow['summonerId']
                fellowTeamId = fellow['teamId']
                fellowChampionId = fellow['championId']
                args = (gameId, fellowId, fellowTeamId, fellowChampionId)
                self.db.query(query3, args).close()
    
    def _update_rank_champions(self):
        id = self.data['id']
        if not 'rank' in self.data:
            return
        apidat = self.data['rank']
        champions = apidat['champions']
        modifyDate = apidat['modifyDate']
        if 'epoch' in self.data and self.data['epoch'] > modifyDate:
            return
        
        season = self.data['season']
        ss = '%s, ' * 16 + "%s"
        query = ("insert into rank_most_champions (s_id, champion_id, season, "
                 "total_sessions_played, total_sessions_won, total_sessions_lost, "
                 "total_champion_kills, total_deaths, total_assists, "
                 "total_gold_earned, total_minion_kills, total_neutral_minions_killed, "
                 "total_double_kills, total_triple_kills, total_quadra_kills, "
                 "total_penta_kills, total_unreal_kills) "
                 "values ({0}) "
                 "on duplicate key update "
                 "total_sessions_played = values(total_sessions_played),"
                 "total_sessions_won = values(total_sessions_won),"
                 "total_sessions_lost = values(total_sessions_lost),"
                 "total_champion_kills = values(total_champion_kills),"
                 "total_deaths = values(total_deaths),"
                 "total_assists = values(total_assists),"
                 "total_gold_earned = values(total_gold_earned),"
                 "total_minion_kills = values(total_minion_kills),"
                 "total_neutral_minions_killed = values(total_neutral_minions_killed),"
                 "total_double_kills = values(total_double_kills),"
                 "total_triple_kills = values(total_triple_kills),"
                 "total_quadra_kills = values(total_quadra_kills),"
                 "total_penta_kills = values(total_penta_kills),"
                 "total_unreal_kills = values(total_unreal_kills)").format(*(ss,))        
        for champion in champions:
            stats = champion['stats']
            championId = champion['id']
            if championId < 1:
                continue
            
            totalSessionsPlayed = stats['totalSessionsPlayed'] if 'totalSessionsPlayed' in stats else 0
            totalSessionsWon = stats['totalSessionsWon'] if 'totalSessionsWon' in stats else 0
            totalSessionsLost = stats['totalSessionsLost'] if 'totalSessionsLost' in stats else 0
            totalChampionKills = stats['totalChampionKills'] if 'totalChampionKills' in stats else 0
            totalDeathsPerSession = stats['totalDeathsPerSession'] if 'totalDeathsPerSession' in stats else 0
            totalAssists = stats['totalAssists'] if 'totalAssists' in stats else 0
            totalGoldEarned = stats['totalGoldEarned'] if 'totalGoldEarned' in stats else 0
            totalMinionKills = stats['totalMinionKills'] if 'totalMinionKills' in stats else 0
            totalNeutralMinionsKilled = stats['totalNeutralMinionsKilled'] if 'totalNeutralMinionsKilled' in stats else 0
            totalDoubleKills = stats['totalDoubleKills'] if 'totalDoubleKills' in stats else 0
            totalTripleKills = stats['totalTripleKills'] if 'totalTripleKills' in stats else 0
            totalQuadraKills = stats['totalQuadraKills'] if 'totalQuadraKills' in stats else 0
            totalPentaKills = stats['totalPentaKills'] if 'totalPentaKills' in stats else 0
            totalUnrealKills = stats['totalUnrealKills'] if 'totalUnrealKills' in stats else 0
            
            args = (id, championId, season, totalSessionsPlayed, totalSessionsWon,
                    totalSessionsLost, totalChampionKills, totalDeathsPerSession,
                    totalAssists, totalGoldEarned, totalMinionKills,
                    totalNeutralMinionsKilled, totalDoubleKills, totalTripleKills,
                    totalQuadraKills, totalPentaKills, totalUnrealKills)
            self.db.query(query, args).close()
    

# id : summoner id
class RuneMasteryUpdator(PentakillUpdator):
    def __init__(self, module):
        PentakillUpdator.__init__(self, module, C_SUMMONER_TRY)
        
    def _update(self):
        self._get_api_data()
        self._update_runes()
        self._update_masteries()
        #print 'rune mastery updata success'
        return True
        
    def _get_api_data(self):
        id = self.data['id']
        
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('runes', (lolapi.LOLAPI.get_summoner_runes, (id,)))
        reqs.add_request_name('masteries', (lolapi.LOLAPI.get_summoner_masteries, (id,)))
        
        response = self.api.get_multiple_data(reqs)
        self._wait_response(response)
                
        for name, res in response:
            #print name, res
            if self._check_response(res, notfound=False):
                self.data[name] = res[1][1]
        
    def _update_runes(self):
        id = self.data['id']
        apidat = self.data['runes']
        pages = apidat[str(id)]['pages']
        pageNumber = 1
        query1 = ("insert into runes (s_id, page_id, page_number, page_name, current) "
                  "values (%s, %s, %s, %s, %s) "
                  "on duplicate key update "
                  "page_number = values(page_number), "
                  "page_name = values(page_name), "
                  "current = values(current)")
        query2 = ("update rune_slots set rune_id = null where page_id = %s")
        query3 = ("insert into rune_slots (page_id, slot_id, rune_id) "
                  "values (%s, %s, %s) "
                  "on duplicate key update "
                  "rune_id = values(rune_id)")
        query4 = ("delete from runes where s_id = %s and not find_in_set(page_id, %s)")
        pids = []
        for page in pages:
            pageId = page['id']
            name = page['name']
            slots = page['slots'] if 'slots' in page else None
            current = page['current']
            
            pids.append(pageId)
            
            args = (id, pageId, pageNumber, name, current)
            self.db.query(query1, args).close()
            pageNumber += 1
            
            self.db.query(query2, (pageId,)).close()
            if not slots:
                continue
            for slot in slots:
                runeId = slot['runeId']
                slotId = slot['runeSlotId']
                
                args = (pageId, slotId, runeId)
                self.db.query(query3, args).close()
            
        # Entries in mastery slots will be deleted automatically by foriegn key 
        # cascading
        #print str(pids)[1:-1]
        self.db.query(query4, (id, str(pids)[1:-1].replace(' ', ''))).close()
        
    def _update_masteries(self):
        id = self.data['id']
        apidat = self.data['masteries']
        pages = apidat[str(id)]['pages']
        pageNumber = 1
        query1 = ("insert into masteries (s_id, page_id, page_number, "
                  "page_name, current) "
                  "values (%s, %s, %s, %s, %s) "
                  "on duplicate key update "
                  "page_number = values(page_number),"
                  "page_name = values(page_name),"
                  "current = values(current)")
        query2 = ("update mastery_slots set rank = 0 where page_id = %s")
        query3 = ("insert into mastery_slots (page_id, mastery_id, rank) "
                  "values (%s, %s, %s) "
                  "on duplicate key update "
                  "rank = values(rank)")
        query4 = ("delete from masteries where s_id = %s and not find_in_set(page_id, %s)")
        pids = []
        for page in pages:
            name = page['name']
            pageId = page['id']
            masteries = page['masteries'] if 'masteries' in page else None
            current = page['current']
            
            pids.append(pageId)
            
            args = (id, pageId, pageNumber, name, current)
            self.db.query(query1, args).close()
            pageNumber += 1
            
            self.db.query(query2, (pageId,)).close()
            if not masteries:
                continue            
            for mastery in masteries:
                masteryId = mastery['id']
                rank = mastery['rank']
                
                args = (pageId, masteryId, rank)
                self.db.query(query3, args).close()
                
        self.db.query(query4, (id, str(pids)[1:-1].replace(' ', ''))).close()
    
# id : match id
class MatchUpdator(PentakillUpdator):
    def __init__(self, module):
        PentakillUpdator.__init__(self, module, C_SUMMONER_TRY)
        
    def _update(self):
        self._get_match_data()
        if not self._validate_match():
            raise UnsupportedMatchError('unsupported queue type')
        
        
        return True
    
    def _get_match_data(self):
        id = self.data['id']
        
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('match', (lolapi.LOLAPI.get_match, (id,)))
        
        response = self.api.get_multiple_data(reqs)
        self._wait_response(response)
                
        for name, res in response:
            #print name, res
            if self._check_response(res, notfound=False):
                self.data[name] = res[1][1]
                
    def _validate_match(self):
        apidat = self.data['match']
        queueType = apidat['queueType']
        queue = ([constant.QT_NORMAL_3x3,
                  constant.QT_NORMAL_5x5_BLIND,
                  constant.QT_NORMAL_5x5_DRAFT,
                  constant.QT_RANKED_SOLO_5x5,
                  constant.QT_RANKED_TEAM_3x3,
                  constant.QT_RANKED_TEAM_5x5,
                  constant.QT_BOT_5x5_INTRO,
                  constant.QT_BOT_5x5_BEGINNER,
                  constant.QT_BOT_5x5_INTERMEDIATE,
                  constant.QT_ARAM_5x5,
                  constant.QT_URF_5x5,
                  constant.QT_TEAM_BUILDER_DRAFT_UNRANKED_5x5,
                  constant.QT_TEAM_BUILDER_DRAFT_RANKED_5x5,])
        
        if type in queue:
            return True
        else:
            return False
        
    def _update_participants(self):
        apidata = self.data['match']
        
    def _update_teams(self):
        apidata = self.data['match']

    def _update_events(self):
        apidata = self.data['match']
        
    def _update_participant_frames(self):
            apidata = self.data['match']
    
'''
errno
'''
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

       
if __name__ == '__main__':
    import time
    module = UpdateModule()
    module.init() 
if __name__ == '__main__':
    print 'test match update'
    data = [{'id':2526543207}]
    
    for i in range(len(data)):
        if i > 0:
            time.sleep(10)        
        updator = module.getMatchUpdator()
        updator.init()
        updator.set_debug(True)
        #updator.put_data({"name":u'   \uba38 \ud53c   9  3'})
        #updator.put_data({"name":'zzz'})
        #updator.put_data({"name":u' cj entus \ubbfc\uae30'})
        updator.put_data(data[i])
        begin = time.time()
        updator.update()
        end = time.time()
        print end - begin, 'sec elapsed'
    print 'test passed'
    
if __name__ == '__main__':
    print 'test summoner update'
    data = [{'id':2060159}, {'name':'hide on bush', 'id':4460427}]
    
    for i in range(len(data)):
        if i > 0:
            time.sleep(10)        
        updator = module.getSummonerUpdator()
        updator.init()
        #updator.put_data({"name":u'   \uba38 \ud53c   9  3'})
        #updator.put_data({"name":'zzz'})
        #updator.put_data({"name":u' cj entus \ubbfc\uae30'})
        updator.put_data(data[i])
        begin = time.time()
        updator.update()
        end = time.time()
        print end - begin, 'sec elapsed'
    print 'test passed'

if __name__ == '__main__':
    module.close()