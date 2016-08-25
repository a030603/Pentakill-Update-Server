# Pentakill update server

import socket, threading, json, urllib, unicodedata
from pentakill.update import updator
from pentakill.lib import tree

# Server configuration
IP = '0.0.0.0'
PORT = 7777
BACKLOG = 20

READ_TIMEOUT = 5.0
LINE_MAX_SIZE = 1024

HDR_SERVER = 'Pentakill Update Server'
HDR_CONTENT_TYPE = 'text/json; charset=utf-8'
HDR_ACCESS_CONTROL_ORIGIN = '*'
HDR_KEEP_ALIVE = 5

# Update server runs in dedicated thread
# Each connection runs in another dedicated thread
class UpdateServer(object):
    def __init__(self, ip=IP, port=PORT, backlog=BACKLOG):
        self.ip = ip
        self.port = port
        self.backlog = backlog
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        
        self.updator = updator.UpdateModule()
        
        self.routine = None
    
    def init(self):
        self.updator.init()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.sock.bind((self.ip, self.port))

    def start(self):
        self.sock.listen(self.backlog)
        self.routine = self.ServerRoutine(self)
        self.routine.daemon = True
        self.routine.start()
        
    def get_updator(self):
        return self.updator
            
    def shutdown(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        ip = '127.0.0.1' if self.ip == '0.0.0.0' else self.ip
        # listening socket close must come first
        self.sock.close()
        sock.connect((ip, self.port))
        #time.sleep(20)
        sock.close()
        self.updator.close()
        self.routine.join(60)
        
    class ServerRoutine(threading.Thread):
        def __init__(self, server):
            threading.Thread.__init__(self)
            self.server = server
            self.sock = self.server.sock
            self.servers = tree.RedBlackTree()
            
            self.summoner_name_tree = tree.RedBlackTree()
            self.summoner_id_tree = tree.RedBlackTree()
            self.match_tree = tree.RedBlackTree()
            self.current_game_tree = tree.RedBlackTree()            
            
        def run(self):
            self._routine()
            
        # Server routine
        def _routine(self):
            n = 0
            while True:
                try:
                    conn, addr = self.sock.accept()
                    server = Server(n, conn, addr, self)
                    server.Daemon = True
                    self.servers.acquire_mutex()
                    self.servers.insert(n, server)
                    self.servers.release_mutex()
                    # server should start after inserted to tree
                    server.start()
                    n += 1
                except socket.error as err:
                    break
            
            left_servers = tree.RedBlackTree()
            self.servers.acquire_mutex()
            while True:
                server = self.servers.delete_root()
                if server is None:
                    break
                try:
                    server.conn.shutdown(socket.SHUT_RDWR)
                except socket.error:
                    pass
                server.conn.close()
                #print 'closed serv sock'
                n += 1
                left_servers.insert(n, server)
            self.servers.release_mutex()
            
            while True:
                server = left_servers.delete_root()
                if server is None:
                    break
                server.join(10)
            print 'Server exits'
        
class SyncInitFinal(updator.UpdatorInitFinal):
    def __init__(self, key, tree):
        self.tree = tree
        self.key = key
        self.cond = threading.Condition()
        
    def get_condition(self):
        return self.cond
    
    def initialize(self):
        pass
        
    def finalize(self):
        self.tree.acquire_mutex()
        self.tree.delete(self.key)
        self.cond.acquire()
        self.cond.notifyAll()
        self.cond.release()
        self.tree.release_mutex()
        
    def rollback(self):
        self.finalize()
        
    # Assumed tree mutex is acquired before
    # This method always releases tree mutex
    def wait_end(self, tree):
        self.cond.acquire()
        tree.release_mutex()
        self.cond.wait()
        self.cond.release()
    
class PollingInitFinal(SyncInitFinal):
    def __init__(self, key, tree):
        super(PollingInitFinal, self).__init__(key, tree)
        self.sema = threading.Semaphore(0)
        
    def initialize(self):
        self.sema.release()
        
    def wait_start(self):
        self.sema.acquire()
        
class Server(threading.Thread):
    def __init__(self, id, conn, addr, routine):
        super(Server, self).__init__()
        self.id = id
        self.conn, self.addr = conn, addr
        self.request, self.arg = None, None
        self.conn.settimeout(READ_TIMEOUT)
        self.module = routine.server.get_updator()
        
        self.servers = routine.servers
        
        self.summoner_name_tree = routine.summoner_name_tree
        self.summoner_id_tree = routine.summoner_id_tree
        self.match_tree = routine.match_tree
        self.current_game_tree = routine.current_game_tree
        
        self.data = None
        
    def run(self):
        print 'client :', self.addr, 'start'
        cnt = 0
        parser = self._RequestParser(self.conn)
        sender = self._ResponseSender(self.conn)
        close = False
        while True:
            try:
                self.data = {}
                parser.parse_request()
                
                headers = parser.get_headers()
                hdr_conn = parser.get_header('Connection')
                if hdr_conn and hdr_conn == 'close':
                    close = True
                    #print 'connection', hdr_conn
                
                method, path, http = parser.get_request()
                # Put data from request
                method = method.upper()
                if method == 'GET':
                    # Get method data
                    data = parser.get_get()
                elif method == 'POST':
                    body = parser.get_body()
                    data = json.loads(body, 'utf8')
                    #data['name'] = unicodedata.normalize('NFKD', data['name'])
                    if 'name' in data:
                        data['name'] = data['name'].encode('utf8')
                else:
                    continue
                self._put_input(data)
                
                split = path.split('?')[0].split('/')
                pathdir = split[1]
                if pathdir.lower() != 'update':
                    continue
                
                msg = self._work_for_request()
                
                sender.set_status('200', 'OK')
                sender.look_headers(headers)
                sender.set_body(msg)
                sender.send_respond()
                sender.reset()
                
                if close:
                    break
            except (Error, socket.error) as err:
                import traceback
                #traceback.print_exc()
                print err
                break
            except (KeyError, ValueError, Exception) as err:
                cnt += 1
                if cnt >= 10:
                    break
                continue
            
        print 'client :', self.addr, 'close'
        self.servers.acquire_mutex()
        self.servers.delete(self.id)
        self.servers.release_mutex()
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.conn.close()
        
    def _put_input(self, data):
        self.data['request'] = data['request']
        self.data['type'] = data['type']
        if 'id' in data:
            self.data['id'] = int(data['id'])
        if 'name' in data:
            #self.data['name'] = unicode(data['name'])
            self.data['name'] = urllib.unquote(data['name']).decode('utf8')
        if self.data['request'] == 'add':
            if 'block' in data:
                self.data['block'] = bool(data['block'])
            else:
                self.data['block'] = True
        
    # Always id comes first than name
    def _work_for_request(self):
        self._check_args()
        request = self.data['request']
        type = self.data['type']
        id = self.data['id'] if 'id' in self.data else None
        name = self.data['name'] if 'name' in self.data else None
        
        tree = self._get_tree()
        self.data['tree'] = tree
        tree.acquire_mutex()
        res = self._lookup_tree_and_make_response()
        
        if res:
            return res
        # check update policy
        db = None
        policy = self.module.getPolicy()
        if type == 'summoner':
            do, left, db = policy.check_summoner_update(id, name)
            
        if type == 'summoner':
            if request == 'check' or not do:
                db.close()
                return json.dumps({'completed':True, 'left':left})
        elif type == 'match' and request == 'check':
            return json.dumps({'error':True, 
                               'message':"can not determine if updated"})
        
        # from here request is 'add'
        block = self.data['block']
        if type == 'summoner':
            updator = self.module.getSummonerUpdator()
        elif type == 'match':
            updator = self.module.getMatchUpdator()
        
        key = id if id is not None else name
        if block:
            initfinal = SyncInitFinal(key, tree)
            updator.init(db, initfinal)
        else:
            initfinal = PollingInitFinal(key, tree)
            updator.init(db, initfinal)
        if 'id' in self.data:
            updator.put_data({'id':self.data['id']})
        else:
            updator.put_data({'name':self.data['name']})
        
        # add to tree
        # if update is already processing, wait
        tree.acquire_mutex()
        result = tree.insert(key, updator)
        if not result:
            updator.close()
            res = self._lookup_tree_and_make_response()
            return res
        tree.release_mutex()
        
        # order update
        self.module.orderUpdate(updator)
        
        # wait until completed or started
        if block:
            tree.acquire_mutex()
            initfinal.wait_end(tree)
            return json.dumps({'completed':True})
        else:
            initfinal.wait_start()
            prog = updator.get_progression()
            return json.dumps({'completed':False, 'progress':prog})
            
    def _check_args(self):
        request = self.data['request']
        type = self.data['type']
        if request != 'add' and request != 'check':
            raise WorkError('invalid request type')
        
        if type == 'summoner':
            if (not 'id' in self.data and
                not 'name' in self.data):
                raise WorkError('arguments not given')
            return
        elif type == 'match':
            if (not 'id' in self.data):
                raise WorkError('arguments not given')
        else:
            raise WorkError('invalid type')
        
    # Assumed tree mutex is acquired
    # This method always releases tree mutex
    def _lookup_tree_and_make_response(self):
        tree = self.data['tree']
        block = self.data['block'] if 'block' in self.data else False
        key = self.data['id'] if 'id' in self.data else self.data['name']
        updator = tree.retrieve(key)
        if updator is None:
            tree.release_mutex()
            return None
        if block:
            updator.get_initfinal().wait_end(tree)
            return json.dumps({'completed':True})
        else:
            prog = updator.get_progression()
            tree.release_mutex()
            return json.dumps({'completed':False, 'progress':prog})
        
    def _get_tree(self):
        type = self.data['type']
        if type == 'summoner':
            if 'id' in self.data:
                return self.summoner_id_tree
            elif 'name' in self.data:
                return self.summoner_name_tree
        elif type == 'match':
            return self.match_tree
            
    class _ResponseSender(object):
        def __init__(self, conn):
            self.conn = conn
            self.reset()
            
        def reset(self):
            self.status, self.status_msg = None, None
            self.req_headers = None
            self.headers = {}
            self.body = None
            self.keep_alive = True
            
        def look_headers(self, headers):
            if 'connection' in headers:
                if headers['connection'] == 'close':
                    self.keep_alive = False
            
        def add_headers(self, headers, overwrite=True):
            for key in headers:
                self.add_header(key, headers[key], overwrite)
            
        def add_header(self, key, value, overwrite=True):
            for name in self.headers:
                if overwrite and name.lower() == key.lower():
                    self.headers[name] = value
                    return
            self.headers[key] = value
            
        def _remove_header(self, key):
            for name in self.headers:
                if name.lower() == key.lower():
                    return self.headers.pop(name, None)
            return None
            
        def set_status(self, status, msg):
            self.status, self.status_msg = status, msg
            
        def set_body(self, body):
            self.body = body
            
        def send_respond(self):
            rheaders = {} if self.req_headers is None else self.req_headers
            size = 0
            if self.body:
                size = len(self.body)
                self.add_header('Content-Length', size)
                body = self.body
            else:
                self._remove_header('Content-Length')
                body = ''
            self._remove_header('Transfer-Encoding')
            self.add_header('Server', HDR_SERVER, False)
            self.add_header('Content-Type', HDR_CONTENT_TYPE, False)
            self.add_header('Access-Control-Allow-Origin', 
                            HDR_ACCESS_CONTROL_ORIGIN, False)
            if self.keep_alive:
                self.add_header('Keep-Alive', 'timeout=' + str(HDR_KEEP_ALIVE), False)
            else:
                self.add_header('Connection', 'close', True)
            respond_line = 'HTTP/1.1 %s %s\r\n' % (self.status, self.status_msg)
            headers = []
            for name in self.headers:
                header = '%s: %s' % (name, self.headers[name])
                headers.append(header)
            headers = '\r\n'.join(headers) + '\r\n\r\n'
            
            message = '{0}{1}{2}'.format(*(respond_line, headers, body))
            #print 'body', body
            self.conn.sendall(message)
            
    class _RequestParser(object):
        def __init__(self, conn):
            self.conn = conn
                
        def _init(self):
            self.method, self.path, self.http = None, None, None
            self.get = {}
            self.headers = {}
            self.body = None
            
        def _readline(self):
            size = LINE_MAX_SIZE
            array = bytearray(size)
            cnt = 0
            while True:
                c = self.conn.recv(1)
                if not c:
                    break
                array[cnt] = c
                cnt += 1
                if cnt == size or c == '\n':
                    break
                
            return str(array[:cnt])
                
        def _safe_read(self, size):
            array = []
            cnt = 0
            left = size
            while True:
                cs = self.conn.recv(left)
                read = len(cs)
                if read == 0:
                    raise ParseError('connection closed while '
                                     'expected bytes are left')
                array.append(cs)
                cnt += read
                left -= read
                if left == 0:
                    break
            
            return ''.join(array)
        
        def _chunked_read(self):
            chunks = []
            
            while True:
                line = self._readline()
                
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
                    raise ParseError('invalid chunk size')
                
                if not chunk_size:
                    # read CRLF
                    self._safe_read(2)
                    break
                
                chunk = self._safe_read(chunk_size)
                # read CRLF in the end of chunk
                self._safe_read(2)
                chunks.append(chunk)
                
            # We assume there is no any trailer
            return ''.join(chunks)
            
        def _parse_get(self):
            if self.method != 'GET':
                return
            
            two = self.path.split('?')
            if len(two) < 2:
                return
            
            pairs = two[1].split('&')
            for pair in pairs:
                try:
                    key, val = pair.split('=')
                    self.get[key] = val
                except ValueError:
                    raise ParseError('not enough key value data')
                
        def _parse_headers(self):
            while True:
                header = self._readline()
                header = header.strip()
                if len(header) == 0:
                    break
                keyval = header.split(':')
                key = keyval[0].strip().lower()
                val = ':'.join(keyval[1:]).strip().lower()
                self.headers[key] = val
            
        def _parse_request_start(self):
            header = self._readline()
            try:
                method, path, http = header.strip().split(' ')
                self.method, self.path, self.http = method, path, http
            except Exception:
                raise ParseError('invalid request header')
            
        def _parse_body(self):
            if self.method.upper() == 'POST':
                if 'content-length' in self.headers:
                    size = int(self.headers['content-length'])
                    data = self._safe_read(size)
                    self.body = data
                elif 'transfer-encoding' in self.headers:
                    encoding = self.headers['transfer-encoding']
                    if encoding != 'chunked':
                        raise ParseError('unsupported transfer encoding')
                    
                    data = self._chunked_read()
                    self.body = data
                else:
                    raise ParseError('cannot read body')
                
        def parse_request(self):
            self._init()
            self._parse_request_start()
            self._parse_get()
            self._parse_headers()
            self._parse_body()
            
        def get_get(self):
            return self.get.copy()
            
        def get_header(self, key):
            key = key.lower()
            if key in self.headers:
                return self.headers[key]
            return None
        
        def get_headers(self):
            return self.headers
        
        def get_request(self):
            return (self.method, self.path, self.http)
        
        def get_body(self):
            return self.body

E_UNKNOWNR = 0     
E_PARSE_ERROR = 1       # Error during request parsing
E_WORK_ERROR = 2        # Error during request processing
    
class Error(Exception):
    def __init__(self, msg, errno=None):
        self.msg = msg
        self.errno = errno or -1
        
    def __str__(self):
        return self.msg + " (" + str(self.errno) + ")"
            
class UnknownError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_UNKNOWN)
            
class ParseError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_PARSE_ERROR)
        
class WorkError(Error):
    def __init__(self, msg):
        Error.__init__(self, msg, E_WORK_ERROR)
        
if __name__ == '__main__':
    import time
    # Start server
    print 'Pentakill Update Server 1.0'
    server = UpdateServer()
    server.init()
    server.start()
    print 'Server started'
    try:
        time.sleep(99999)
    except KeyboardInterrupt:
        pass
    server.shutdown()
    