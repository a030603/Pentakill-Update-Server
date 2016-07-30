# Pentakill fast lol API module
#
# This module provides wrapper of LOLAPI class which provides
# non-blocking I/O with League of Legends official API.
# This functionality allows one to send multiple request at once.
# It also can be deployed in multithread application, which
# results in significant I/O speed up.
#
# All API functions such as game history, match, league, summoner
# are handled by methods of LOLAPI module or any compatible one.
#
# LOLAdmin class manages one Riot API key and distributes to multiple
# threads in a way that total request number per one session time does not
# exceed the limit. It also handles server errors or servers network problems
# so users does not need to restart after everything is working well again.
# It automatically resumes processing so one can pass request again for retrial.
# LOLAdmin uses one key in config.py in the same directory.
#
# LOLFastAPI class provides non-blocking multi-I/O for multithreads.
# One can pack every request into FastRequest object and pass to LOLFastAPI
# then can wait for response with timeout(timeout 0 means non-blocking).

# This version is implemented in single core threading way(if you're using CPython)
# it may not utilize multicore resources

# This module is dependent to LOLAPI module, I decided it because I wanted to 
# leave lolapi module as independent module, without key management. 
# Otherwise, lolapi would have wrapped this module.

from pentakill.lolapi import lolapi
from pentakill.db import connector
from pentakill.update import config
import threading
import time

'''
Work type
'''
W_SUMMONER = 1
W_GAME = 2
W_CURRENT_GAME = 3

'''
states

LOLAdmin is an simple state machine
There are two types of events 
Type1 : Events can only happen in certain state   (e.g. get data, sync)
Type2 : Events causes state to move another state (e.g. service unavailable)
Rule
1. Before Type2 event swtiches current state, it should block
   further Type1 events and must wait for current processing Type1 events to end
2. Type2 event must occur atomically. That is, only one Type2 event can be
   processed at a time, which means no more than 2 Type2 events happen in
   a state. Also no any Type1 event can happen during Type2 event
'''
S_IDLE = 0
S_OK = 1
S_SERVICE_UNAVAILABLE = 2

'''
substate of S_OK

There's no specified rule for substate regarding events
'''
SS_OK = 0
SS_SYNCHRONIZING = 1

# LOLKeyManager is in charge of managing multiple keys
## it is not implemented yet
class LOLKeyManager(object):
    # keys : list of key which is represented by string
    # cores : core number which each admin will have
    def __init__(self, keys, cores=4):
        self.keys = keys
        self.core_num = cores
        if self.core_num <= 0:
            self.core_num = 1

# State machine for event based class with multithreading
class _StateMachine(object):
    def __init__(self, init_state=None, init_sstate=None):
        self.state = init_state
        self.substate = init_sstate
        # number of events processing now
        self.state_event_num = 0
        # flag for state switch request
        self.state_switch = False
        # state synchronization
        self.state_condition = threading.Condition()
        
    # Switch state and substate, must be called in switching event
    def switch_state(self, state=None, sstate=None):
        self.state_condition.acquire()
        self.state = state
        self.substate = sstate
        self.state_condition.release()
        
    # No calling rule for substate functions
    def switch_substate(self, sstate=None):
        self.substate = sstate
    
    def get_substate(self):
        return self.substate
    
    # return True if state switching event is waiting, False otherwise
    # Used by Type1 events to know that it should not block waiting for 
    # another Type1 event
    def is_switch_started(self):
        self.state_condition.acquire()
        ret = self.state_switch
        self.state_condition.release()
        return ret
    
    # Start a event of state in list 'states'
    # If 'wait' is True, when Type2 event is waiting, it does not fail
    # but it blocks until Type2 event is completed. If 'timeout' is specified and
    # not None, after timeout elapse, it fails.
    # if success, return (True, state), otherwise tuple (False, state, switch)
    # when True second entry 'state' is current state which is one of list 'states'
    # when False second entry 'state' is the state made this call fail
    # third entry 'switch' is true if state_switch was true when called
    def start_event(self, states, wait=False, timeout=None):
        self.state_condition.acquire()
        if wait:
            if self.state_switch and timeout != None:
                begin = time.time()
            while self.state_switch:
                self.state_condition.wait(timeout)
                if timeout != None:
                    end = time.time()
                    elapsed = end - begin
                    if elapsed >= timeout:
                        break
                    else:
                        timeout -= elapsed
        found = False
        for state in states:
            if state == self.state:
                found = True
                break
        if self.state_switch or not found:
            ret = (False, self.state, self.state_switch)
            self.state_condition.release()
            return ret
        self.state_event_num += 1
        ret = (True, self.state)
        self.state_condition.release()
        return ret
        
    # End event started before
    def end_event(self):
        self.state_condition.acquire()
        self.state_event_num -= 1
        if self.state_event_num == 0:
            self.state_condition.notifyAll()
        self.state_condition.release()
        
    # Start state switch event from state in list 'states'
    # if success, return (True, state), otherwise (False, state, switch)
    # when True, second entry 'state' is current state which is one of list 'states' 
    # when False, second entry 'state' is the state made this call fail
    # third entry 'switch' is true if another Type2 event got chance earlier
    def start_state_switch(self, states):
        self.state_condition.acquire()
        found = False
        for state in states:
            if state == self.state:
                found = True
                break
        if not found or self.state_switch:
            #if self.state_switch:
            #    self.state_switch = False
            ret = (False, self.state, self.state_switch)
            self.state_condition.release()
            return ret
        self.state_switch = True
        if self.state_event_num > 0:
            self.state_condition.wait()
        ret = (True, self.state)
        self.state_condition.release()
        return ret
    
    # Enc state switching event started before
    def end_state_switch(self):
        self.state_condition.acquire()
        self.state_switch = False
        # notify waiting events
        self.state_condition.notifyAll()
        self.state_condition.release()
        
# Provides timer event reservation and cancellation
# It can be used together with _StateMachine events
class _TimerEventManager(object):
    def __init__(self):
        # timer events
        self.timer_events = {}
        # mutex
        self.mutex = threading.Lock()
        
        
    def _timer_func_factory(self, method, name, id):
        def timer_start():
            method(name=name, id=id)
        return timer_start
    
    # Reserve timer event 'method' which start after 'time' second
    # Returns True if new timer is reserved, False if already reserved
    def reserve_timer(self, name, method, time):
        ret = False
        while True:
            self.mutex.acquire()
            if not name in self.timer_events:
                # 0th item : timer id
                # 1th item : is timer event running now?
                # 2th item : Lock to wait for end of event
                # 3th item : reserved timer object (not None if reserved or running)
                self.timer_events[name] = [0, False, threading.Condition(), None]
            meta = self.timer_events[name]
            cond = meta[2]
            cond.acquire()
            self.mutex.release()
            while True:
                if meta[3]:
                    break
                meta[0] += 1
                timer_func = self._timer_func_factory(method, name, meta[0])
                meta[3] = threading.Timer(time, timer_func)
                meta[3].start()
                ret = True
                break
            cond.release()
            break
        return ret
    
    def start_timer(self, name, id):
        ret = False
        while True:
            self.mutex.acquire()
            if not name in self.timer_events:
                self.mutex.release()
                break
            meta = self.timer_events[name]
            cond = meta[2]
            cond.acquire()
            self.mutex.release()
            while True:
                if meta[0] != id or meta[1]:
                    break
                if meta[3] == None:
                    break
                meta[1] = True
                ret = True
                break
            cond.release()
            break
        return ret
    
    def end_timer(self, name):
        self.mutex.acquire()
        if not name in self.timer_events:
            self.mutex.release()
            return
        meta = self.timer_events[name]
        cond = meta[2]
        cond.acquire()
        self.mutex.release()
        if not meta[1] or meta[3] == None:
            cond.release()
            return
        meta[1] = False
        meta[3] = None
        cond.notifyAll()
        cond.release()
        return
        
    # Cancel timer if it's reserved and not stated
    # Returns True if cancelled current timer or there's no timer
    # Returns False if 'wait' is False and timer is running now
    def cancel_timer(self, name, wait=True):
        ret = False
        while True:
            self.mutex.acquire()
            if not name in self.timer_events:
                self.mutex.release()
                break
            meta = self.timer_events[name]
            cond = meta[2]
            cond.acquire()
            self.mutex.release()
            while True:
                if not meta[3]:
                    ret = True
                    break
                if meta[1]:
                    if wait:
                        # wait until timer ends
                        cond.wait()
                    else:
                        break
                ret = True
                meta[0] += 1
                if meta[3]:
                    meta[3].cancel()
                    meta[3] = None
                break
            cond.release()
            break
        return ret
    
# LOLAdmin is in charge of managing one key.
class LOLAdmin(object):
    # key : your API key
    # limit : tuple (req number, second) so that
    #         req number / second is req per sec
    #         'req number' of request is possible for 'second' sec
    # core : number of cores (default in config)
    # api : API to use (default in config)
    def __init__(self, limit=None, key=None, cores=None, api=None):
        limit = config.LIMIT if limit == None else limit
        cores = config.CORE_NUM if cores == None else cores
        api = config.API if api == None else api
        self.api = api
        self.key = config.KEY if key == None else key
        self.req_num = limit[0]
        self.per_time = limit[1]
        self.core_num = cores
        if self.core_num <= 0:
            self.core_num = 1
        self.cores = []
        self.core_req_num = self.req_num/self.core_num
        
        # timer event function
        self.timer = _TimerEventManager()
        
        # LOLAdmin is an state machine
        self.state = _StateMachine(S_IDLE)
        
        # index to next core to dispatch request
        self.next_core = 0
        
        # miss counted requests when synchronizes
        self.sync_miss = 0
        self.sync_miss_time = 0  # time when response to miss req is got 
        self.sync_miss_mutex = threading.Lock()
        self.sync_last = 0       # time when last successful synchronization is done
        
        # policy for service unavailable
        self.policy = _ServiceUnavailablePolicy()
        
        # debug
        self.debug = False
        
        '''
        Synchronization
        '''
        
        # conditions
        # condition for permission to request for all cores
        # Each core may have its own perm condition but here's only one        
        self.perm_condition = threading.Condition()
        
        # semaphores for mutual exclusion
        
        # Make sure that timer doesn't work when synchronizing
        self.sync_mutex = threading.Semaphore(1)    
        # when sync happens, it's possible that a successful request before
        # limit exceed is counted in miss req, this will make
        # early reqs get into result processing phase probably earlier 
        # in _get_data in LOLCore
        self.global_after_req_mutex = threading.Semaphore(1)
        self.get_data_mutex = threading.Semaphore(1)
        
    # Get information of admin
    def get_spec(self):
        r = {}
        r['key'] = self.key
        r['req_num'] = self.req_num
        r['per_time'] = self.per_time
        r['core_num'] = self.core_num
        return r
    
    # Initializes cores
    def init(self):
        start = self.state.start_state_switch((S_IDLE,))
        if not start[0]:
            return
        
        # initialize cores
        for i in range(self.core_num):
            core = LOLCore(self, (self.core_req_num, self.per_time))
            self.cores.append(core)
            
        self.state.switch_state(S_OK, SS_OK)
        self.state.end_state_switch()
        
    # Test request to check server state, status
    def _test_request(self, api):
        return api.get_summoners_by_names(u'\uba38\ud53c93'.encode('utf8'))
    
    def _call_synchronize(self):
        # to SS_SYNCHRONIZING substate
        # in this state, if get_permission found no more request left,
        # it will return False
        self.state.switch_substate(SS_SYNCHRONIZING)
        return self.timer.reserve_timer('synchronize', self._synchronize, 0.0)
    
    def _synchronize(self, name, id):
        # All synchronization must follow this order
        # sync_mutex -> perm_condition -> req_condition -> sync_miss_mutex
        # otherwise, deadlock may occur
        
        start = self.timer.start_timer(name, id)
        if not start:
            return
        
        start = self.state.start_event([S_OK])
        if not start[0]:
            self.timer.end_timer(name)
            return
        
        # Sync mutex with reset thread
        self.sync_mutex.acquire()        
        # Block any permission
        self.perm_condition.acquire()
        # Wait for currently executing cores till method is done
        for i in range(self.core_num):
            self.cores[i].req_condition.acquire()
        # cancel timer if it's set
        self._cancel_reset_timer()
            
        api = self.cores[0].api
        self._debug_msg('sync')
            
        begin = time.time()
        
        success = False
        while 1:
            # assume api is initialized and not closed
            # test request
            try:
                content = self._test_request(api)
            except lolapi.Error as err:
                try:
                    raise err
                except lolapi.Timeout as err:
                    if not self.policy.push_timeout():
                        break
                    continue
                except lolapi.Error as err:
                    if not self.policy.push_error():
                        break
                    continue
                
            status_code = content[0][0]
            if status_code == config.SC_LIMIT_EXCEEDED:
                time.sleep(0.05)
                end = time.time()
                time_thresh = self.per_time * 1.5
                # check if per_time is elapsed from start
                if end-begin > time_thresh:
                    break
                continue
            else:
                if self.policy.push_status_code(status_code):
                    success = True
                break
        
        # common codes
        self.sync_miss_time = 0
        
        if success:
            self._debug_msg('sync success')
            # set new timer
            # If miss request is got, timer in server is already set before
            # sync. To fix, calculate delayed time 
            delay = time.time() - self.sync_miss_time if self.sync_miss_time else 0
            timing = self.per_time - delay if self.per_time > delay else 0
            #print 'Delay', delay
            self.sync_last = time.time() - delay
            self._call_reset_timer(timing)
            
            self._reset_rate_for_each_cores()
            
            self.state.switch_substate(SS_OK)
            
            # fix count miss by misses and 1 request to server 
            self.sync_miss_mutex.acquire()
            miss_cnt = self.sync_miss + 1
            if miss_cnt:
                miss_for_one = miss_cnt / self.core_num
                miss_remainder = miss_cnt % self.core_num
                for core in self.cores:
                    core.left -= miss_for_one
                for r in range(miss_remainder):
                    self.cores[r].left -= 1
            self.sync_miss = 0
            time.sleep(0.1)
            self.sync_miss_mutex.release()
            
            # debug - show left for each core
            if self._is_debug():
                for cor in self.cores:
                    print 'core : ', cor.left
                
        else:
            self._debug_msg('sync failed')
            self._call_service_unavailable()

        # release locks
        for i in range(self.core_num):
            # tell the blocked limit exceeded threads that sync is completed
            self.cores[i].req_condition.notifyAll()
            self.cores[i].req_condition.release()
        self.perm_condition.release()
        self.sync_mutex.release()
        
        self.state.end_event()
        self.timer.end_timer(name)
        
    def _call_service_unavailable(self):
        return self.timer.reserve_timer('service_unavailable', self._service_unavailable, 0.0)
        
    # Get into service unavailable state
    def _service_unavailable(self, name, id):
        start = self.timer.start_timer(name, id)
        if not start:
            return
        
        start = self.state.start_state_switch([S_OK])
        if not start[0]:
            self.timer.end_timer(name)
            return
            
        self._debug_msg('service unavailable called')
            
        self._cancel_reset_timer()
            
        self.state.switch_state(S_SERVICE_UNAVAILABLE)
        
        self.state.end_state_switch()
        self.timer.end_timer(name)
        
    # When in service_unavailable state, make request to server to
    # check connection status. If it's ok, it moves to 'OK' state and
    # returns True. Otherwise, returns False and remains in the state.
    def check_service_status(self):
        start = self.state.start_event([S_SERVICE_UNAVAILABLE])
        if not start[0]:
            return True
        
        self.sync_mutex.acquire()
        while True:
            ret = False
            # If service status was checked to be fine,
            # just return
            if self.state.is_switch_started():
                ret = True
                break
            while True:
                core = self.cores[0]
                try:
                    content = self._test_request(core.api)
                except Exception:
                    break
                else:
                    status_code = content[0]
                    if status_code[0] == config.SC_OK:
                        self._call_service_available()
                        ret = True
                    break
            break
        self.sync_mutex.release()
        
        self.state.end_event()
        return ret
    
    def _call_service_available(self):
        return self.timer.reserve_timer('service_available', self._service_available, 0.0)
            
    # Move to 'OK' state and 'OK' substate
    def _service_available(self, name, id):
        start = self.timer.start_timer(name, id)
        if not start:
            return
        
        start = self.state.start_state_switch([S_SERVICE_UNAVAILABLE])
        if not start[0]:
            self.timer.end_timer(name)
            return
        
        self.state.switch_state(S_OK, SS_OK)
        self.policy.reset()
        self._clear_rate_for_each_cores()
        
        self.state.end_state_switch()
        self.timer.end_timer(name)
        
        # start new timer
        self._call_reset_timer(0.0)
            
    # sets timer for rate reset
    # time : time untile timer is called in sec, if time is not given, self.per_time is used
    def _call_reset_timer(self, time=None):
        time = time if time != None else self.per_time
        ret = self.timer.reserve_timer('reset', self._reset_rate, time)
        if ret:
            self._debug_msg('set timer')
        return ret
        
    def _cancel_reset_timer(self):
        return self.timer.cancel_timer('reset')
        
    # synchronized rate reset
    def _reset_rate(self, name, id):
        start = self.timer.start_timer(name, id)
        if not start:
            return
        
        start = self.state.start_event([S_OK])
        if not start[0]:
            self.timer.end_timer(name)
            return
        
        self.sync_mutex.acquire()
        self.perm_condition.acquire()
        self._debug_msg('timer start')
        self._reset_rate_for_each_cores()
        # wake up all cores waiting for reset
        self.perm_condition.notifyAll()
        self.perm_condition.release()
        self.sync_mutex.release()
        
        self.state.end_event()
        self.timer.end_timer(name)
        
    # clear rates for each cores
    def _clear_rate_for_each_cores(self):
        for core in self.cores:
            core.left = 0
        
    # reset rates for each cores
    def _reset_rate_for_each_cores(self):
        for core in self.cores:
            core.left = self.core_req_num
        
    # Get data from lol api and returns response
    # method : lolapi method
    # args : tuple of arguments to 'method'
    # If some errors occur, LOLAdmin may get into S_SERVICE_UNAVAILABLE state. 
    # In this state, all cores does not work and any call to this method just
    # raises ServiceUnavailableError.
    def get_data(self, method, args):
        start = self.state.start_event([S_OK], True)
        if not start[0]:
            if start[1] == S_IDLE:
                raise InvalidUseError("Please initailize before")
            elif start[1] == S_SERVICE_UNAVAILABLE or start[2]:
                # only movable state is service unavailable
                raise ServiceUnavailableError("Problem with connection to server")
            
        self.get_data_mutex.acquire()
        
        core = self.cores[self.next_core]
        self.next_core = (self.next_core + 1) % self.core_num
        
        self.get_data_mutex.release()
        
        try:
            data = core._get_data(method, args)
        except PermissionFailError as err:
            raise err
        finally:
            self.state.end_event()
        
        return data
    
    # request test data
    def get_test_data(self):
        #self._debug_msg('request test data')
        td = self.get_data(lolapi.LOLAPI.get_summoners_by_names, (u'\uba38\ud53c93'.encode('utf8'), ))
        return td
    
    # if 'mode' is true, set to debug mode
    # otherwise, turn off debug mode
    def set_debug(self, mode):
        if mode:
            self.debug = mode
            
    def _debug_msg(self, msg):
        if self.debug:
            print 'debug :', msg
            
    def _is_debug(self):
        return self.debug
            
class LOLCore(object):
    def __init__(self, admin, limit):
        # Administrator of this core
        self.admin = admin
        self.req_num = limit[0]
        self.per_time = limit[1]
        
        # Left request counts before reset
        self.left = self.req_num
        self.key = self.admin.key
        self.api = None
        
        self.state = self.admin.state
        self.policy = self.admin.policy
        
        # Condition for mutual exclusive requesting data
        self.req_condition = threading.Condition()
        
        # Get synchronizations from admin
        self.perm_condition = self.admin.perm_condition
        self.global_after_req_mutex = self.admin.global_after_req_mutex
            
        # Initialize LOL API
        self._init_api()
        
    # Close core
    def _close(self):
        self._close_api()
        self.admin = None
        self.req_num = None
        self.per_time = None
        self.left = None
        self.key = None        
        
    def _init_api(self):
        if not self.api:
            self.api = self.admin.api()
        try:
            self.api.init()
            if config.STATUS_INIT:
                self.api.init_status()
            if config.STATIC_INIT:
                self.api.init_static()
        except Exception as err:
            raise InitializeError("API initialization error [%s]" % (str(err)),)
        
    def _close_api(self):
        if self.api:
            self.api.close()
            self.api = None
            
    # Get permission for sending one request to server
    # It blocks if request count is 0 until timer or sync wakes up blocking.
    # If state switching is started during getting permission, it will fail.
    # Note : This function must be called when self.perm_condition is acquired
    # @return true if successful, false otherwise
    def _get_permission(self):
        while True:
            if self.state.is_switch_started():
                return False
            if self.left > 0:
                self.left -= 1
                return True
            else:
                self.perm_condition.wait(self.admin.per_time)
            
    # Basic routine for retrieving data from lol api
    # method : lolapi request method, must be class's method
    # args : tuple of arguments for the method
    # return : tuple of status code tuple (e.g ('200', 'OK')) and data
    # data is either jason data parsed to python obejct or just raw string.
    # When lolapi timeout or error exception raises, it raises timeout or internal exeception
    # respectively
    def _get_data(self, method, args):
        while True:
            self.perm_condition.acquire()
            # get permission
            if not self._get_permission():
                self.perm_condition.release()
                raise PermissionFailError("Failed to get permission")
            
            # only one call to this method works at a moment for each core
            self.req_condition.acquire()
            self.perm_condition.release()
            
            try:
                result = method(self.api, *args)
                self.global_after_req_mutex.acquire()
                status = result[0]
            except lolapi.Error as err:
                self.global_after_req_mutex.release()
                try:
                    raise err
                except lolapi.Timeout as err:
                    if not self.policy.push_timeout():
                        self.admin._call_service_unavailable()
                    raise TimeoutError('Timeout')
                except (lolapi.InitializationFail, lolapi.InvalidUse) as err:
                    # currently, there's no case would come to here
                    if not self.policy.push_error():
                        self.admin._call_service_unavailable()
                    self._close_api()
                    try:
                        self._init_api()
                    except lolapi.InitializationFail as err:
                        raise InternalError(str(err))
                    raise InternalError(str(err))
                except lolapi.Error as err:
                    if not self.policy.push_error():
                        self.admin._call_service_unavailable()
                    raise InternalError(str(err))
                finally:
                    self.req_condition.release()
                    
            else:
                status_code = status[0]
                if status_code == config.SC_OK:
                    # possibly, successful requests after rate exceed request
                    # may be counted after rate reset. so it increases gap between here
                    # and server
                    if self.state.get_substate() == SS_SYNCHRONIZING:
                        self.admin.sync_miss += 1
                        if not self.admin.sync_miss_time:
                            self.admin.sync_miss_time = time.time()
                    
                    # start timing for rate reset
                    self.admin._call_reset_timer()
                    # release locks
                    self.global_after_req_mutex.release()
                    self.req_condition.release()
                    
                    break
                elif status_code == config.SC_LIMIT_EXCEEDED:
                    # synchronize and do it again
                    
                    # call synchonization process, only one call will be accepted.
                    self.admin._call_synchronize()
                    
                    # release locks
                    self.global_after_req_mutex.release()
                    # wait until synchronization is completed
                    self.req_condition.wait(self.per_time)
                    self.req_condition.release()
                    
                    # start again
                    continue
                else:
                    if not self.policy.push_status_code(status_code):
                        self.admin._call_service_unavailable()
                    self.global_after_req_mutex.release()
                    self.req_condition.release()
                    break
        return result
        
# Action command got by pushing errors or status codes
P_PASS = 1
P_SERVICE_UNAVAILABLE = 0

# Policy about when to go service unavailable state
class _ServiceUnavailablePolicy(object):
    class _Counter(object):
        def __init__(self):
            self.cnt = 0
        def inc(self):
            self.cnt += 1
            return self.cnt
        def reset(self):
            self.cnt = 0
        
    def __init__(self):
        # critical error policy
        self.critical_sets = {}
        # multiple error in a row policy
        self.cont_sets = {}
        self.exception_mutex = threading.Semaphore(1)
        # init
        self._init_critical_error_policy()
        self._init_continuous_error_policy()
        
    # one critical error make it goes to s-u state
    def _init_critical_error_policy(self):
        self.critical_set1_name = config.CRITICAL_SET1_NAME
        set1_errors = config.CRITICAL_SET1_ERRORS
        if not self._critical_add_set(self.critical_set1_name, set1_errors):
            raise PolicyFailedError("policy init failed")
        
    # add set of (set name, list of errors) to critical set
    # if set with same name already exists, don't add and return False
    def _critical_add_set(self, sname, errors):
        if sname in self.critical_sets:
            return False
        
        self.critical_sets[sname] = errors
        return True
    
    def _critical_push_error(self, sname, key):
        self.exception_mutex.acquire()
        if not sname in self.critical_sets:
            self.exception_mutex.release()
            return P_PASS
        set = self.critical_sets[sname]
        ret = P_PASS
        if key in set:
            ret = P_SERVICE_UNAVAILABLE
        self.exception_mutex.release()
        return ret
    
    # set describes total error set of certain type
    # cont error set has following structure
    # each set has tuple described in _cont_make_tuple
    # errors in a tuple shares counter and thresh
    # other tuples distinguishe counter and thresh
    # an error must be pushed to one of set
    # by calling _cont_push_error
    def _init_continuous_error_policy(self):
        succ = False
        while True:
            # Add new field
            self.cont_set1_name = config.CONT_ERROR_SET1_NAME
            self.cont_set2_name = config.CONT_ERROR_SET2_NAME
            if not self._cont_add_set(self.cont_set1_name):
                break
            if not self._cont_add_set(self.cont_set2_name):
                break
            
            l = list(config.CONT_ERROR_SET1_TUPLE1_ERRORS)
            t = self._cont_make_tuple(l, config.CONT_ERROR_SET1_TUPLE1_THRESH)
            if not self._cont_add_tuple_to_set(config.CONT_ERROR_SET1_NAME, t):
                break
            
            l = list(config.CONT_ERROR_SET2_TUPLE1_ERRORS)
            t = self._cont_make_tuple(l, config.CONT_ERROR_SET2_TUPLE1_THRESH)
            if not self._cont_add_tuple_to_set(config.CONT_ERROR_SET2_NAME, t):
                break
            
            succ = True
            break
        if not succ:
            raise PolicyFailedError("policy init failed")
        
    # add tuple to set, if set name does not exists, return False
    # if set name not exists, does not add and return False
    def _cont_add_tuple_to_set(self, sname, tup):
        if not sname in self.cont_sets:
            return False
        
        self.cont_sets[sname].append(tup)
        return True
        
    # add set to cont_sets, 
    # if set name already exists, does not add and return False
    def _cont_add_set(self, name):
        if name in self.cont_sets:
            return False
        
        self.cont_sets[name] = []
        return True
    
    # Make and return tuple of (list of errors, thresh, counter) 
    # list : list of erros, all elements in list must have same type
    # thresh : number of cont. erros in 'list' to go to service unavailable
    def _cont_make_tuple(self, list, thresh):
        return (list, thresh, self._Counter())
        
    # Policy in which multiple events in a row causes to service unavailable state
    def _cont_push_error(self, sname, key):
        self.exception_mutex.acquire()
        if not sname in self.cont_sets:
            self.exception_mutex.release()
            return P_PASS
        set = self.cont_sets[sname]
        found = False
        for t in set:
            if key in t[0]:
                found = True
                break
        # if ok, reset all other counters
        if not found:
            self._reset()
            self.exception_mutex.release()
            return P_PASS
        cnt = t[2]
        thresh = t[1]
        check = cnt.inc() < thresh
        ret = P_PASS if check else P_SERVICE_UNAVAILABLE
        self.exception_mutex.release()
        return ret
    
    def push_timeout(self):
        return self._cont_push_error(self.cont_set2_name, 'timeout')
    
    def push_error(self):
        return self._cont_push_error(self.cont_set2_name, 'error')
    
    # For status codes, apply critical policy and cont policy
    def push_status_code(self, code):
        if not self._critical_push_error(self.critical_set1_name, code):
            return P_SERVICE_UNAVAILABLE
        return self._cont_push_error(self.cont_set1_name, code)
    
    # reset all counters of all tuples of all sets
    def _reset(self):
        for set in self.cont_sets:
            for tuple in self.cont_sets[set]:
                tuple[2].reset()
            
    # synchronized reset
    def reset(self):
        self.exception_mutex.acquire()
        self._reset()
        self.exception_mutex.release()


# LOL API with fast multiple request object  
# This provides functionality that one thread can send multiple request
# at once.
class LOLFastAPI(object):
    def __init__(self, servants=None, limit=None, key=None, cores=None, api=None):
        self.admin = LOLAdmin(limit, key, cores, api)
        self.servant_num = servants if servants else config.SERVANT_NUM
        self.servants = []                          # list of servant thread objects
        self.servant_idx = 0                        # next servant index
        self.state = _StateMachine(LOLFastAPI.S_OK) # state of servants
        
        self.get_mutex = threading.Lock()
        
        self.keep_alive_on = False
        self.spec = self.admin.get_spec()
    
    # Commands master can give to servant
    FCMD_DIE = 0    # stop routine and return
    FCMD_GET = 1    # get api data
    
    # Servant state
    S_OK = 0        # OK
    S_SU = 1        # service unavailable
    class _servant(threading.Thread):
        def __init__(self, master, id):
            threading.Thread.__init__(self)
            self.master = master
            self.admin = master.admin
            self.id = id
            import collections
            # object in request is form of (cmd, arg)
            # 'cmd' is one of FCMD_* value
            # 'arg' is variable wrt 'cmd' value
            # FCMD_DIE, arg is not used
            # FCMD_GET, (fastResponse, tuple returned by fastRequest iterator)
            self.requests = collections.deque()
            self.cond = threading.Condition()
            
            # servant is state machine
            self.state = self.master.state
        
        def run(self):
            self.routine()
            
        # order request
        def order(self, tup):
            self.cond.acquire()
            self.requests.append(tup)
            self.cond.notify()
            self.cond.release()
            
        # only number 0 servant is in charge of checking status
        def _check_status(self):
            if not self.state.start_event([LOLFastAPI.S_SU])[0]:
                return
            if self.admin.check_service_status():
                self.state.end_event()
                if not self.state.start_state_switch([LOLFastAPI.S_SU])[0]:
                    return
                self.state.switch_state(LOLFastAPI.S_OK)
                self.state.end_state_switch()
            else:
                self.state.end_event()
            
        def routine(self):
            while True:
                self.cond.acquire()
                first = True
                loop = 0
                while True:
                    try:
                        #print 'LOOP START (' + str(self.id) + ')'
                        if loop < 2:
                            loop += 1
                            tup = self.requests.popleft()
                        else:
                            loop = 0
                            if self.id == 0:
                                self._check_status()
                        first = True
                        break                                 
                    except IndexError:
                        self.cond.release()
                        if self.state.start_event([LOLFastAPI.S_OK])[0]:
                            if not first and self.master.keep_alive_on:
                                try:
                                    self.admin.get_test_data()
                                except Exception:
                                    pass
                            self.state.end_event()
                        elif self.id == 0:
                            self._check_status()
                        first = False
                        self.cond.acquire()
                        self.cond.wait(config.KEEP_ALIVE_INTERVAL)
                self.cond.release()
                
                cmd = tup[0]
                if cmd == LOLFastAPI.FCMD_DIE:
                    break
                elif cmd == LOLFastAPI.FCMD_GET:
                    self._serve_get(tup)
                    
                    
        def _serve_get(self, tup):
            try:
                cmd_arg = tup[1]
                req_iter_tup = cmd_arg[1]
                req_name = req_iter_tup[0]
                req_tup = req_iter_tup[1]
                method = req_tup[0]
                args = req_tup[1]
                res = cmd_arg[0]
            except Exception as err:
                res_tup = (FS_ERROR, str(err))
                res.add_response(req_name, res_tup)
                return
            
            if self.state.start_event([LOLFastAPI.S_OK])[0]:
                do_end = True
                try:
                    result = self.admin.get_data(method, args)
                except TimeoutError as err:
                    res_tup = (FS_TIMEOUT, str(err))
                except ServiceUnavailableError as err:
                    res_tup = (FS_SERVICE_UNAVAILABLE, str(err))
                    # Go to service unavailable state
                    do_end = False
                    self.state.end_event()
                    if self.state.start_state_switch([LOLFastAPI.S_OK])[0]:                        
                        self.state.switch_state(LOLFastAPI.S_SU)
                        self.state.end_state_switch()
                except (Error, Exception) as err:
                    res_tup = (FS_ERROR, str(err))
                else:
                    res_tup = (FS_OK, result)
                    
                if do_end:
                    self.state.end_event()
                    
            else:
                res_tup = (FS_SERVICE_UNAVAILABLE, "Service unavailable,"
                           " servant is trying to restore problem")
                
            res.add_response(req_name, res_tup)
            
    # Initialize serving threads
    def start_multiple_get_mode(self):
        self.admin.init()
        for i in range(self.servant_num):
            servant = self._servant(self, i)
            self.servants.append(servant)
            servant.daemon = True
            servant.start()
    
    def close_multiple_get_mode(self):
        die_tup = (self.FCMD_DIE, None)
        for servant in self.servants:
            servant.order(die_tup)
            
        for servant in self.servants:
            servant.join(60)
            
        self.servants = []
        self.servant_idx = 0
    
    # Returns fastResponse object which will get responses
    # from servants
    # fast_req : fastRequest object containing caller's requests
    def get_multiple_data(self, fast_req):
        self.get_mutex.acquire()
        req_num = fast_req.get_request_num()
        res = FastResponse(req_num)
        for req_tup in fast_req:
            get_tup = (self.FCMD_GET, (res, req_tup))
            servant = self.servants[self.servant_idx]
            servant.order(get_tup)
            self.servant_idx += 1
            self.servant_idx %= self.servant_num
        #print 'adddddded'
        self.get_mutex.release()
        return res
    
    def set_keep_alive(self, level):
        self.keep_alive_on = level
        
    def set_debug(self, level):
        self.admin.set_debug(level)
        
    def get_spec(self):
        return self.spec

# Fast response status codes
FS_OK = 0
FS_TIMEOUT = 1
FS_ERROR = 2
FS_SERVICE_UNAVAILABLE = 3

class FastResponse(object):
    def __init__(self, req_num):
        self.req_num = req_num
        self.response_num = 0
        self.responses = {}
        self.cond = threading.Condition()
        
    class _iterator(object):
        def __init__(self, responses, cond):
            self.responses = responses
            self.cond = cond
            self.cond.acquire()
            self.iter = self.responses.__iter__()
            
        def next(self):
            while True:
                try:
                    name = self.iter.next()
                    if not self.responses[name][1]:
                        continue
                    self.responses[name][1] = False
                    return (name, self.responses[name][0])
                except StopIteration:
                    self.cond.release()
                    raise StopIteration()
            
        def close(self):
            while True:
                try:
                    self.iter.next()
                except StopIteration:
                    break
            self.cond.release()
            
    # return iterator object for responses
    # it iterates through only non-read new responses
    def __iter__(self):
        return self._iterator(self.responses, self.cond)
        
    # Add response
    # If all requests are served, it notifies requester
    # name: name of request in request dictionary
    # tuple : tuple (status_code, data)
    #         'status code' is one of FS_* value
    #         'data' is returned data from API or error message
    def add_response(self, name, tuple):
        self.cond.acquire()
        self.responses[name] = [tuple, True] # data, unread(True)
        self.response_num += 1
        # notify requestor
        if self.response_num >= self.req_num:
            self.cond.notifyAll()
        self.cond.release()
        
    # Wait for responses
    # If 'timeout' is specified, if not all request have gotten
    # response until timeout, it returns False
    # If all response is got, return True
    def wait_response(self, timeout=None):
        ret = True
        self.cond.acquire()
        if self.req_num == self.response_num:
            self.cond.release()
            return ret
        self.cond.wait(timeout)
        if self.req_num > self.response_num:
            ret = False
        self.cond.release()
        return ret
    
    # If responded, it will return tuple
    # If not responded, return None
    def get_response(self, name):
        if name in self.responses:
            self.responses[name][1] = False
            return self.responses[name][0]
        return None
    
    # returns next unread response
    # if no new reponse, return None
    def next_response(self):
        iter = self.__iter__()
        try:
            result = iter.next()
            iter.close()
            return result
        except StopIteration:
            return None
        
    # returns true if all requests are responded,
    # false otherwise.
    def responded_all(self):
        self.cond.acquire()
        result = self.req_num <= self.response_num
        self.cond.release()
        return result
        
    
class FastRequest(object):
    def __init__(self):
        # list of tuple (method, arg)
        self.req_num = 0
        self.counter = 0
        self.reqs = {}
        
    # it is actually not redundant
    class _iterator(object):
        def __init__(self, reqs):
            self.reqs = reqs
            self.iter = reqs.__iter__()
        
        # returns tuple (index of request, request tuple)
        def next(self):
            try:
                name = self.iter.next()
                return (name, self.reqs[name])
            except StopIteration:
                raise StopIteration()
        
    # return iterator object for requests
    def __iter__(self):
        return self._iterator(self.reqs)
    
    # Add request for API
    # tuple: tuple (method, arg)
    #        'method' is API method, 'arg' is tuple of arguments
    #        to the method
    # beware that internal counter may conflict with name of request
    # added by add_request_name method, vice versa.
    def add_request(self, tuple):
        self.reqs[self.counter] = tuple
        self.counter += 1
        self.req_num += 1
        
    # name : request name string
    # tuple : tuple (method, arg) 
    #         meaning is same as add_request method
    def add_request_name(self, name, tuple):
        self.reqs[name] = tuple
        self.req_num += 1
        
    def get_request_num(self):
        return self.req_num

'''
errno
'''
E_PYTHON_ERROR = -1
E_UNKNOWN = 0
E_PERMISSION_FAIL = 1
E_INTERNAL_ERROR = 2
E_SERVICE_UNAVAILABLE_ERROR = 3
E_INITIALIZE_ERROR = 4
E_TIMEOUT_ERROR = 5
E_INVALID_USE = 6
E_POLICY_FAILED = 7
    
class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
    
class PythonBuiltInError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_PYTHON_ERROR)    

class PermissionFailError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_PERMISSION_FAIL)    

class InternalError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_INTERNAL_ERROR)    

class ServiceUnavailableError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_SERVICE_UNAVAILABLE_ERROR)    
        
class InitializeError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_INITIALIZE_ERROR)    
        
class TimeoutError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_TIMEOUT_ERROR)    
        
class InvalidUseError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_INVALID_USE)    
        
class PolicyFailedError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_POLICY_FAILED)    
        
# tests
if __name__ == '__mafin__':
    print 'keep alive test'
    API = LOLFastAPI()
    API.set_debug(True)
    API.start_multiple_get_mode()
    API.set_keep_alive(True)
    for i in range(2):
        time.sleep(10)
        print (i + 1) * 10, 'sec elapsed'
    time.sleep(2)
    API.close_multiple_get_mode()
    
if __name__ == '__main__':
    #time.sleep(1)
    print 'fast api multiple request test'
    API = LOLFastAPI()
    API.set_debug(True)
    API.start_multiple_get_mode()
    API.set_keep_alive(True)
    ids = [2577586, 2580719, 2610449, 2705388, 2706560, 2712005, 2714978, 2716219, 2726954, 2730142]
    print 'started multiple mode'
    for i in range(20):
        req = FastRequest()
        #for i in range(10):
        #    req.add_request((lolapi.LOLAPI.get_summoners_by_names, (u'\uba38\ud53c93'.encode('utf8'),)))
        for id in ids:
            req.add_request((lolapi.LOLAPI.get_summoners_by_ids, (id,)))
        res = API.get_multiple_data(req)
        while not res.wait_response(10):
            pass
        for t in res:
            r = t[1]
            v = r[0]
            if v == 0:
                status = 'OK'
            elif v == 1:
                status = 'TIMEOUT'
            elif v == 2:
                status = 'ERROR'
            elif v == 3:
                status = 'SERVICE UNAVAILABLE'
            else:
                status = 'UNKNOWN'
            if v == 0:
                for name in r[1][1]:
                    name = r[1][1][name]["name"]
                print status, name
            else:
                print status, r[1]
        import random
        time.sleep(random.random() * 5)
    API.close_multiple_get_mode()
    print 'closed multiple mode'
    
# Multiple threads request simultaneously multiple times with random time interval
# If error occurs, it try again until it succeeds
if __name__ == '__mafin__':
    import random
    print 'admin test'
    API = LOLAdmin()
    API.init()
    API.set_debug(True)
    s1 = threading.Semaphore(1)
    class cnt(object):
        def __init__(self):
            self.val = 0
            self.l = threading.Lock()
        def inc(self):
            self.l.acquire()
            self.val += 1
            self.l.release()
        def __str__(self):
            return str(self.val)
    counter = cnt()
    class test(threading.Thread):
        def __init__(self, n, s, t):
            threading.Thread.__init__(self)
            self.s = s
            self.n = n
            self.t = t
        def run(self):
            for i in range(15):
                #counter.inc()
                time.sleep(round(random.random()*self.t, 1))
                #time.sleep(0.1)
                #r = 'th ' + str(self.n) +' '+ str(i) + ' : ' +'req'
                while True:
                    try:
                        result = API.get_data(lolapi.LOLAPI.get_summoners_by_names, (u'\uba38\ud53c93'.encode('utf8'),))
                    except Exception as err:
                        self.s.acquire()
                        print 'th', self.n, i, ': exception', str(err) 
                        self.s.release()
                        if type(err) == ServiceUnavailableError:
                            while True:
                                if API.check_service_status():
                                    print 'th', self.n, i, ': connection is fine' 
                                    time.sleep(round(random.random()*5, 1))
                                    break
                        else:
                            time.sleep(round(random.random()*5, 1))
                    else:
                        break
                self.s.acquire()
                print 'th', self.n, i, ' : ', result[0]
                self.s.release()
            self.s.acquire()
            print 'thread end count : ' + str(counter)
            counter.inc()
            self.s.release()
            
    threads = []
    for i in range(10):
        a = test(i + 1,s1, round(random.random()*40, 0))
        a.daemon = True
        a.start()
        threads.append(a)
    try:
        while True: time.sleep(1)
        #for i in range(len(threads)):
        #    threads[i].join()
    except (KeyboardInterrupt, SystemExit):
        pass
    