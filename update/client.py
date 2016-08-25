from pentakill.lolapi import http
import json, time

conn = http.HTTP('127.0.0.1', 7777, timeout=100)
#conn.debugMode(1)
first = True
#ID = 2576538
IN = 'id'
#IN = 'name'
# True False
if False:
#if False:
    type = 'match'
    KEY = 2542091603 
    KEY = 2543013957 # ARAM
    KEY = 2543185185
    KEY = 2542291404
else:
    type = 'summoner'
    KEY = 2576538
    KEY = 2060159 #CJ ENTUS MINGI
    #KEY = 3263292 #CJ ENTUS JJONKK
    KEY = 37750750 #SEXY SWINGS
#KEY = u'\uba38\ud53c93'.encode('utf8')

BLOCK = False
ADD = 'add'
ADD = 'check'
while True:
    print 'START LOOP'
    begin = time.time()
    conn.setRequest('POST', '/update')
    conn.putHeader('Host', '127.0.0.1')
    if first:
        body = json.dumps({'request':ADD, 'type':type, IN:KEY, 'block':BLOCK})
        #first = False
    else:
        body = json.dumps({'request':'check', 'type':type, IN:KEY, 'block':BLOCK})
    print KEY
    conn.setbody(body)
    conn.sendRequest()
    msg = conn.getResponse()
    read = msg.readDecompress()
    end = time.time()
    print round(end - begin, 3), 'elapsed'
    print read
    time.sleep(0.2)