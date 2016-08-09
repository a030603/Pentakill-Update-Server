# Pentakill HTTP connection module 1.0
# This module provides IPv4 HTTP, HTTPS client socket
# It only supports HTTP/1.1

# It does not support other ip versions like IPv6 and
# files in the request body yet.

import socket
import ssl
import time
import zlib

'''
One connection obeject can serve one request at one time. There are six states
for socket.

S_IDLE                : Socket is in idle state, you can set a new request in this state.
S_REQ_STARTED         : You put an request, you can put headers or send request.
S_REQ_SENT            : You sent request, you can get response object and read it.
S_MSG_READ            : You got message, you must read response and close message.
S_SECOND_REQ_STARTED  : Before you close message, you set another request.
S_SECOND_REQ_SENT     : Before you close message, you sent another request.

How to use:
1. Make connection object such as HTTP, HTTPS (conn = HTTP(host, port)) (->S_IDLE)
2. Set request by giving http method and path. (conn.setRequest('GET', '/')) (S_IDLE->S_REQ_STARTED)
3. Put headers (conn.putHeader('User-Agent', 'Pentakill')) (S_REQ_STARTED->S_REQ_STARTED)
4. Send request(conn.sendRequest()) (S_REQ_STARTED->S_REQ_SENT)
5. Get response (msg = conn.getResponse()) (S_REQ_SEND->S_MSG_READ)
6. Read response and close response (msg.read(), msg.close()) (S_MSG_READ->S_IDLE)
7. After 5, but before closing response, you can set and send another request. 
   You may set another request (conn.setRequest('GET', '/status')) (S_MSG_READ->S_SECOND_REQ_STARTED)
   Put headers and send request (conn.sendRequest()) (S_SECOND_REQ_STARTED->S_SECOND_REQ_SENT)
   in same way as 2~4 step. But before you get response for the second request (msg = conn.getResponse()),
   You must read and close first response by msg.read() and msg.close() 
   (S_SECOND_REQ_SENT->S_REQ_SENT if you close after sending request,
    S_SECOND_REQ_STARTED->S_REQ_STARTED if you close before sending). 

Note: If you do not read all message when you close response, the connection is in 
      inconsistent state and may raise error.
Note: If you excepted an critical error, you must close object and either start again
      from 2 or make new object
Note: When response contains 'Content-Length' or 'Transfer-Encoding: chunked' header,
      response will automatically closed when you just call read function. chunked
      message will neglect your argument for read() function. But if 'Content-Length' is
      given, close() called automatically only when you give no argument, or argument
      you've given is enough to read all rest message. Otherwise, you must call close()
      method manually. So if you are not sure, it's safe to call close() after
      you read all message.
Note: This module is not thread-safe.
'''

#Set of states of HTTP object
S_IDLE = 0
S_REQ_STARTED = 1
S_REQ_SENT = 2
S_MSG_READ = 3
S_SECOND_REQ_STARTED = 4
S_SECOND_REQ_SENT = 5


#Other constants
C_TBUFSIZE = 8
C_BUFSIZE = 1024

'''
IP constants
'''
IPV4 = socket.AF_INET
IPV6 = socket.AF_INET6
IPV46 = -1
IPV64 = -2

_SUPPORTED_ENCODING = ['identity', 'gzip', 'deflate', 'zlib']

class HTTP(object):
    # host : string representation of ipv4 address or host domain
    # port : integer value (default 80)
    # proto : HTTP version without dot
    # timeout : integer in seconds, if timeout is set, it raises exception
    #           when respond ping exceeds timeout
    def __init__(self, host, port=80, timeout=None, proto=11, ipv=IPV4):
        self.sock = None
        
        self.host = host
        self.port = port
        self.ips = []
        
        self.ipv = None
        self.proto = None
        self.timeout = timeout
        
        self.headers = {}
        self.method = None
        self.loc = None
        self.body = None
        
        self.sock = None
        self._response = None
        
        self._debug = 0
        
        # it only supports HTTP 1.1
        if proto != 11:
            raise UnsupportedProtocol('Only HTTP 1.1 supported'
                                               , E_UNSUP_PROTOCOL)
        # now only ipv4 is supported
        if ipv != IPV4:
            raise UnsupportedProtocol('Only IPv4 connection is supported'
                                               , E_UNSUP_PROTOCOL)        
        
        self.ipv = ipv        
        self.proto = proto        
        
        self.state = S_IDLE
        
    def setRequest(self, method, loc, timeout=None):
        if self.state != S_IDLE and self.state != S_MSG_READ:
            raise PrematureRequestSet('Read and close response then try again'
                                               , E_PREMATURE_REQSET)
        
        self.headers = {}
        self.body = None
        
        self.method = method
        self.loc = loc
        
        if timeout != None:
            self.timeout = timeout
        
        if self.state == S_IDLE:
            self.state = S_REQ_STARTED
        elif self.state == S_MSG_READ:
            self.state = S_SECOND_REQ_STARTED
                
    def _get_req_first_header(self):
        if self.proto == 11:
            proto = '1.1'
        else:
            raise UnsupportedProtocol('Only HTTP 1.1 supported'
                                               , E_UNSUP_PROTOCOL)
        try:
            return self.method + ' ' + self.loc + ' HTTP/' + proto
        except TypeError as err:
            raise PythonBuiltInError("Python Built-in Error - " + str(err))
    
    def putHeader(self, key, val):
        if self.state != S_REQ_STARTED:
            raise RequestNotStarted('set new request and try again'
                                             , E_REQ_NOT_STARTED)
        
        try:
            self.headers[key] = val
        except TypeError as err:
            raise PythonBuiltInError("Python Built-in Error - " + str(err))
        
    def setbody(self, body):
        self.body = body
        
    def putbody(self, body):
        self.body += body
        
    def sendRequest(self):
        if self.state != S_REQ_STARTED and self.state != S_SECOND_REQ_STARTED:
            raise RequestNotStarted('set new request and try again'
                                             , E_REQ_NOT_STARTED)
                
        # put Host
        if not self.getHeader('host'):
            self.putHeader('Host', self.host)
        
        # put default Accept-Encoding
        if not self.getHeader('accept-encoding'):
            self.putHeader('Accept-Encoding', 'identity')
            
        # put content-length
        if self.body is not None and not self.getHeader('content-length'):
            if not self.getHeader('transfer-encoding') == 'chunked':
                self.putHeader('Content-Length', len(self.body))
            
        headers = []
        headers.append(self._get_req_first_header())
            
        for key in self.headers:
            headers.append('%s: %s' % (key, self.headers[key]))
            
        content = '%s\r\n\r\n' % ('\r\n'.join(headers),)
        
        if self.body is not None:
            content += body
            
        if self._debug:
            print 'headers\n', self.headers
            print 'content\n', content 
        
        if self.sock is None:
            self.connect()
            
        first_loop = True
        while True:
            try:
                self.sock.sendall(content)
            except socket.timeout as err:
                raise Timeout('send timeout', E_TIMEOUT)
            except (socket.error, ssl.SSLError) as err:
                # send can fail for some reason
                # if connection is not will_close or connection timeouts
                # so server closes connection, it may fail.
                
                # ssl timeout error contains string 'timed out'
                if 'timed out' in str(err):
                    raise Timeout(str(err), E_TIMEOUT)
                
                ## not sure ssl connection will raise SSLError or socket error
                # it seems ssl connection raises SSLError
                if first_loop:
                    self.sock.close()
                    self.sock = None
                    self.connect()
                    first_loop = False
                else:
                    raise Error(str(err), E_UNKNOWN)
            else:
                break
            
        if self.state == S_REQ_STARTED:
            self.state = S_REQ_SENT
        elif self.state == S_SECOND_REQ_STARTED:
            self.state = S_SECOND_REQ_SENT
        
    def _set_host(self):
        try:
            addrlist = socket.getaddrinfo(self.host, self.port, socket.AF_INET, 0, socket.IPPROTO_TCP)
        except socket.gaierror:
            raise FailedToGetHost('failed to find host', E_FAILED_GET_HOST)
        
        for addr in addrlist:
            self.ips.append(addr[4][0])
        
    def connect(self):
        # now only ipv4 socket is supported
        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   
        #self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if not len(self.ips):
            self._set_host()
            
        if self.timeout is not None:
            self.sock.settimeout(self.timeout)
            
        for ip in self.ips:
            try:
                self.sock.connect((ip, self.port))
            except socket.error:
                continue
            except SSLError as err:
                if 'timed out' in str(err):
                    continue             
                raise SSLError(str(err), E_SSL_ERROR)
            else:
                return
            
        raise ConnectionFailure('failed to connect to host', E_CONN_FAILURE)
        
    def hasHeader(self, hname):
        for key in self.headers:
            if key.lower() == hname:
                return True
        return False
        
    def getHeader(self, hname):
        for key in self.headers:
            if key.lower() == hname:
                return self.headers[key].lower()
        return ''
    
    def getResponse(self):
        if self.state != S_REQ_SENT:
            raise RequestNotSent('send request and try again',
                                          E_REQ_NOT_SENT)
        
        if self._response:
            raise ResponseNotRead('close response before doing it.'
                                  , E_RESPONSE_NOT_READ)
        
        try:
            response = HTTPResponse(self, self.sock, self.timeout, self._debug)
        # If will_close of last request was False, then sufficient time elapsed
        # from the last request, server may close the connection then, reconnect to server
        except ConnectionClosed:
            self.sock.close()
            self.sock = None
            self.state = S_REQ_STARTED
            self.sendRequest()
            response = HTTPResponse(self, self.sock, self.timeout, self._debug)
        self._response = response
        
        self.state = S_MSG_READ
        
        return response
    
    # close function will never raise exception
    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        if self._response:
            self._response.close()
            self._response = None
        self.state = S_IDLE
        
    # when value is 0, no debug message
    # when greater than 0, show message
    def debugMode(self, mode):
        self._debug = int(mode)
    
class HTTPResponse(object):
    
    def __init__(self, conn, sock, timeout=None, debug=0):
        
        self.conn = conn
        self.sock = sock
        self.fp = None
        #self.fp = sock.makefile('rb', 0)
            
        self.timeout = timeout
        
        self.headers = {}
        
        self.chunked = None
        self.chunked_trailer = False
        self.length = None
        self.version = None
        self.stacode = None
        self.stamsg = None
        
        self.will_close = None
        
        self.encoding = None
        self.trsencoding = None
        
        # debug must be set before reading headers
        self._debug = debug
        
        self._read_status()
        
        self._read_headers()
        
    # slow readline function (two times when read 4k byte)
    # it is better to use readline() method of file object
    # returned by makefile() method. but if timeouts, data read by 
    # makefile() method till now is gone so we should start connection again.
    # but if we use this, we do not have to. call it again and again  << Only in buffered mode
    # Python document states file-like socket object should not have a timeout
    def _readline(self, size=C_BUFSIZE):
        bbuf = bytearray(size)
        cur = 0
        
        while 1:
            c = self.sock.recv(1)
            if len(c) == 0:
                break
            
            bbuf[cur] = c
            cur += 1
            
            if c == '\n':
                break
        
        return str(bbuf[:cur])
        
    def _freadline(self):
        try:
            return self._readline()
            #return self.fp.readline(1024)
        except socket.timeout as err:
            raise Timeout(str(err), E_TIMEOUT)
        except (socket.error, ssl.SSLError) as err:
            # This case is to check SSL connection timeout
            # They raise SSLError instead of socket.Timeout
            if 'timed out' in str(err):
                raise Timeout(str(err), E_TIMEOUT)
            raise Error(str(err), E_UNKNOWN)
        
    # if size is not given, it reads all the content until EOF.
    # it may not read string with size 'size', to get safely, use _safe_read().
    # it raises error when timeouts.
    def _fread(self, size=-1):
        try:
            return self.sock.recv(size)
            #return self.fp.read(size)
        except socket.timeout as err:
            raise Timeout(str(err), E_TIMEOUT)
        except (socket.error, ssl.SSLError) as err:
            if 'timed out' in str(err):
                raise Timeout(str(err), E_TIMEOUT)
            raise Error(str(err), E_UNKNOWN)
        
    def _remove_crlf(self, line):
        cur = len(line)-1
        
        if line[cur] == '\n':
            cur -= 1
            if line[cur] == '\r':
                cur -= 1
            
        return line[:cur+1]
        
    def _read_status(self):
        header = self._freadline()
        if len(header) == 0:
            raise ConnectionClosed('server closed connection', E_CONNECTION_CLOSED)
        
        split = header.split()
        
        if self._debug:
            print "header", header
        
        if len(split) < 3:
            print header
            raise InvalidResponse('not sufficient arguments',
                                  E_INVALID_RESPONSE)
        
        http = split[0]
        status = split[1]
        msg = ' '.join(split[2:])
        
        index = http.find('HTTP/')
        if index < 0:
            raise InvalidResponse('only HTTP procotol supported',
                          E_UNSUP_PROTOCOL)
        
        try:
            version = int(float(http[index+5:len(http)])*10)
        except ValueError:
            raise InvalidValue('invalid HTTP version',
                               E_INVALID_VAL)
        
        self.version = version
        self.stacode = status
        self.stamsg = msg
            
    def _read_headers(self):        
        while True:
            header = self._freadline()
            if len(header) == 0:
                raise ConnectionClosed('server closed connection', E_CONNECTION_CLOSED)
            
            if self._debug:
                print repr(header)
            
            if header == '\r\n':
                break
            
            self._add_header(header)
        
        self._parse_headers()
            
    def _add_header(self, header):
        sep = header.find(':')
        if sep < 0:
            #just ignore invalid header
            return
            #raise InvalidHeader('header without \':\''
            #                             , E_INVALID_HEADER)
        cur = len(header) - 1
        key = header[:sep]
        
        while sep < cur:
            if header[sep+1] == ' ':
                sep += 1
            else:
                break
        
        if header[cur] == '\n':
            if header[cur-1] == '\r':
                cur -= 1
        else:
            cur += 1
                
        if sep >= cur:
            self.headers[key] = ''
        else:
            self.headers[key] = header[sep+1:cur]
    
    def hasHeader(self, hname):
        for key in self.headers:
            if key.lower() == hname:
                return True
        return False
        
    def getHeader(self, hname):
        for key in self.headers:
            if key.lower() == hname:
                return self.headers[key].lower()
        return ''
    
    # returns dictionary of header name, value
    def getHeaders(self):
        return self.headers
        
    def _parse_headers(self):
        # Parse length
        length = self.getHeader('content-length')
        if len(length) > 0:
            try:
                self.length = int(length)
            except ValueError:
                raise InvalidValue('content length must be integer'
                                            , E_INVALID_VAL)
        else:
            self.length = None
            
        # Content-Encoding
        encoding = self.getHeader('content-encoding')
        if encoding:
            if encoding in _SUPPORTED_ENCODING:
                self.encoding = encoding
            else:
                raise InvalidValue('not supported encoding ' + encoding
                                            , E_INVALID_VAL)
        
        # transfer-cncoding
        trsencoding = self.getHeader('transfer-encoding')
        if trsencoding:
            self.trsencoding = trsencoding
            if trsencoding == 'chunked':
                self.chunked = True
                self.chunked_trailer = False

        
        # Parse will_close
        self.will_close = self._is_will_close()
        
    def _is_will_close(self):
        conn = self.getHeader('connection')
        if conn and 'keep-alive' in conn:
            return False
            
        if self.hasHeader('keep-alive'):
            return False
        
        proxy_conn = self.getHeader('proxy-connection')
        if proxy_conn and 'keep-alive' in proxy_conn:
            return False
        
        return True
    
    # if response is chunked, 'size' argument is neglected
    # if content-length is given and 'size' is greater than it,
    # only content-length size will be read.
    def read(self, size=None):
        # reading is already done
        #if self.fp is None:
        #    return ''
            
        if self.trsencoding == 'chunked':
            return self._chunked_read()
        
        if self.length is None:
            if size is None:
                return self._fread()
            else:
                return self._fread(size)
            
        if self.length == 0:
            return ''
        
        try:
            if size is None:
                size = self.length  
            elif size > self.length:
                size = self.length
        except ValueError:
            raise InvalidValue('invalid read size',
                               E_INVALID_VAL)            
            
        #content = self._read(size)
        #we can use safe read here
        content = self._safe_read(size)
        
        self.length -= size
        
        if not self.length:
            self.close() 
        
        return content
    
    def _chunked_read(self):
        chunks = []
        
        while True:
            line = self._freadline()
            
            # check chunk-extension
            comma = line.find(';')
            if comma != -1:
                line = line[:comma]
            else:
                #line = self._remove_crlf(line)
                line = line[:len(line)-2]
            
            try:
                chunk_size = int(line, 16)
            except ValueError:
                raise InvalidValue('invalid chunk size',
                                   E_INVALID_VAL)
            
            if not chunk_size:
                # read CRLF
                self._safe_read(2)
                break
            
            chunk = self._safe_read(chunk_size)
            # read CRLF in the end of chunk
            self._safe_read(2)
            chunks.append(chunk)
            
        # read trailers and last CRLF
        # This version, we assume that we don't have any trailer
        while self.chunked_trailer:
            line = self._freadline()
            # line is empty string when there is
            # no trailer?
            if not line:
                break
            # last CRLF
            if line == '\r\n':
                break
            
        # we read whole message
        self.close()
        return ''.join(chunks)
    
    # it can fail to read all content with size 'size', it could
    # happen when EOF occurs or interrupt is caught. Then it raises error
    # it only returns when all the data has been read
    def _safe_read(self, size=0):
        #if not self.fp:
        #    raise SocketClosed('response is closed',
        #                       E_SOCKET_CLOSED)
        reads = []
        while True:
            read = self._fread(size)
            if not read:
                raise IncompleteRead('Incomplete read',
                                     E_INCOMPLETE_READ)
            size -= len(read)
            reads.append(read)
            if not size:
                break
            
        return ''.join(reads)
    
    # it reads all response and decompress texts (gzip)
    # if there is no content-length and response is not chunked,
    # we don't know the whole message so you should use decompress() method
    def readDecompress(self):
        if self.trsencoding == 'chunked':
            content = self._chunked_read()
        elif self.length != None:
            content = self.read()
        else:
            raise InvalidUseException('can\'t read segment of compressed text'
                                      , E_INVALID_USE)
        
        return self.decompress(content)
        
    # after reading all response, if it is compressed you can use this to
    # decompress
    # if it is not supported encoding or it is not compressed, just return it.
    def decompress(self, content):
        try:
            if self.encoding == 'gzip':
                return zlib.decompress(content, zlib.MAX_WBITS | 16)
            elif self.encoding == 'deflate':
                return zlib.decompress(content, -zlib.MAX_WBITS)
            elif self.encoding == 'zlib':
                return zlib.decompress(content, zlib.MAX_WBITS)
            else:
                return content
        except zlib.error as err:
            raise DecompressFail(str(err), E_DECOMPRESS_FAIL)
    
    # close function will never raise exception
    def close(self):
        # if will_close, close socket
        if self.will_close:
            if self.sock:
                self.sock.close()
                self.sock = None
                self.conn.sock = None
        if self.sock:
            self.sock = None
        if self.fp:
            self.fp.close()
            self.fp = None
        if self.conn:
            if self.conn.state == S_MSG_READ:
                self.conn.state = S_IDLE
            elif self.conn.state == S_SECOND_REQ_STARTED:
                self.conn.state = S_REQ_STARTED
            elif self.conn.state == S_SECOND_REQ_SENT:
                self.conn.state = S_REQ_SENT
            self.conn._response = None
            self.conn = None
            
        if self._debug:
            print 'msg closed'
            
    def getStatus(self):
        return (self.stacode, self.stamsg)
    
    def getVersion(self):
        return self.version
   
# SSL wrapper for HTTP connection
class HTTPS(HTTP):
    def __init__(self, host, port, timeout=None):
        HTTP.__init__(self, host, port, timeout)
    
    def connect(self):
        # now only ipv4 socket is supported
        HTTP.connect(self)
        
        try:
            self.sock = ssl.wrap_socket(self.sock, None, None)
        except ssl.SSLError as err:
            raise SSLError(str(err), E_SSL_ERROR)
        
'''
Exceptions
'''
E_PYTHON_ERROR = -1
E_UNKNOWN = 0
E_UNSUP_PROTOCOL = 1
E_INVALID_USE = 2
E_PREMATURE_REQSET = 3
E_REQ_NOT_STARTED = 4
E_REQ_NOT_SENT = 5
E_TIMEOUT = 6
E_INVALID_HEADER = 7
E_INVALID_VAL = 8
E_INVALID_RESPONSE = 9
E_SOCKET_CLOSED = 10
E_INCOMPLETE_READ = 11
E_FAILED_GET_HOST = 12
E_CONN_FAILURE = 13
E_RESPONSE_NOT_READ = 14
E_DECOMPRESS_FAIL = 15
E_SSL_ERROR = 16
E_CONNECTION_CLOSED = 17

class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
    
class PythonBuiltInError(Error):
    pass    

class UnsupportedProtocol(Error):
    pass

class InvalidUseException(Error):
    pass
    
class PrematureRequestSet(Error):
    pass

class RequestNotStarted(Error):
    pass

class RequestNotSent(Error):
    pass

class Timeout(Error):
    pass

class InvalidHeader(Error):
    pass

class InvalidValue(Error):
    pass

class InvalidResponse(Error):
    pass

class SocketClosed(Error):
    pass

class IncompleteRead(Error):
    pass

class FailedToGetHost(Error):
    pass

class ConnectionFailure(Error):
    pass

class ResponseNotRead(Error):
    pass

class DecompressFail(Error):
    pass

class SSLError(Error):
    pass

class ConnectionClosed(Error):
    pass

if __name__ == '__main__':
    #what if we don't read response and make new request?
    con = HTTP('localhost', 80)
    con.debugMode(1)
    con.setRequest('GET', '/pentakill/')
    con.sendRequest()
    msg = con.getResponse()
    #print repr(con.sock.recv(1000)) + "sadad"
    content = msg.readDecompress()
    #print content + "Asdasdsad"
    msg.close()
    con.setRequest('GET', '/pentakill/search.php?name=CJ%20Entus%20%EC%9A%B0%EC%A3%BC')
    con.sendRequest()
    msg = con.getResponse()
    content = msg.readDecompress()
    print content
    msg.close()
    con.close()

if __name__ == '__main__':
    key = '66badc84-d6f2-4a17-a609-423ae5d8f052'
    
if __name__ == '__m3ain__':
    #test codes
    con = HTTPS('kr.api.pvp.net', 443, 2)
    
    trial = 10
    setreq = 0
    puthea = 0
    sendreq = 0
    getres = 0
    read = 0
    begin = time.time()
    for i in range(trial):
        #con.setRequest('GET', '/api/lol/kr/v2.2/match/1736835012?includeTimeline=true&api_key='+key)
        
        #con.setRequest('GET', '/api/lol/kr/v1.4/summoner/by-name/'+u'\uba38\ud53c'.encode('utf8')+'93?api_key='+key)
        #con.putheader('Host', 'kr.api.pvp.net')
        #con.putheader('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
        #con.putheader('Accept-Encoding', 'identity')
        con.setRequest('GET', '/api/lol/kr/v1.3/game/by-summoner/2576538/recent?api_key='+key)
        con.sendRequest()
        
        msg = con.getResponse()
        #print msg.getStatus()
        #print msg.headers
        content = msg.read()
        #print msg.read()
        msg.close()
    con.close()
    end = time.time()
    print end-begin, 'sec taken'
    


if __name__ == '__1main__':
    import httplib
    con = httplib.HTTPSConnection('kr.api.pvp.net', 443)
    begin = time.time()
    for i in range(10):
        con.putrequest('GET', '/api/lol/kr/v1.3/game/by-summoner/2576538/recent?api_key='+key)
        
        con.endheaders()
        
        msg = con.getresponse()
        
        content = msg.read()
        msg.close()
        #print content
    con.close()
    end = time.time()
    
    print end - begin, 'sec takten for reading'
    
if __name__ == '__2main__':
    #test codes
    #time.sleep(10)
    con = HTTPS('kr.api.pvp.net', 443, 3)
    #con.debugMode(1)
    trial = 1
    begin = time.time()
    for i in range(trial):
        con.setRequest('GET', '/api/lol/kr/v1.3/game/by-summoner/1135567/recent?api_key='+key)
        con.putHeader('Accept-Encoding', 'gzip, deflate, zlib')
        con.sendRequest()
        
        msg = con.getResponse()
        content = msg.readDecompress()
        print 'content:\n', content
        msg.close()
        
    con.close()
    end = time.time()
    print end-begin, 'sec taken'
    
    
if __name__ == '__m2ain__':
    #test codes
    
    con = HTTP('127.0.0.1', 999, timeout=2)
    con.debugMode(1)
    con.setRequest('GET', '/pentakill/search.php?name=CJ%20Entus%20%EC%9A%B0%EC%A3%BC')
    con.putHeader('Host', '127.0.0.1')
    con.putHeader('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    con.putHeader('Accept-Encoding', 'identity')
    con.sendRequest()
    
    begin = time.time()
    try:
        msg = con.getResponse()
        print msg.getStatus()
        print msg.headers 
        content = ''
        for i in range(6):
            time.sleep(1)
            content += msg.read(1)
            print 'read', i+1, 'st'

        print content  
        msg.close()
    except Timeout as err:
        print err
    end = time.time()
    print end-begin, 'sec taken for reading'

if __name__ == '__main__':
    #test codes
    
    HOST = 'ddragon.leagueoflegends.com'
    PORT = 80
    TIMEOUT = 2
    PATH = '/cdn/6.16.2/img/item/3078.png'
    con = HTTP(HOST, PORT, timeout=TIMEOUT)
    con.debugMode(1)
    con.setRequest('GET', PATH)
    con.putHeader('Host', HOST)
    con.putHeader('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    con.putHeader('Accept-Encoding', 'identity')
    con.sendRequest()
    
    begin = time.time()
    try:
        msg = con.getResponse()
        #print msg.getStatus()
        #print msg.headers 
        content = msg.read()
        print content
        msg.close()
    except Timeout as err:
        print err
    end = time.time()
    print end-begin, 'sec taken for reading'
