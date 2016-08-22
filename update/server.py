# Pentakill update server

import socket, threading, json
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
HDR_CONNECTION = 'Keep-Alive'

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
                    print 'client :', addr
                    server = Server(conn, addr, self)
                    server.Daemon = True
                    server.start()
                    self.servers.insert(n, server)
                    n += 1
                except socket.error as err:
                    break
            
            servers = tree.RedBlackTree()
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
                servers.insert(n, server)
                
            while True:
                print 'delete'
                server = servers.delete_root()
                if server is None:
                    break
                print 'start join'
                server.join(10)
                print 'joined'
            print 'exits'
                
class PollingInitFinal(updator.UpdatorInitFinal):
    def __init__(self, key, tree, sema):
        self.tree = tree
        self.sema = sema
        self.key = key
    
    def initialize(self):
        self.sema.release()
        
    def finalize(self):
        self.tree.acquire_mutex()
        self.tree.delete(self.key)
        self.tree.release_mutex()
        
    def rollback(self):
        self.finalize()
        
class SyncInitFinal(updator.UpdatorInitFinal):
    def __init__(self, key, tree, sema):
        self.tree = tree
        self.sema = sema
        self.key = key
    
    def initialize(self):
        pass
        
    def finalize(self):
        self.tree.acquire_mutex()
        self.tree.delete(self.key)
        self.tree.release_mutex()
        self.sema.release()
        
    def rollback(self):
        self.finalize()
    
class Server(threading.Thread):
    def __init__(self, conn, addr, routine):
        super(Server, self).__init__()
        self.conn, self.addr = conn, addr
        self.request, self.arg = None, None
        self.conn.settimeout(READ_TIMEOUT)
        self.module = routine.server.get_updator()
        
        self.summoner_name_tree = routine.summoner_name_tree
        self.summoner_id_tree = routine.summoner_id_tree
        self.match_tree = routine.match_tree
        self.current_game_tree = routine.current_game_tree
        
        self.data = None
        
    def run(self):
        cnt = 0
        parser = self._RequestParser(self.conn)
        sender = self._ResponseSender(self.conn)
        while True:
            try:
                self.data = {}
                parser.parse_request()
                method, path, http = parser.get_request()
                body = parser.get_body()
                
                # Check validity of request
                if method.upper() != 'POST' or not body:
                    continue
                split = path.split('/')
                pathdir = split[1]
                if pathdir.lower() != 'update':
                    continue
                
                # Body should be json data
                data = json.loads(body)
                
                self._put_input(data)
                
                msg = self._work_for_request()
                sender.set_body(msg)
                sender.set_status('200', 'OK')
                sender.send_respond()
                sender.reset()
            
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
            
        print 'server returns'
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
            self.data['name'] = unicode(data['name'])
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
        val = self._retrieve_value_from_tree()
        if val:
            prog = val.get_progression()
            return json.dumps({'completed':False, 'progress':prog})
        #print 'not found tree'
        db = None
        policy = self.module.getPolicy()
        #print id, name
        if type == 'summoner':
            success, left, db = policy.check_summoner_update(id, name)
            
        if type == 'summoner':
            if request == 'check' or not success:
                db.close()
                return json.dumps({'completed':True, 'left':left})
        elif request == 'check' and type == 'match':
            return json.dumps({'completed':True})
        
        # request is 'add'
        block = self.data['block']
        sema = threading.Semaphore(0)
        if type == 'summoner':
            updator = self.module.getSummonerUpdator()
        elif type == 'match':
            updator = self.module.getMatchUpdator()
        
        key = id if id is not None else name
        if block:
            updator.init(db, SyncInitFinal(key, tree, sema))
        else:
            updator.init(db, PollingInitFinal(key, tree, sema))
        if 'id' in self.data:
            updator.put_data({'id':self.data['id']})
        else:
            updator.put_data({'name':self.data['name']})
        
        tree.acquire_mutex()
        result = tree.insert(key, updator)
        if not result:
            updator.close()
            updator = tree.retrieve(key)
            prog = updator.get_progression()
            tree.release_mutex()
            if block:
                return json.dumps({'error':'request fail'})
            else:
                return json.dumps({'completed':False, 'progress':prog})
        #print 'inserted'
        tree.release_mutex()
        
        self.module.orderUpdate(updator)
        sema.acquire()
        prog = updator.get_progression()
        if block:
            return json.dumps({'completed':True})
        else:
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
        
    def _retrieve_value_from_tree(self):
        tree = self.data['tree']
        tree.acquire_mutex()
        key = self.data['id'] if 'id' in self.data else self.data['name']
        val = tree.retrieve(key)
        tree.release_mutex()
        return val
        
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
            self.headers = {}
            self.body = None            
            
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
            self.add_header('Connection', HDR_CONNECTION, False)
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
            
        def _parse_headers(self):
            while True:
                header = self._readline()
                header = header.strip()
                if len(header) == 0:
                    break
                keyval = header.split(':')
                if len(keyval) != 2:
                    raise ParseError('invalid header')
                key = keyval[0].strip().lower()
                val = keyval[1].strip().lower()
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
            self._parse_headers()
            self._parse_body()
            
        def get_header(self, key):
            if key.lower() in self.headers:
                return self.headers[key.lower()]
            return None
        
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
    