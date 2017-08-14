# Collection of functions frequently used for update
from pentakill.lib import error
from pentakill.update import constant

instance = None

class Utility(object):
    # Get instance in singleton pattern
    def getInstance():
        global instance
        if instance is None:
            instance = Utility()
        
        return instance
    
    # Transfrom unicode string of summoner names
    def transform_names(self, names):
        return names.lower().replace(" ", "")
    
    # Get abbrevation names
    def abbre_names(self, names):
        return names.replace(" ", "")
    
    # League queue is same as subtype
    def league_queue_convertor(self, type):
        if type == 'RANKED_SOLO_5x5':
            return constant.S_RANKED_SOLO_5x5
        elif type == 'RANKED_TEAM_3x3':
            return constant.S_RANKED_TEAM_3x3 
        elif type == 'RANKED_TEAM_5x5':
            return constant.S_RANKED_TEAM_5x5
        
        return self.subtype_convertor(type)
        #print(type)
        #raise error.TypeConvertError("league queue conversion fail")
    
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
        
        raise error.TypeConvertError("division conversion fail")
    
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
        elif mode == 'URF':
            return constant.M_URF
        
        raise error.TypeConvertError("game mode conversion fail '%s'" % (mode,))
    
    def game_type_convertor(self, type):
        if type == 'CUSTOM_GAME':
            return constant.T_CUSTOM_GAME
        elif type == 'TUTORIAL_GAME':
            return constant.T_TUTORIAL_GAME
        elif type == 'MATCHED_GAME':
            return constant.T_MATCHED_GAME
        
        raise error.TypeConvertError("game type conversion fail")
    
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
        elif subtype == 'RANKED_FLEX_TT':
            return constant.S_RANKED_FLEX_TT
        elif subtype == 'RANKED_FLEX_SR':
            return constant.S_RANKED_FLEX_SR
        
        raise error.TypeConvertError("subtype conversion fail")
    
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
        if type == 'ARURF_5X5':
            return constant.QT_ARURF_5X5
        if type == 'TEAM_BUILDER_DRAFT_UNRANKED_5x5':
            return constant.QT_TEAM_BUILDER_DRAFT_UNRANKED_5x5
        if type == 'TEAM_BUILDER_DRAFT_RANKED_5x5':
            return constant.QT_TEAM_BUILDER_DRAFT_RANKED_5x5
        if type == 'TEAM_BUILDER_RANKED_SOLO':
            return constant.QT_TEAM_BUILDER_RANKED_SOLO
        if type == 'RANKED_FLEX_SR':
            return constant.QT_RANKED_FLEX_SR
        if type == 'ASSASSINATE_5x5':
            return constant.QT_ASSASSINATE_5x5
        
        print(type)
        raise error.TypeConvertError("queue type conversion fail")
    
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
        if type == 'NightmareBot':
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
        if type == 'RankedFlexTT':
            return constant.PS_RankedFlexTT
        if type == 'RankedFlexSR':
            return constant.PS_RankedFlexTT
        
        print(type)
        raise error.TypeConvertError("player stat summary type conversion fail")
    
    def season_int_convertor(self, season):
        if season == constant.SEASON2013:
            return 3
        elif season == constant.SEASON2014:
            return 4
        elif season == constant.SEASON2015:
            return 5
        elif season == constant.SEASON2016:
            return 6
        elif season == constant.SEASON2017:
            return 7
        
        # From SEASON2014, we assume there are two formats
        try:
            if division.startswith('PRESEASON'):
                return int(division[8:])
            elif division.startswith('SEASON'):
                return int(division[5:])
        except ValueError:
            pass
        
        raise error.TypeConvertError("season int conversion fail")
    
    def int_season_convertor(self, int):
        if int == 3:
            return constant.SEASON2013
        elif int == 4:
            return constant.SEASON2014
        elif int == 5:
            return constant.SEASON2015
        elif int == 6:
            return constant.SEASON2016
        
        raise error.TypeConvertError("int season conversion fail")
    
    def event_type_convertor(self, type):
        if type == 'BUILDING_KILL':
            return constant.ET_BUILDING_KILL
        elif type == 'CHAMPION_KILL':
            return constant.ET_CHAMPION_KILL
        elif type == 'ELITE_MONSTER_KILL':
            return constant.ET_ELITE_MONSTER_KILL
        elif type == 'WARD_KILL':
            return constant.ET_WARD_KILL
        elif type == 'WARD_PLACED':
            return constant.ET_WARD_PLACED
        elif type == 'ITEM_DESTROYED':
            return constant.ET_ITEM_DESTROYED
        elif type == 'ITEM_PURCHASED':
            return constant.ET_ITEM_PURCHASED
        elif type == 'ITEM_SOLD':
            return constant.ET_ITEM_SOLD
        elif type == 'ITEM_UNDO':
            return constant.ET_ITEM_UNDO
        elif type == 'SKILL_LEVEL_UP':
            return constant.ET_SKILL_LEVEL_UP
        elif type == 'ASCENDED_EVENT':
            return constant.ET_ASCENDED_EVENT
        elif type == 'CAPTURE_POINT':
            return constant.ET_CAPTURE_POINT
        elif type == 'PORO_KING_SUMMON':
            return constant.ET_PORO_KING_SUMMON
        
        raise error.TypeConvertError("event type conversion fail")
        
    def building_type_convertor(self, type):
        if type == 'TOWER_BUILDING':
            return constant.BT_TOWER_BUILDING
        elif type == 'INHIBITOR_BUILDING':
            return constant.BT_INHIBITOR_BUILDING
        
        raise error.TypeConvertError("building type conversion fail")
    
    
    def tower_type_convertor(self, type):
        if type == 'OUTER_TURRET':
            return constant.TT_OUTER_TURRET
        elif type == 'INNER_TURRET':
            return constant.TT_INNER_TURRET
        elif type == 'BASE_TURRET':
            return constant.TT_BASE_TURRET
        elif type == 'NEXUS_TURRET':
            return constant.TT_NEXUS_TURRET
        elif type == 'UNDEFINED_TURRET':
            return constant.TT_UNDEFINED_TURRET
        elif type == 'FOUNTAIN_TURRET':
            return constant.TT_FOUNTAIN_TURRET
        
        raise error.TypeConvertError("tower type conversion fail")
    
    def lane_type_convertor(self, type):
        if type == 'TOP_LANE':
            return constant.LT_TOP_LANE
        elif type == 'MID_LANE':
            return constant.LT_MID_LANE
        elif type == 'BOT_LANE':
            return constant.LT_BOT_LANE
        
        raise error.TypeConvertError("lane type conversion fail")
    
    def monster_type_convertor(self, type):
        if type == 'BLUE_GOLEM':
            return constant.MT_BLUE_GOLEM
        elif type == 'RED_LIZARD':
            return constant.MT_RED_LIZARD
        elif type == 'DRAGON':
            return constant.MT_DRAGON
        elif type == 'BARON_NASHOR':
            return constant.MT_BARON_NASHOR
        elif type == 'VILEMAW':
            return constant.MT_VILEMAW
        elif type == 'RIFTHERALD':
            return constant.MT_RIFTHERALD
        
        raise error.TypeConvertError("monster type conversion fail")
    
    def ward_type_convertor(self, type):
        if type == 'SIGHT_WARD':
            return constant.WT_SIGHT_WARD
        elif type == 'VISION_WARD':
            return constant.WT_VISION_WARD
        elif type == 'YELLOW_TRINKET':
            return constant.WT_YELLOW_TRINKET
        elif type == 'YELLOW_TRINKET_UPGRADE':
            return constant.WT_YELLOW_TRINKET_UPGRADE
        elif type == 'TEEMO_MUSHROOM':
            return constant.WT_TEEMO_MUSHROOM
        elif type == 'UNDEFINED':
            return constant.WT_UNDEFINED
        elif type == 'BLUE_TRINKET':
            return constant.WT_BLUE_TRINKET
        
        raise error.TypeConvertError("ward type conversion fail")
    
    def lane_convertor(self, type):
        if type == 'TOP':
            return constant.L_TOP
        elif type == 'JUNGLE':
            return constant.L_JUNGLE
        elif type == 'MIDDLE':
            return constant.L_MIDDLE
        elif type == 'MID':
            return constant.L_MIDDLE
        elif type == 'BOTTOM':
            return constant.L_BOTTOM
        elif type == 'BOT':
            return constant.L_BOTTOM
        
        raise error.TypeConvertError("lane conversion fail")
    
    def role_convertor(self, type):
        if type == 'DUO':
            return constant.R_DUO
        elif type == 'NONE':
            return constant.R_NONE
        elif type == 'SOLO':
            return constant.R_SOLO
        elif type == 'DUO_CARRY':
            return constant.R_DUO_CARRY
        elif type == 'DUO_SUPPORT':
            return constant.R_DUO_SUPPORT
        
        raise error.TypeConvertError("role conversion fail")
    
    def level_up_type_convertor(self, type):
        if type == 'NORMAL':
            return constant.LU_NORMAL
        elif type == 'EVOLVE':
            return constant.LU_EVOLVE
        
        raise error.TypeConvertError("level up type conversion fail")
    
    def list_to_str(self, list):
        return str(list)[1:-1].replace(' ', '')
    
