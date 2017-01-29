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

from pentakill.lolapi import lolapi, lolfastapi, config
from pentakill.db import connector
from pentakill.db import error as dbError
from pentakill.update import constant, util
from pentakill.lib import servant, progress_note, error
import threading, traceback

# Simple configuration
T_WAIT = 22.0      # timeout for api data

# Number of trial
C_SUMMONER_TRY = 1
C_RUNE_MASTERY_TRY = 1
C_MATCH_TRY = 1
C_CURRENT_GAME_TRY = 1

# Summoner update cooltime, in seconds
C_SUMMONER_UPDATE_RENEW_INTERVAL = 60.0

# Current game data refresh interval, in seconds
C_CURRENT_GAME_REFRESH_INTERVAL = 60.0

# Number of background updator(servants)
C_BG_UPDATOR_NUMBER = 5

Util = util.Utility()

class UpdateModule(object):
    def __init__(self):
        self.api = lolfastapi.LOLFastAPI()
        #self.api.set_debug(1)
        self.bg_num = C_BG_UPDATOR_NUMBER
        self.bg_next = 0
        self.bgs = []
        self.mutex = threading.Lock()
        self.policy = PentakillUpdatePolicy(self)
    
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
        
    def getPolicy(self):
        return self.policy
    
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
    def orderUpdate(self, updator):
        self._orderBgUpdator((self.CMD_UPDATE, updator))
        
    def orderRuneMasteryUpdate(self, id):
        self._orderBgUpdator((self.CMD_RUNEMASTERY, id))
        
    def _orderBgUpdator(self, arg):
        self.mutex.acquire()
        bg = self.bgs[self.bg_next]
        self.bg_next += 1
        self.bg_next %= self.bg_num
        bg.order(arg)
        self.mutex.release()
        
    # background updator commands
    CMD_EXIT = 0
    CMD_RUNEMASTERY = 1
    CMD_UPDATE = 2
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
                
                updator = None
                try:
                    cmd = req[0]
                    if cmd == self.module.CMD_EXIT:
                        return
                    elif cmd == self.module.CMD_RUNEMASTERY:
                        id = req[1]
                        updator = self.module.getRuneMasteryUpdator()
                        updator.init()
                        updator.put_data({'id':id})
                        updator.update()
                    elif cmd == self.module.CMD_UPDATE:
                        updator = req[1]
                        updator.update()
                    else:
                        continue
                except Exception:
                    traceback.print_exc()
                    pass
                finally:
                    if updator:
                        updator.close()
                        updator = None

class PentakillUpdatePolicy(object):
    def __init__(self, module):
        self.module = module
        
    def _get_db(self):
        db = connector.PentakillDB()
        db.init()
        db.begin()
        return db
    
    def check_summoner_update(self, id=None, name=None):
        db = self._get_db()
        query = ("select last_update, unix_timestamp(now()) "
                 "from summoners {0}")
        where1 = ("where s_id = %s")
        where2 = ("where s_name_abbre = %s")
        if id:
            result = db.query(query.format(*(where1,)), (id,))
        elif name:
            name = Util.transform_names(name)
            result = db.query(query.format(*(where2,)), (name,))
        else:
            raise error.InvalidArgumentError('id or name must be given')
        
        row = result.fetchRow()
        result.close()
        if row:
            last_update, cur = row
            if last_update:
                left = C_SUMMONER_UPDATE_RENEW_INTERVAL - cur + last_update
                left = left if left > 0 else 0
                if left > 0:
                    return (False, left, db)
                else:
                    return (True, left, db)
        
        return (True, None, db)
        
# Updator's initialize and finalize functions
class UpdatorInitFinal(object):
    def init(self, updator):
        self.updator = updator
        self.data = self.updator.get_data()
    
    def initialize(self):
        pass
    
    def finalize(self):
        pass

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
        self.db = None
        self.trial = trial
        self.data = None
        self.prog = progress_note.ProgressNote()
        
        self.debug = False
        
    def init(self, db=None, initfinal=None):
        try:
            self.data = {}
            
            self.initfinal = initfinal
                
            self.new_db = db is None
            self.db = connector.PentakillDB() if self.new_db else db
            if self.new_db:
                self.db.init()
                
            cursor = self.db.query("set names utf8; set AUTOCOMMIT=0;", 
                                   multi=True, buffered=False)
            cursor.close()
            self.prog.reset()
        except dbError.Error as e:
            raise error.DBError(str(e))
        except Exception as e:
            raise error.UnknownError(str(e))
        
    def get_initfinal(self):
        try:
            return self.initfinal
        except AttributeError:
            return None
        
    def get_progression(self):
        return self.prog.look()
    
    def completed(self):
        return self.prog.completed()
    
    # puts dictionary 'data' containing data for update
    # data can be accessed from self.data in _update method
    # data is shallow copied.
    def put_data(self, data):
        self.data = data.copy()
        
    def get_data(self):
        return self.data
        
    # pentakill generic update routine
    # returns true for success, raise error.Error for failure
    def update(self):
        trial = 0
        while True:
            try:
                if self.new_db:
                    self.db.begin()
                if self.initfinal:
                    self.initfinal.init(self)                    
                    self.initfinal.initialize()
                self._update()
            except (error.Error, dbError.Error, Exception) as err:
                traceback.print_exc()
                try:
                    raise err
                except error.Error as err:
                    errtmp = err
                except dbError.Error as err:
                    errtmp = DBError(str(err))
                except Exception as err:
                    errtmp = UnknownError(str(err))
                # rollback everything from here
                try:
                    self.db.rollback()
                    self._rollback()
                    if self.initfinal:
                        self.initfinal.rollback()
                except dbError.Error as err:
                    raise error.DBError(str(err))
                except Exception as err:
                    raise error.UnknownError(str(err))
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
                        if self.initfinal:
                            self.initfinal.finalize()
                    else:
                        print('debug : rollback')
                        self.db.rollback()
                        if self.initfinal:
                            self.initfinal.rollback()
                except dbError.Error as err:
                    raise error.DBError(str(err))
                except Exception as err:
                    raise error.UnknownError(str(err))
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
        if self.db:
            self.db.close()
            self.db = None
        
    def _wait_response(self, respond):
        if not respond.wait_response(T_WAIT):
            raise error.APITimeout("Sever do not respond too long")
        
    def _wait_target_response(self, respond, list):
        try:
            ret = respond.wait_target_response(list, T_WAIT)
        except lolfastapi.TimeoutError:
            raise error.APITimeout("Sever do not respond too long")
        else:
            return ret
        
    # Check fastResponse response code and status code
    def _check_response(self, res, notfound=True):
        if res[0] == lolfastapi.FS_TIMEOUT:
            raise error.APITimeout("Sever do not respond too long")
        elif res[0] == lolfastapi.FS_SERVICE_UNAVAILABLE:
            raise error.APIUnavailable("Server is not available now")
        elif res[0] != lolfastapi.FS_OK:
            raise error.APIError("Problem with API server")
        
        sc = res[1][0][0]
        if notfound and sc == config.SC_NOT_FOUND:
            raise error.NotFoundError("Cannot find such summoner")
        elif sc != config.SC_OK and sc != config.SC_NOT_FOUND:
            raise error.APIError("Bad status code")
            
        return sc == config.SC_OK
    
    # level is boolean. If True, enable debug mode
    # In debug mode, update is not committed
    def set_debug(self, level=True):
        self.debug = level
        
    def _get_game_query(self):
        query1 = ("insert into games (game_id, create_date, time_played, "
                  "game_mode, game_type, sub_type) "
                  "values (%s, %s, %s, %s, %s, %s) "
                  "on duplicate key update "
                  "game_id = values(game_id)")
        return query1
    
    def _get_game_detail_query(self):
        ss = '%s' + ', %s'* 41
        # Game detail update
        query1 = ("insert into game_detail ( "
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
                  "values ({0}) "
                  "on duplicate key update "
                  "s_id = values(s_id), "
                  "game_id = values(game_id)").format(*(ss,))
        return query1
        
# Update summoner data by id or name
# data dictionary must contain "id" or "name" key
# at least one of two must be given.
# If both are given, "id" is used to identify summoner
# Update speed is much faster when id is given
# name : string, unicode encoded string name
# id : int, summoner id
class SummonerUpdator(PentakillUpdator):
    def __init__(self, module):
        super(SummonerUpdator, self).__init__(module, C_SUMMONER_TRY)
        
    def _rollback(self):
        data = {}
        if 'id' in self.data:
            data['id'] = self.data['id']
        elif 'name' in self.data:
            data['name'] = self.data['name']
        self.data = data
        
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
            raise error.InvalidArgumentError("id or name must be given")
        
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
                raise error.UnknownError('unknown request name')
                
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
            if name == 'summoner':
                if self._check_response(res):
                    self.data[name] = res[1][1][str(id)]
            elif self._check_response(res, notfound=False):
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
        
        data['summoner'] = res[1][1][name]
        
    def _update_summoner(self):
        while True:
            apidat = self.data['summoner']
            
            id = apidat['id']
            name = apidat['name']
            nameAbbre = Util.abbre_names(name)
            profileIconId = apidat["profileIconId"]
            summonerLevel = apidat["summonerLevel"]
            revisionDate = int(apidat["revisionDate"] / 1000)
            
            print(name)
            print((id, profileIconId, summonerLevel, revisionDate))
            
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
                    #print "dead summoner found"
                elif row[1] >= revisionDate:
                    query = (("update summoners "
                              "set last_update = UNIX_TIMESTAMP(now()), "
                              "level = %s, "
                              "s_icon = %s "
                              "where s_id = %s"))
                    #print 'summoner up to date'
                    self.db.query(query, (summonerLevel, profileIconId, id)).close()
                    break
            #else:
            #    print "row not found"
            
            # check if summoner name has been changed
            result = self.db.query("select s_name from summoners where s_id = %s", (id,))
            row = result.fetchRow()
            result.close()
            if row and row[0].encode('utf8') != name:
                #print "new name"
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
        
        query1 = ("insert into tier_transition (s_id, tier, division, lp, time) "
                  "values (%s, %s, %s, %s, UNIX_TIMESTAMP(now()))"
                  "on duplicate key update "
                  "s_id = values(s_id),"
                  "time = values(time)")
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
        
        stats = apidat['playerStatSummaries'] if 'playerStatSummaries' in apidat else None
        season = self.data['season']
        query = ("insert into stats (s_id, season, sub_type, win, lose) "
                 "values (%s, %s, %s, %s, %s) "
                 "on duplicate key update "
                 "win = values(win),"
                 "lose = values(lose)")
        
        if not stats:
            return
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
        
        season = self.data['season']
        
        query1 = self._get_game_query()
        # Game detail update
        query2 = self._get_game_detail_query()
        # Fellow update
        query3 = ("insert into game_fellows values (%s, %s, %s, %s) "
                  "on duplicate key update "
                  "game_id = values(game_id),"
                  "s_id = values(s_id)")
        for game in apidat['games']:
            stats = game['stats']
            fellows = game['fellowPlayers'] if 'fellowPlayers' in game else None
            
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
                    pentaKills, unrealKills, season, None, None)
            
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
        super(RuneMasteryUpdator, self).__init__(module, C_RUNE_MASTERY_TRY)
        
    def _rollback(self):
        data = {}
        if 'id' in self.data:
            data['id'] = self.data['id']
        self.data = data
        
    def _update(self):
        self._get_api_data()
        self._update_runes()
        self._update_masteries()
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
            name = page['name'] if 'name' in page else None
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
        self.db.query(query4, (id, Util.list_to_str(pids))).close()
        
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
            name = page['name'] if 'name' in page else None
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
                
        self.db.query(query4, (id, Util.list_to_str(pids))).close()
    
# id : match id
class MatchUpdator(PentakillUpdator):
    def __init__(self, module):
        super(MatchUpdator, self).__init__(module, C_MATCH_TRY)
        
    def _rollback(self):
        data = {}
        if 'id' in self.data:
            data['id'] = self.data['id']
        self.data = data
        
    def _update(self):
        self.data['season'] = season = Util.season_int_convertor(config.SEASON)
        if self._check_updated():
            return True
        self._get_match_data()
        if not self._validate_match():
            raise error.UnsupportedMatchError('unsupported queue type')
        self.data['matchId'] = self.data['match']['matchId']
        self._update_game()
        if not self.data['details_updated']:
            self._update_participants()
        self._update_teams()
        if not self.data['events_updated']:
            self._process_timeline()
            self._update_events()
            self._update_participant_frames()
        return True
    
    def _get_match_data(self):
        id = self.data['id']
        
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('match', (lolapi.LOLAPI.get_match, (id, 'true')))
        
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
                  #constant.QT_ARAM_5x5,
                  constant.QT_URF_5x5,
                  constant.QT_TEAM_BUILDER_DRAFT_UNRANKED_5x5,
                  constant.QT_TEAM_BUILDER_DRAFT_RANKED_5x5,
                  constant.QT_TEAM_BUILDER_RANKED_SOLO])
        
        if Util.queue_type_convertor(queueType) in queue:
            return True
        else:
            return False
        
    # If game is not in table, add to games table
    def _update_game(self):
        apidat = self.data['match']
        matchId = self.data['matchId']
        
        # Here queueType is used to identify game type instead of subType
        query = ("insert into games (game_id, create_date, time_played, "
                 "game_mode, game_type, queue_type) "
                 "values (%s, %s, %s, %s, %s, %s) "
                 "on duplicate key update "
                 "game_id = values(game_id)")
        
        createDate = int(apidat['matchCreation'] / 1000)
        timePlayed = apidat['matchDuration']
        gameMode = Util.game_mode_convertor(apidat['matchMode'])
        gameType = Util.game_type_convertor(apidat['matchType'])
        queueType = Util.queue_type_convertor(apidat['queueType'])
        
        args = (matchId, createDate, timePlayed, gameMode, gameType, queueType)
        self.db.query(query, args).close()
        
    # Returns True if the match is not updated, False otherwise
    def _check_updated(self):
        ret = True
        
        query = ("select details_updated, events_updated "
                 "from games where game_id = %s")
        
        self.data['details_updated'] = False
        self.data['events_updated'] = False
        args = (self.data['id'],)
        while True:
            result = self.db.query(query, args)
            row = result.fetchRow()
            if not row:
                ret = False
                break
            detail, event = row[0], row[1]
            self.data['details_updated'] = True if detail else False
            self.data['events_updated'] = True if event else False
            if detail != 1 or event != 1:
                ret = False
                break
            break
        
        result.close()
        return ret
        
    def _update_participants(self):
        apidat = self.data['match']
        matchId = self.data['matchId']
        
        query1 = ("select s_id from summoners "
                  "where find_in_set(s_id, %s) and enrolled = 1 and live = 1")
        
        query2 = ("insert into game_participants (game_id, s_id, participant_id) "
                  "values (%s, %s, %s) "
                  "on duplicate key update "
                  "game_id = values(game_id),"
                  "s_id = values(s_id),"
                  "participant_id = values(participant_id)")
        
        query3 = self._get_game_detail_query()
        
        participants = apidat['participants']
        identities = apidat['participantIdentities']
        
        unknownSummoners = []
        for identity in identities:
            #print identity
            sId = identity['player']['summonerId']
            unknownSummoners.append(sId)
        
        ids = Util.list_to_str(unknownSummoners)
        result = self.db.query(query1, (ids,))
        
        for row in result:
            unknownSummoners.remove(row[0])
        
        result.close()
        
        # Update unknown summoners
        if len(unknownSummoners) > 0:
            self._update_unknown_summoners(unknownSummoners)
        
        season = self.data['season']
        # Match participant Id and summoner Id
        for identity in identities:
            sId = identity['player']['summonerId']
            pId1 = identity['participantId']
            for participant in participants:
                    pId2 = participant['participantId']
                    if pId1 != pId2:
                        continue
                    # Update participant info
                    args = (matchId, sId, pId1)
                    self.db.query(query2, args).close()
                    
                    # Update game detail info
                    teamId = participant['teamId']
                    championId = participant['championId']
                    stats = participant['stats']
                    mastery = participant['masteries']
                    timeline = participant['timeline']
                    
                    teamId = participant['teamId']
                    spell1 = participant['spell1Id']
                    spell2 = participant['spell2Id']
                    level = stats['champLevel']
                    gold = stats['goldEarned']
                    minionsKilled = stats['minionsKilled'] if 'minionsKilled' in stats else 0
                    neutralYourJungle = stats['neutralMinionsKilledTeamJungle'] if 'neutralMinionsKilledTeamJungle' in stats else 0
                    neutralEnemyJungle = stats['neutralMinionsKilledEnemyJungle'] if 'neutralMinionsKilledEnemyJungle' in stats else 0
                    championsKilled = stats['kills'] if 'kills' in stats else 0
                    numDeaths = stats['deaths'] if 'deaths' in stats else 0
                    assists = stats['assists'] if 'assists' in stats else 0
                    physicalDamageDealtToChampions = stats['physicalDamageDealtToChampions'] if 'physicalDamageDealtToChampions' in stats else 0
                    magicDamageDealtToChampions = stats['magicDamageDealtToChampions'] if 'magicDamageDealtToChampions' in stats else 0
                    trueDamageDealtToChampions = stats['trueDamageDealtToChampions'] if 'trueDamageDealtToChampions' in stats else 0
                    totalDamageDealt = stats['totalDamageDealt'] if 'totalDamageDealt' in stats else 0
                    physicalDamageTaken = stats['physicalDamageTaken'] if 'physicalDamageTaken' in stats else 0
                    magicDamageTaken = stats['magicDamageTaken'] if 'magicDamageTaken' in stats else 0
                    trueDamageTaken = stats['trueDamageTaken'] if 'trueDamageTaken' in stats else 0
                    sightWardsBought = stats['sightWardsBoughtInGame'] if 'sightWardsBoughtInGame' in stats else 0
                    visionWardsBought = stats['visionWardsBoughtInGame'] if 'visionWardsBoughtInGame' in stats else 0
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
                    win = stats['winner']
                    lane = Util.lane_convertor(timeline['lane'])
                    role = Util.role_convertor(timeline['role'])
                    
                    args = (sId, matchId, championId, teamId, None, win, spell1, spell2,
                            level, item0, item1, item2, item3, item4, item5, item6, gold,
                            minionsKilled, neutralYourJungle, neutralEnemyJungle,
                            championsKilled, numDeaths, assists, physicalDamageDealtToChampions,
                            magicDamageDealtToChampions, trueDamageDealtToChampions,
                            totalDamageDealt, physicalDamageTaken, magicDamageTaken,
                            trueDamageTaken, sightWardsBought, visionWardsBought,
                            wardPlaced, wardKilled, doubleKills, tripleKills, quadraKills,
                            pentaKills, unrealKills, season, lane, role)
                    
                    self.db.query(query3, args).close()
                        
        # set details updated flag
        query = ("update games set details_updated = true where game_id = %s")
        self.db.query(query, (matchId,)).close()
            
    def _update_unknown_summoners(self, lids):
        #print 'update unknown summoners'
        
        query = ("insert into summoners (s_id, s_name, s_name_abbre, s_icon, level, last_update, enrolled, live) "
                 "values {0} "
                 "on duplicate key update "
                 "s_name = values(s_name), "
                 "s_name_abbre = values(s_name_abbre), "
                 "s_icon = values(s_icon), "
                 "level = values(level), "
                 "last_update = values(last_update), "
                 "enrolled = values(enrolled), "
                 "live = values(live)")
        
        ids = Util.list_to_str(lids)
        reqs = lolfastapi.FastRequest()
        reqs.add_request_name('summoners', (lolapi.LOLAPI.get_summoners_by_ids, (ids,)))
        
        response = self.api.get_multiple_data(reqs)
        self._wait_response(response)
        
        res = response.get_response('summoners')
        if self._check_response(res):
            unit = '(%s, %s, %s, %s, %s, UNIX_TIMESTAMP(now()), false, false)'
            form = unit + (', ' + unit) * (len(lids) - 1)
            largs = []
            for id in lids:
                summoner = res[1][1][str(id)]
                name = summoner['name']
                nameAbbre = Util.abbre_names(name)
                profileIconId = summoner["profileIconId"]
                summonerLevel = summoner["summonerLevel"]
                revisionDate = int(summoner["revisionDate"] / 1000)
                largs.append(id)
                largs.append(name)
                largs.append(nameAbbre)
                largs.append(profileIconId)
                largs.append(summonerLevel)
            args = tuple(largs)
            #print query.format(*(form,))
            #print args
            self.db.query(query.format(*(form,)), args).close()
    
    def _update_teams(self):
        apidat = self.data['match']
        matchId = self.data['matchId']
        
        ss = '%s' + ', %s' * 15
        query = ("insert into game_teams ("
                 "game_id, team_id, inhibitor_kills, tower_kills, first_tower, "
                 "first_blood, first_baron, first_inhibitor, first_dragon, "
                 "is_win, baron_kills, dragon_kills, vilemaw_kills, ban1, ban2, ban3) "
                 "values ({0}) "
                 "on duplicate key update "
                 "game_id = values(game_id),"
                 "team_id = values(team_id)").format(*(ss,))
        
        teams = apidat['teams']
        for team in teams:
            #print team
            teamId = team['teamId']
            firstTower = team['firstTower']
            firstBlood = team['firstBlood']
            firstBaron = team['firstBaron']
            firstInhibitor = team['firstInhibitor']
            firstDragon = team['firstDragon']
            winner = team['winner']
            
            vilemawKills = team['vilemawKills'] if 'vilemawKills' in team else 0
            baronKills = team['baronKills'] if 'baronKills' in team else 0
            dragonKills = team['dragonKills'] if 'dragonKills' in team else 0
            inhibitorKills = team['inhibitorKills'] if 'inhibitorKills' in team else 0
            towerKills = team['towerKills'] if 'towerKills' in team else 0
            
            bans = team['bans'] if 'bans' in team else None
            banList = [None for i in range(6)]
            if bans:
                for i in range(min(3, len(bans))):
                    pickTurn = bans[i]['pickTurn']
                    #print pickTurn
                    banList[pickTurn - 1] = bans[i]
                    
            banList.sort(key=lambda x: x['pickTurn'] if x is not None else 999)
            
            for i in range(len(banList)):
                if banList[i] is not None:
                    banList[i] = banList[i]['championId']
                #print banList[i]
            
            args = (matchId, teamId, inhibitorKills, towerKills, firstTower,
                    firstBlood, firstBaron, firstInhibitor, firstDragon, winner,
                    baronKills, dragonKills, vilemawKills, banList[0], banList[1],
                    banList[2])
            
            self.db.query(query, args).close()
            
    def _process_timeline(self):
        apidat = self.data['match']
        if not 'timeline' in apidat:
            return
        timeline = apidat['timeline']
        frames = timeline['frames']
        
        frames.sort(key=lambda x: x['timestamp'])
        self.data['timeline'] = timeline

    def _update_events(self):
        matchId = self.data['matchId']
        if not 'timeline' in self.data:
            return
        
        query1 = ("insert into game_events_buildings ("
                  "game_id, creator_id, timestamp, event_type, "
                  "killer_id, pos_x, pos_y, lane_type, building_type, tower_type) "
                  "values {0}")
        query2 = ("insert into game_events_kills ("
                  "game_id, creator_id, timestamp, event_type, "
                  "killer_id, victim_id, pos_x, pos_y) "
                  "values {0}")
        query3 = ("insert into game_events_monsters ("
                  "game_id, creator_id, timestamp, event_type, "
                  "killer_id, pos_x, pos_y, monster_type) "
                  "values {0}")
        query4 = ("insert into game_events_wards ("
                  "game_id, creator_id, timestamp, event_type, "
                  "killer_id, pos_x, pos_y, ward_type) "
                  "values {0}")
        query5 = ("insert into game_events_items ("
                  "game_id, creator_id, timestamp, event_type, "
                  "item_id, item_before, item_after) "
                  "values {0}")
        query6 = ("insert into game_events_skills ("
                  "game_id, creator_id, timestamp, event_type, "
                  "skill_slot, level_up_type) "
                  "values {0}")
        queryl = ("update games "
                  "set events_updated = true "
                  "where game_id = %s")
        s10 = '%s' + ', %s' * 9
        s8 = '%s' + ', %s' * 7
        s7 = '%s' + ', %s' * 6
        s6 = '%s' + ', %s' * 5
        
        timeline = self.data['timeline']
        frames = timeline['frames']
        
        for frame in frames:
            if not 'events' in frame:
                continue
            #print 'events'
            events = frame['events']
            buildingEventSS, buildingEventArgs = [], []
            championKillEventSS, championKillEventArgs = [], []
            monsterKillEventSS, monsterKillEventArgs = [], []
            wardEventSS, wardEventArgs = [], []
            itemEventSS, itemEventArgs = [], []
            skillEventSS, skillEventArgs = [], []
            for event in events:
                eventType = Util.event_type_convertor(event['eventType'])
                creatorId = event['participantId'] if 'participantId' in event else None
                if creatorId == 0:
                    creatorId = None                
                timestamp = event['timestamp']
                
                teamId = event['teamId'] if 'teamId' in event else None
                itemId = event['itemId'] if 'itemId' in event else None
                itemAfter = event['itemAfter'] if 'itemAfter' in event else None
                itemBefore = event['itemBefore'] if 'itemBefore' in event else None
                skillSlot = event['skillSlot'] if 'skillSlot' in event else None
                killerId = event['killerId'] if 'killerId' in event else None
                victimId = event['victimId'] if 'victimId' in event else None
                position = event['position'] if 'position' in event else None
                x, y = None, None
                if position:
                    x, y = position['x'], position['y']
                wardType = Util.ward_type_convertor(event['wardType']) if 'wardType' in event else None
                buildingType = Util.building_type_convertor(event['buildingType']) if 'buildingType' in event else None
                monsterType = Util.monster_type_convertor(event['monsterType']) if 'monsterType' in event else None
                towerType = Util.tower_type_convertor(event['towerType']) if 'towerType' in event else None
                laneType = Util.lane_type_convertor(event['laneType']) if 'laneType' in event else None
                levelUpType = Util.level_up_type_convertor(event['levelUpType']) if 'levelUpType' in event else None
                
                if eventType == constant.ET_BUILDING_KILL:
                    values = (matchId, creatorId, timestamp, eventType,
                              killerId, x, y, laneType, buildingType, towerType)
                    buildingEventSS.append(s10)
                    for value in values:
                        buildingEventArgs.append(value)
                elif eventType == constant.ET_CHAMPION_KILL:
                    values = (matchId, creatorId, timestamp, eventType,
                              killerId, victimId, x, y)
                    championKillEventSS.append(s8)
                    for value in values:
                        championKillEventArgs.append(value)
                elif eventType == constant.ET_ELITE_MONSTER_KILL:
                    values = (matchId, creatorId, timestamp, eventType, 
                              killerId, x, y, monsterType)
                    monsterKillEventSS.append(s8)
                    for value in values:
                        monsterKillEventArgs.append(value)
                elif (eventType == constant.ET_WARD_KILL or
                      eventType == constant.ET_WARD_PLACED):
                    values = (matchId, creatorId, timestamp, eventType, 
                              killerId, x, y, wardType)
                    wardEventSS.append(s8)
                    for value in values:
                        wardEventArgs.append(value)
                elif (eventType == constant.ET_ITEM_DESTROYED or
                      eventType == constant.ET_ITEM_PURCHASED or
                      eventType == constant.ET_ITEM_SOLD or
                      eventType == constant.ET_ITEM_UNDO):
                    values = (matchId, creatorId, timestamp, eventType, 
                              itemId, itemBefore, itemAfter)
                    itemEventSS.append(s7)
                    for value in values:
                        itemEventArgs.append(value)
                elif eventType == constant.ET_SKILL_LEVEL_UP:
                    values = (matchId, creatorId, timestamp, eventType,
                              skillSlot, levelUpType)
                    skillEventSS.append(s6)
                    for value in values:
                        skillEventArgs.append(value)
                
            if buildingEventArgs:
                self.db.query(query1.format(*('(' + '), ('.join(buildingEventSS) + ')',)), 
                              tuple(buildingEventArgs)).close()
            if championKillEventArgs:
                self.db.query(query2.format(*('(' + '), ('.join(championKillEventSS) + ')',)), 
                              tuple(championKillEventArgs)).close()
            if monsterKillEventArgs:
                self.db.query(query3.format(*('(' + '), ('.join(monsterKillEventSS) + ')',)), 
                              tuple(monsterKillEventArgs)).close()
            if wardEventArgs:
                self.db.query(query4.format(*('(' + '), ('.join(wardEventSS) + ')',)), 
                              tuple(wardEventArgs)).close()
            if itemEventArgs:
                self.db.query(query5.format(*('(' + '), ('.join(itemEventSS) + ')',)), 
                              tuple(itemEventArgs)).close()
            if skillEventArgs:
                self.db.query(query6.format(*('(' + '), ('.join(skillEventSS) + ')',)), 
                              tuple(skillEventArgs)).close()
        self.db.query(queryl, (matchId,)).close()
            
    def _update_participant_frames(self):
        matchId = self.data['matchId']
        if not 'timeline' in self.data:
            return

        timeline = self.data['timeline']
        frames = timeline['frames']
        #print ' timeline'
        query = ("insert into game_participant_frames ("
                 "game_id, participant_id, timestamp, gold, xp, level, "
                 "minions_killed, jungle_minions_killed) "
                 "values (%s, %s, %s, %s, %s, %s, %s, %s) "
                 "on duplicate key update "
                 "game_id = values(game_id),"
                 "participant_id = values(participant_id)")
        
        frameInterval = timeline['frameInterval']
        prevTimestamp = 0
        for frame in frames:
            timestamp = frame['timestamp']
            if timestamp - prevTimestamp < frameInterval - 200:
                continue
            
            pFrames = frame['participantFrames']
            for pId in pFrames:
                pFrame = pFrames[pId]
                totalGold = pFrame['totalGold']
                level = pFrame['level']
                xp = pFrame['xp']
                minionsKilled = pFrame['minionsKilled'] if 'minionsKilled' in pFrame else 0
                jungleMinionsKilled = pFrame['jungleMinionsKilled'] if 'jungleMinionsKilled' in pFrame else 0
                
                args = (matchId, int(pId), timestamp, totalGold, xp, level,
                        minionsKilled, jungleMinionsKilled)
                
                self.db.query(query, args).close()
                
class CurrentGameUpdator(PentakillUpdator):
    def __init__(self, module):
        super(CurrentGameUpdator, self).__init__(module, C_CURRENT_GAME_TRY)
        
    def _rollback(self):
        data = {}
        if 'id' in self.data:
            data['id'] = self.data['id']
        self.data = data
       
if __name__ == '__main__':
    import time
    module = UpdateModule()
    module.init() 
    
if __name__ == '__maign__':
    print('policy and init final test')
    ID = 2576538
    begin = time.time()
    policy = module.getPolicy()
    ok, left, db = policy.check_summoner_update(id=ID)
    if not ok:
        print(left, 'sec left for', ID)
        db.close()
    else:
        import threading
        class MyInitFinal(UpdatorInitFinal):
            def __init__(self, sema):
                self.sema = sema
            def initialize(self):
                print('initialize update')
                print(self.data)
                
            def finalize(self):
                print('finalize update')
                self.sema.release()
        
        sema = threading.Semaphore(0)        
        updator = module.getSummonerUpdator()
        updator.init(db, MyInitFinal(sema))
        updator.put_data({'id':ID})
        module.orderUpdate(updator)
        sema.acquire()
        end = time.time()
        print(end - begin, 'elapsed')
    
if __name__ == '__mfain__':
    print('test match update')
    data = [{'id':2526543207}, {'id':2529517584}]
    
    updator = module.getMatchUpdator()
    for i in range(len(data)):
        updator.init()
        updator.put_data(data[i])
        begin = time.time()
        updator.update()
        updator.close()
        end = time.time()
        print(end - begin, 'sec elapsed')
    print('test passed')
    
if __name__ == '__main__':
    print('test summoner update')
    data = [{'name':'hide on bush', 'id':4460427}, {'id':2576538}, {'id':2060159}]
    data = [{'name':'hide on bush', 'id':44604274} for i in range(100)]
    updator = module.getSummonerUpdator()
    SLEEP = 0
    for i in range(len(data)):
        try:
            if i > 0:
                time.sleep(SLEEP)
            updator.init()
            updator.put_data(data[i])
            begin = time.time()
            updator.update()
            updator.close()
            end = time.time()
            print(end - begin, 'sec elapsed')
        except Exception as err:
                pass
    print('test passed')

if __name__ == '__main__':
    module.close()