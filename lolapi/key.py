# LOL API setting

'''
Regional constants for main connection

Regions:                  Region      Platform id
Brazil                  : br          BR1
EU Nordic & East        : eune        EUN1
EU West                 : euw         EUW1
Korea                   : kr          KR
Latin America North     : lan         LA1
Latin America South     : las         LA2
Noth America            : na          NA1
Oceania                 : oce         OC1  
Russia                  : ru          RU
Turkey                  : tr          TR1
Public Beta Environment : global*   
'''

'''
Host:
host name in which region value replaced with %s

Timeout:
nonnegative floating number expressed in second
If you don't want to use timeout, set it to None

Note: This values can be overwritten to another by
giving new values to lolapi when you initialize it
'''
REGION = 'kr'
PLATFORM = 'KR'
HOST = '%s.api.pvp.net'
PORT = 443
TIMEOUT = 4.0

'''
Other hosts

status : host that returns status information
static : host for lol static data

timeout for main host will be used as default timeout for these hosts

Note: The static data is a global service, and thus uses 
the global.api.pvp.net endpoint regardless of the region selected. 
'''
STATUS_HOST = 'status.leagueoflegends.com'
STATUS_PORT = 80

STATIC_HOST = 'global.api.pvp.net'
STATIC_PORT = 443

'''
Request headers

If you set it to empty string, default request header is used
'''
C_CONNECTION = 'keep-alive'
C_ACCEPT = 'application/json'
C_ACCEPT_ENCODING = 'gzip'

'''
Request message
this message will be included to every http request to API server

If you don't want to include, leave it to empty string
'''
C_USER_AGENT = 'Pentakill League of Legends API 1.0'

'''
Default key

LIMIT_NUM: request number limitation per release
LIMIT_TIME: time needed to release limit, in second

If you don't give key when initialize, this key is used.
'''
KEY = '66badc84-d6f2-4a17-a609-423ae5d8f052'
LIMIT_NUM = 10
LIMIT_TIME = 10

'''
Other constants

Season: Default season setting
        must be one of SEASON3, SEASON2014, SEASON2015
        You can change season when you initialize
'''
SEASON = 'SEASON2015'

'''
Constants for api version

This information needs to be updated as new version of 
api comes out
'''
V_SUMMONER = '1.4'
V_TEAM = '2.4'
V_STATS = '1.3'
V_MATCHLIST = '2.2'
V_MATCH = '2.2'
V_STATIC = '1.2'
V_LEAGUE = '2.5'
V_GAME = '1.3'
V_CHAMPION = '1.2'

'''
request paths

each parameters (version, region, summonerId..) are replaced with argument you give
'''
# Champions
# champion enabled information
P_CHAMPIONS_ENABLED = '/api/lol/{region}/v{version}/champion'
# champion enabled information by champion id
P_CHAMPIONS_ENABLED_BY_ID = '/api/lol/{region}/v{version}/champion/{id}'

# Current game
# live game playing information by summoner id 
P_CURRENT_GAME = '/observer-mode/rest/consumer/getSpectatorGameInfo/{platformId}/{summonerId}'

# Featured game
# featured games data
P_FEATURED_GAMES = '/observer-mode/rest/featured'

# Game
# recent games data by summoner id
P_RECENT_GAMES = '/api/lol/{region}/v{version}/game/by-summoner/{summonerId}/recent'

# League
# league data by summoner ids
P_LEAGUE_BY_SUMMONER_IDS = '/api/lol/{region}/v{version}/league/by-summoner/{summonerIds}'
# league entry data by summoner ids
P_LEAGUE_ENTRY_BY_SUMMONER_IDS = '/api/lol/{region}/v{version}/league/by-summoner/{summonerIds}/entry'
# league data by team ids
P_LEAGUE_BY_TEAM_IDS = '/api/lol/{region}/v{version}/league/by-team/{teamIds}'
# league entry data by team ids
P_LEAGUE_ENTRY_BY_TEAM_IDS = '/api/lol/{region}/v{version}/league/by-team/{teamIds}/entry'
# challenger league data
P_CHALLENGER_LEAGUE = '/api/lol/{region}/v{version}/league/challenger'

# LOL-Static data
# champion lists and information
P_CHAMPIONS = '/api/lol/static-data/{region}/v{version}/champion'
# champion information by champion id
P_CHAMPION_BY_ID = '/api/lol/static-data/{region}/v{version}/champion/{id}'
# item list
P_ITEMS = '/api/lol/static-data/{region}/v{version}/item'
# item by item id
P_ITEM_BY_ID = '/api/lol/static-data/{region}/v{version}/item/{id}'
# language string data
P_LANGUAGE_STRING = '/api/lol/static-data/{region}/v{version}/language-strings'
# supported languages data
P_LANGUAGES = '/api/lol/static-data/{region}/v{version}/languages'
# maps data
P_MAP = '/api/lol/static-data/{region}/v{version}/map'
# masteries data
P_MASTERY = '/api/lol/static-data/{region}/v{version}/mastery'
# mastery data by mastery id
P_MASTERY_BY_ID = '/api/lol/static-data/{region}/v{version}/mastery/{id}'
# realm data
P_REALM = '/api/lol/static-data/{region}/v{version}/realm'
# rune data
P_RUNE = '/api/lol/static-data/{region}/v{version}/rune'
# rune data by rune id
P_RUNE_BY_ID = '/api/lol/static-data/{region}/v{version}/rune/{id}'
# summoner spell data
P_SUMMONER_SPELLS = '/api/lol/static-data/{region}/v{version}/summoner-spell'
# summoner spell data by spell id
P_SUMMONER_SPELL_BY_ID = '/api/lol/static-data/{region}/v{version}/summoner-spell/{id}'
# league of legends versions
P_VERSIONS = '/api/lol/static-data/{region}/v{version}/versions'

# LOL-Status
# shard list
P_STATUS_SHARD = '/shards'
# shard by region
P_STATUS_SHARD_BY_REGION = '/shards/{region}'

# Match
# match information by match id
P_MATCH = '/api/lol/{region}/v{version}/match/{matchId}'

# Match list
# match list by summoner id
P_MATCH_LIST = '/api/lol/{region}/v{version}/matchlist/by-summoner/{summonerId}'

# Stats
# ranked game stats by summoner id
P_RANK_STATS = '/api/lol/{region}/v{version}/stats/by-summoner/{summonerId}/ranked'
# a player's stats for all types of game by summoner id
P_PLAYER_STAT_SUMMARY = '/api/lol/{region}/v{version}/stats/by-summoner/{summonerId}/summary'

# Summoners
# summoner information by summoner names
P_SUMMONERS_BY_NAME = '/api/lol/{region}/v{version}/summoner/by-name/{summonerNames}'
# summoner information by summoner idsf n
P_SUMMONERS_BY_IDS = '/api/lol/{region}/v{version}/summoner/{summonerIds}'
# masteries by summoner ids
P_SUMMONER_MASTERIES = '/api/lol/{region}/v{version}/summoner/{summonerIds}/masteries'
# just summoner names by summoner ids
P_SUMMONER_NAMES_BY_IDS = '/api/lol/{region}/v{version}/summoner/{summonerIds}/name'
# runes by summoner ids
P_SUMMONER_RUNES = '/api/lol/{region}/v{version}/summoner/{summonerIds}/runes'

# Teams
# rank team information by summoner ids
P_TEAMS_BY_SUMMONER_IDS = '/api/lol/{region}/v{version}/team/by-summoner/{summonerIds}'
# rank team information by team ids
P_TEAMS_BY_TEAM_IDS = '/api/lol/{region}/v{version}/team/{teamIds}'