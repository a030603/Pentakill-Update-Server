# Pentakill DB connection library 1.0
# This file contains classes for connection to MySQL db.
# configurations of db are set in config.py file.
#
# 2015-02-03 Kim Hyun Seung
# pentakill.kr

from mysql.connector import *
from mysql.connector import errorcode
from pentakill.db import error
from pentakill.db.config import configs

'''
states
'''
S_IDLE = 1
S_INIT = 2
S_EXECUTED = 3

'''
 This is an wrapper class of DB connector provided by MySQL
 It gets rid of tiresome db configuration and makes querying
 more easier.

 To use this class, you must follow this.
 1. after you make instance of this object, you must call init() to
    connect to db server
 2. Then you can query using query() method. There are two mode,
    Buffered and non-buffered mode. In non-buffered mode,
    note that more than 2 queries at the same time is not possible.
    when you query again, it will raise an exception.
    In buffered mode, you can send multiple query at the same time.
    but they consume memory space, so huge query will impact your memory.
 3. When you finish your transaction, make sure that you call
    commit() and close() method to end transaction.

 if connection is made and exception is thrown, you should try again
 or close connection. It is bad not to close connection.
'''
class DB(object):
    def __init__(self, config):
        self.db = None
        self.cursor = None
        self.cursorObj = None
        
        self._buffered = False
        if 'buffered' in config:
            self._buffered = config['buffered']
            
        self.config = config
        
        self.state = S_IDLE
        
    def __str__(self):
        return self.config
    
    def newConfig(self, config):
        self.config = config
        
    def setConfig(self, key, val):
        self.config[key] = val
        
    # Initialize db
    # This function actually connects to database
    # returns True if succeeded, Exception when failed.
    def init(self, buffered=None, timeout=None):
        if self.state != S_IDLE:
            raise error.NotClosed('close DB and try again', error.E_DB_NOT_CLOSED)
        
        config = self.config.copy()
        
        try:
            if buffered != None:
                config['buffered'] = buffered
            if timeout != None:
                config['connection_timeout'] = timeout
                
            self.db = connect(**config)
            
        except Error as err:
            raise error.ConnectionFailure('Failed to connect to DB, ' + str(err)
                                          , error.E_CONNECTION_FAIL)
        else:
            # self.cursor is non buffered cursor
            self.cursor = self.db.cursor(buffered=False)
                
        self.state = S_INIT
            
    def close(self):
        if self.cursorObj:
            self.cursorObj.close()
            self.cursorObj = None
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.db:
            self.db.close()
            self.db = None
        self.state = S_IDLE
    
    # this starts a new transaction
    def begin(self):
        self.query('begin', buffered=False)
        self.state = S_INIT
        
    # when after insertion, modification
    # you should commit to tell db the transaction ended
    def commit(self):
        self.query('commit', buffered=False)
        self.state = S_INIT
            
    # If you want to rollback all the operations in your
    # transaction, use this.
    def rollback(self):
        self.query('rollback', buffered=False)
        self.state = S_INIT
        
    # query 
    # 1. (arg1: string, multi=False) -> (Cursor or Exception)
    # 2. (arg1: string, arg2: tuple of string, multi=False) -> (Cursor or Exception)
    # 3. multi=True -> arg1 is semi-colon separated multiple queries, in this case,
    #                  don't use arg2 tuple to format arg1 string
    #
    # You can pass MySQL query string just by passing the complete one SQL string
    # (number 1 usage), or by passing SQL form string and tuple of data (number 2 usage)
    # When it succeeds it returns Cursor object from which you can fetch rows.
    # Otherwise it raises Exception which contains error code and message of detail
    # Note : It is encouraged to use second usage for security. 
    #        First usage may suffer from malicious attack(e.g. SQL injection)
    def query(self, arg1, arg2=None, multi=False, buffered=None):
        buffered = self._buffered if buffered == None else buffered 
        
        # whatever buffered or not, it must be in INIT state
        # buffered querying after non-buffered querying requires
        # previous cursor to be closed
        if self.state != S_INIT:
            raise error.QueryError('cursor not closed', error.E_QUERY_ERROR)
            
        try:
            if buffered:
                cursor = self.db.cursor(buffered=buffered)
            # non-buffered and no cursor
            else:
                if not self.cursor:
                    self.cursor = self.db.cursor(buffered=False)
                cursor = self.cursor
                
            # query with one arg
            if arg2 == None:
                result = cursor.execute(arg1, multi=multi)
            # query with two arg
            # for insertion, retrieval
            else:
                result = cursor.execute(arg1, arg2, multi=multi)

        except Error as err:
            raise error.QueryError(str(err), error.E_QUERY_ERROR)
        except Exception as err:
            raise error.PythonBuiltInError(str(err), error.E_PYTHON_ERROR)
        else:
            # it does not support Cursor for multi query execution.
            # so it just return mysql iterator object
            if multi:
                return result
            
            cursorObj = Cursor(self, cursor, buffered)
            if not buffered:
                self.cursorObj = cursorObj
                self.state = S_EXECUTED
            return cursorObj

    def callProc(self, proc, args):
        if self.state != S_INIT:
            raise error.QueryError('cursor not closed', error.E_QUERY_ERROR)
        
        if not self.cursor:
            # make an non buffered cursor
            self.cursor = self.db.cursor(buffered=False)
        
        try:
            return self.cursor.callproc(proc, args)
        except Error as err:
            raise error.QueryError('DB error ' + str(err), error.E_QUERY_ERROR)
    
        
# Wrapper for MySQLCursor object
#
# If you don't want to use this wrapper, you can get MySQLCursor object
# by getCursor() method. But you must call close() after you're done
# with it. 
class Cursor(object):
    def __init__(self, db, cursor, buffered, iterator=None):
        self.db = db
        self.cursor = cursor
        self._buffered = buffered
        self.iterator = iterator
        
        # properties 
        self.column_names = self.cursor.column_names
        self.statement = self.cursor.statement
        self.description = self.cursor.description
        
    # get iterator object
    # for multi query execution, you can use for loop to
    # get cursor for each execution
    def __iter__(self):
        if self.cursor:
            return self.cursor.__iter__()
        
    def __str__(self):
        return self.statement
        
    # fetch one row
    def fetchRow(self):
        if self.cursor:
            return self.cursor.fetchone()
    
    # fetch many rows, default is one
    def fetchMany(self, size=1):
        return self.cursor.fetchmany(size)
    
    # fetch all remaining rows
    # When no more rows, MySQL connector raises InterfaceError,
    # it catches it and returns empty list, which is consistent to 
    # fetchMany method.
    def fetchAll(self):
        try:
            return self.cursor.fetchall()
        except InterfaceError as err:
            return []
        
    
    # with MySQLCursor, you can use for loop to
    # fetch each row
    def getCursor(self):
        return self.cursor
    
    # it proceeds function proc at most 'num' rows
    # if 'num' is not given, it fetches all rows
    # proc must return True or something equivalent to that
    # it precedure successful, return False or equivalence when not.
    # it returns when all rows are done or it fails.
    def proceed(self, proc, num=None):
        left = num
        row = self.fetchRow()
        if left == None:
            # proceed all rows
            while row:
                if not proc(row):
                    return False
                row = self.fetchRow()
        else:
            # proceed at most 'num' rows
            while row:
                if not left:
                    break
                if not proc(row):
                    return False
                left -= 1
                row = self.fetchRow()
            
        return True
            
    
    # in buffered mode, unread rows must be fetched
    # before further querying.
    def close(self):
        if self._buffered:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            self.db = None
            return
        if self.cursor:
            if self.cursor.with_rows:
                try:
                    # when no more rows left and call fetchall, 
                    # it raises exception
                    self.cursor.fetchall()
                except InterfaceError:
                    pass
            self.cursor = None
        if self.db:
            self.db.cursorObj = None
            self.db.state = S_INIT
            self.db = None
        
class PentakillDB(DB):
    def __init__(self):
        DB.__init__(self, configs.pentakill)
        
# This lines are executed only when this script is executed as main script

# test code for retrieval
if __name__ == '__main__':    
    print Error
    try:
        db = PentakillDB()
        db.init()
    except AttributeError as err:
        raise err
    else:
        query = ("SELECT s_name, s_id FROM summoners "
                 "WHERE s_id > %s "
                 "ORDER BY s_id desc "
                 "LIMIT 10")
        query2 = ("SELECT s_name, s_id FROM summoners "
                 "WHERE s_id = %s "
                 "LIMIT 10")
        data = ("2576538", )

        #print cursor == db.cursor differenc cursor
        result = db.begin()
        print result
        result = db.query("insert into summoners (s_id, s_name, s_name_abbre) "
                          "values (1111112, \'zzzz\', \'zzzz\')")
        print result
        result.close()
        result = db.rollback()
        print result
        
        result = db.begin()
        print result
        result = db.query("insert into summoners (s_id, s_name, s_name_abbre) "
                          "values (1111112, \'zzzz\', \'zzzz\')")
        print result
        result.close()
        result = db.rollback()
        print result
        
        result = db.begin()
        print result
        result = db.query("delete from summoners "
                          "where s_id = 1111112")
        print result
        result.close()
        result = db.rollback()
        print result        
        
        db.begin()
        result = db.query(query, data)
    
        def proc(row):
            print 'Summonfer ' + str(row[1]), row[0].encode('cp949')
            print result.cursor.rowcount
            return True
        i = 0
        for row in result:
            print 'Summoner ' + str(row[1]), row[0].encode('cp949')
            print result.cursor.rowcount            
            if i > 4:
                break
            i = i + 1
        if result.proceed(proc): 
            print 'success' 
        else: 
            print 'fail'
        print 'fetchrow', result.fetchRow()
        print 'fetchmany1', result.fetchMany(1)
        print 'fetchmany5', result.fetchMany(5)
        print 'fetchall', result.fetchAll()
        result.close()
        # show results
        #for row in result:
            #print row
            
        cursor = db.db.cursor()
        cursor = cursor.execute(query2, data, True)

        for result in cursor:
            print 'row',result.fetchone()
            
        db.commit()
        db.close()
            
# test for buffered mode
# it's ok to execute two queries on one cursor without reading all buffer
# but for utility, it is good to make one cursor for each query
if __name__ == '__main__':    
    def testBufferMode():
        #db = PentakillDB()
        #db.init(buffered=False)
        
        query1 = ("select * from (select s_id, s_name from summoners where s_id >= %s "
                  "order by s_id "
                  "LIMIT 10) a "
                  "order by a.s_id")
        query2 = ("select s_id, s_name from summoners where s_id <= %s "
                  "order by s_id desc "
                  "LIMIT 10")
        query3 = ("select s_id, s_name from summoners where s_id = %s "
                  "order by s_id "
                  "LIMIT 10")
        query4 = ("select s_id, s_name from summoners where s_id = %s "
                  "order by s_id "
                  "LIMIT 10")
        arg = (2576538,)
        arg2 = ("1135567",)
        arg3 = ("2060871",)
        args = [arg, arg2, arg3, arg, arg2]
        print 'buffered test'
        def test(db, query, arg, buffered):
            cursor = db.query(query, arg, buffered=buffered)
            #print '##################test#################'
            row =  cursor.fetchRow()
            if row[0] != int(arg[0]):
                raise Exception
            #print row
            cursor.fetchAll()
            return cursor
        
        # execute 3**n number of n query tests
        # n consecutive query test in which queries are all possible permutations
        # of set {(buffered, close), (not buffered, close), (buffered, not close)}
        def testChain (n, query, args):
            it = []
            num = 0
            for i in range(n):
                it.append([query, args[i], True, True])
            
            while True:
                do(it)
                num += 1
                i = len(it) - 1
                while True:
                    if i < 0:
                        break
                    if not it[i][2]:
                        i -= 1
                        continue
                    elif it[i][3]:
                        it[i][3] = False
                        break
                    else:
                        it[i][2] = False
                        it[i][3] = True
                        break
                if i < 0:
                    break
                for j in range(i+1, len(it)):
                    it[j][2] = True
                    it[j][3] = True
            print 'test successful', num, 'tests'
                
        # list of (query, arg, buffer, close)
        def do(args):
            db = PentakillDB()
            db.init()
            
            for i in args:
                cursor = test(db, i[0], i[1], i[2])
                if i[3]:
                    cursor.close()
                    
            db.close()
            
        #db.close()
        testChain(3, query1, args)
            
    testBufferMode()

# test code for insertion

if __name__ == '__main__':    
    try:
        db = PentakillDB()
        db.init()
    except AttributeError as err:
        raise err
    else:
        query = ("INSERT INTO summoners (s_id, s_name, s_name_abbre) "
                 "VALUES (%s, \"%s\", \"%s\")")
        delete = ("delete from summoners where s_id = %s")
        data = (2576539, "Murphy", "Murphy")
        data2 = (2576539,)
        try:
            result = db.query(delete, data2)
            result.close()
            result = db.query(query, data)
            for (name,) in result:
                print name.encode("utf8")
            result.close()
            result = db.query(delete, data2)
            result.close()
        except Error as err:
            print "Error"
            if err.errno == errorcode.ER_PARSE_ERROR:
                print "sql syntax error"
        else:
            print "finish"
            db.commit()
            db.close()


if __name__ == '__main__':
    db = PentakillDB()
    db.init(timeout=0.5)
    cursor = db.cursor
    results = cursor.execute('select 1; select 2; select 3;', multi=True)
    print results != cursor
    #cursor.execute('select 1;')
    for result in results:
        print result.fetchall()
        
    print 'second'
    
    for row in cursor:
        print row
    db.close()