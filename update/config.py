'''
LOLAdmin configuration
'''

'''
default API
API must be lolapi compatible
'''
from pentakill.lolapi import lolapi
API = lolapi.LOLAPI

'''
default key 
'''
KEY = '66badc84-d6f2-4a17-a609-423ae5d8f052'

'''
default request number per time
form : tuple (req number, per time in sec)
'''
LIMIT = (10, 10.0)

'''
default number of core
'''
CORE_NUM = 10

'''
Status api and static api initialize
'''
STATUS_INIT = True
STATIC_INIT = True

'''
status codes
'''
SC_OK = '200'
SC_BAD_REQUEST = '400'                       # Bad request sent to server
SC_UNAUTHORIZED = '401'                      # invalid key
SC_NOT_FOUND = '404'                         # Not bad, the behavior is controlled by caller
SC_LIMIT_EXCEEDED = '429'                    # Wait until reset
SC_INTERNAL_ERROR = '500'                    # Server has some problem
SC_SERVICE_UNAVAILABLE = '503'               # Server problem

'''
Service unavailable state config
'''
# status codes by which goes to unavailable if just once occur
CRITICAL_SET1_NAME = 'status_code'
CRITICAL_SET1_ERRORS = [SC_UNAUTHORIZED]

# error policies which make it goes to unavailable if occur multiple times in a row
CONT_ERROR_SET1_NAME = 'status_code'
CONT_ERROR_SET1_TUPLE1_ERRORS = [SC_BAD_REQUEST, SC_UNAUTHORIZED, SC_SERVICE_UNAVAILABLE, SC_INTERNAL_ERROR]
CONT_ERROR_SET1_TUPLE1_THRESH = 3

CONT_ERROR_SET2_NAME = 'api_error'
CONT_ERROR_SET2_TUPLE1_ERRORS = ['timeout', 'error']
CONT_ERROR_SET2_TUPLE1_THRESH = 3

'''
LOLFastAPI configuration
'''

'''
servant thread number
'''
SERVANT_NUM = 5

'''
keep alive request time interval
When you set keep alive mode by method set_keep_alive(True),
servants sends test request every moment this time value elapsed 
from last request to maintain connection with server continuously
as long as possible, so that latency is improved.
user is required to specify appropriate floating number value in second
'''
KEEP_ALIVE_INTERVAL = 10.0