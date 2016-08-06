# Servant is background thread which accomplishes tasks ordered by master
import threading
import collections

class Servant(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # object in request is tuple which is form of(cmd, arg)
        # 'cmd' is one of FCMD_* value
        # 'arg' is variable wrt 'cmd' value
        self.requests = collections.deque()
        self.cond = threading.Condition()
        
    # Give command to this servant
    def order(self, tup):
        self.cond.acquire()
        self.requests.append(tup)
        self.cond.notify()
        self.cond.release()
        
    def run(self):
        self.routine()
        
    # Routine of servant which circulates infinite loop
    # This function must not return until Exit command is given
    def routine(self):
        pass
    