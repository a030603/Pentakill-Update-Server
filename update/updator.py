class LOLWorker(threading.Thread):
    # work_type : one of work type (W_*) constant
    # key : api key
    # api : lolapi instance. if not given, new instance is made
    # db : pentakillDB instance. if not given, new instance is made
    def __init__(self, core, work_type, key, api=None, db=None):
        threading.Thread.__init__(self)
        
        self.core = core
        self.admin = self.core.admin
        self.key = key
        self.work_type = work_type
        self.api = api or C_DEFAULT_API()
        self.db = db or C_DEFAULT_DB()
        
    def run(self):
        if self.work_type == W_SUMMONER:
            return self.updateSummoner()
        elif self.work_type == W_GAME:
            return self.updateGame()
        elif self.work_type == W_CURRENT_GAME:
            return self.getCurrentGame()
        else:
            return None
        
    # The two init functions can raise exception if they are alreay
    # initialized..
    def _init_api(self):
        if not self.api:
            self.api = C_DEFAULT_API()
        self.api.init()
    
    def _init_db(self):
        if not self.db:
            self.db = C_DEFAULT_DB()
        self.db.init()
        
    def _close_api(self):
        if self.api:
            self.api.close()
            self.api = None
    
    def _close_db(self):
        if self.db:
            self.db.close()
            self.db = None
            
    # update summoner stats
    # request number : 6 per summoner
    # at least one of s_id or s_name should be given.
    # if two are given, s_id is used.
    # if nothing is given, it just returns
    def update_summoner(self, s_id=None, s_name=None):
        self._init_api()
        self._init_db()
        api = self.api
        db = self.db
        
        db.begin()
        # update summoner and gets summoner id
        
        
        
        db.commit()
        
        self._close_db()
        self._close_api()
        
    def update_game(self, gId):
        pass
    
    def get_current_game(self, sId):
        pass
        
    # UPTADE ROUTINES FOR update_summoenr method
    
    # update summoner info and return summoner id
    def _update_summoner(self):
        pass