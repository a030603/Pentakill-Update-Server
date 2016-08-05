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
        self._update_runes()
        self._update_masteries()
        return True
        
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
        
    def _update_summoner(self):
        while True:
            apidat = self.data['summoner']
            
            id = apidat['id']
            name = apidat['name'].encode('utf8')
            nameAbbre = Util.abbre_names(name)
            profileIconId = apidat["profileIconId"]
            summonerLevel = apidat["summonerLevel"]
            revisionDate = int(apidat["revisionDate"] / 1000)
            
            result = self.db.query("select s_id, last_update "
                                   "from summoners where s_name_abbre = %s and live = 1", (nameAbbre,))
            row = result.fetchRow()
            result.close()
            print row
            if row:
                print row[1], revisionDate
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
                print row
            print name.decode('utf8').encode('cp949')
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
            break
        
        # data update
        self.data['id'] = id
    
    def _get_api_data(self, summoner_by_id=False):
        id = self.data['id']
        
        reqs = lolfastapi.FastRequest()
        if summoner_by_id:
            reqs.add_request_name('summoner', (lolapi.LOLAPI.get_summoners_by_ids, (id,)))
        reqs.add_request_name('leagues', (lolapi.LOLAPI.get_league_entries, (id,)))
        reqs.add_request_name('games', (lolapi.LOLAPI.get_recent_games, (id,)))
        reqs.add_request_name('stats', (lolapi.LOLAPI.get_stats_summary, (id,)))
        reqs.add_request_name('rank', (lolapi.LOLAPI.get_rank_stats, (id,)))
        reqs.add_request_name('runes', (lolapi.LOLAPI.get_summoner_runes, (id,)))
        reqs.add_request_name('masteries', (lolapi.LOLAPI.get_summoner_masteries, (id,)))
        
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
                
    def _update_leagues(self):
        id = self.data['id']
        if not 'leagues' in self.data:
            return
        apidat = self.data['leagues'][str(id)]
        #print apidat
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
                query = ("insert into tier_transition (s_id, tier, division, lp, time) "
                         "values (%s, %s, %s, %s, UNIX_TIMESTAMP(now()))")
                
                self.db.query(query, (id, tier, division, point)).close()
            
            # insert league data
            query = ("insert into league (s_id, league_id, player_or_team_name, "
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
            arg = (id, leagueId, playerOrTeamName, queue, leagueName, tier, division,
                   point, fresh, inactive, veteran, hotStreak, isMiniSeries,
                   miniSeriesWins, miniSeriesLosses, miniSeriesTarget)
            
            self.db.query(query, arg).close()
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
        for stat in stats:
            modifyDate = int(stat['modifyDate'] / 1000)
            playerStatSummaryType = Util.player_stat_summary_type_convertor(
                stat['playerStatSummaryType'])
            wins = stat['wins'] if 'wins' in stat else None
            losses = stat['losses'] if 'losses' in stat else None
            season = Util.season_int_convertor(config.SEASON)
            
            query = ("insert into stats (s_id, season, sub_type, win, lose) "
                     "values (%s, %s, %s, %s, %s) "
                     "on duplicate key update "
                     "win = values(win),"
                     "lose = values(lose)")
            arg = (id, season, playerStatSummaryType, wins, losses)
            
            self.db.query(query, arg).close()      

    def _update_games(self):
        id = self.data['id']
        if not 'games' in self.data:
            return
        apidat = self.data['games']
        #print apidat['games'][0]
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
            season = Util.season_int_convertor(config.SEASON)
            
            # Games table update
            ##query = ("insert into games (game_id, create_date, time_played, "
                     ##"game_mode, game_type, sub_type) "
                     ##"select * from ( "
                     ##"select %s as id, %s as create_date, %s as time_played,"
                     ##"%s as game_mode, %s as game_type, %s as sub_type) AS tmp "
                     ##"where not exists ( "
                     ##"select game_id from games where game_id = %s LIMIT 1)")
        
            query = ("insert into games (game_id, create_date, time_played, "
                     "game_mode, game_type, sub_type) "
                     "values (%s, %s, %s, %s, %s, %s) "
                     "on duplicate key update "
                     "game_id = values(game_id)")
            args = (gameId, createDate, timePlayed, gameMode, gameType, subType)
            self.db.query(query, args).close()
            
            ss = '%s, ' * 40
            # Game detail update
            query = ("insert into game_detail ( "
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
            self.db.query(query, args).close()
            
            # Fellow update
            query = ("insert into game_fellows values (%s, %s, %s, %s) "
                     "on duplicate key update "
                     "game_id = values(game_id),"
                     "s_id = values(s_id)")
            args = (gameId, id, teamId, championId)
            self.db.query(query, args).close()
            if fellows is None:
                return
            for fellow in fellows:
                fellowId = fellow['summonerId']
                fellowTeamId = fellow['teamId']
                fellowChampionId = fellow['championId']
                args = (gameId, fellowId, fellowTeamId, fellowChampionId)
                self.db.query(query, args).close()
    
    def _update_rank_champions(self):
        id = self.data['id']
        if not 'rank' in self.data:
            return
        apidat = self.data['rank']
        champions = apidat['champions']
        modifyDate = apidat['modifyDate']
        if 'epoch' in self.data and self.data['epoch'] > modifyDate:
            return
        for champion in champions:
            pass
    
    def _update_runes(self):
        pass
    
    def _update_masteries(self):
        pass
        
        
        
        
    
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
        
if __name__ == '__main__':
    print 'test update'
    import time
    module = UpdateModule()
    module.init()
    for i in range(1):
        updator = module.getSummonerUpdator()
        updator.init()
        updator.put_data({"name":' Hide on bush  '})
        #updator.put_data({"name":u'   \uba38 \ud53c   9  3'})
        #updator.put_data({"id":2576538})
        #updator.put_data({"name":'zzz'})
        begin = time.time()
        updator.update()
        end = time.time()
        print end - begin, 'sec elapsed'
    module.close()
    print 'test passed'