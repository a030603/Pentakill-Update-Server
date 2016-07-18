# Test for mysql connector
if __name__ == '__main__':
    def assert_fetch_fail(cursor):
        try:
            cursor.__iter__().next()
        except Exception:
            pass
        else:
            assert(0)
    def assert_fetch_one(cursor):
        try:
            print cursor.__iter__().next()
        except Exception:
            assert(0)
        else:
            pass
        
    from mysql.connector import *
    from mysql.connector import errorcode
    pentakill = {
        'user': 'guest',
        'password': '1234',
        'host': '127.0.0.1',
        'database': 'pentakill',
        'port': '3306',
      }   
    
    """ 
    All rows of non-buffered execution must be fetched before executing next query.
    Rows of bufferd execution don't need to be fetched before executing next query.
    If you do next query, previous rows are all gone.
    """
    
    # Test if double non-buffer on single fails
    db = connect(**pentakill)
    cursor = db.cursor(buffered=False)
    cursor.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    try:
        cursor.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    except Exception:
        print "Double non-buffer single passed"
    assert_fetch_one(cursor)
    cursor.close()
    db.close()
    
    # Test if double non-buffer on multiple fails
    db = connect(**pentakill)
    cursor1 = db.cursor(buffered=False)
    cursor2 = db.cursor(buffered=False)
    cursor1.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    try:
        cursor2.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    except Exception:
        print "Double non-buffer multiple passed"
    assert_fetch_one(cursor1)
    assert_fetch_fail(cursor2)
    cursor1.close()
    cursor2.close()
    db.close()    
    
    # Test if double buffered on one cursor succeeds    
    db = connect(**pentakill)
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    assert_fetch_one(cursor)
    cursor.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    assert_fetch_one(cursor)
    print "Double buffer single passed"
    cursor.close()
    db.close()
    
    # Test if double buffered on multiple cursor succeeds    
    db = connect(**pentakill)
    cursor1 = db.cursor(buffered=True)
    cursor2 = db.cursor(buffered=True)
    cursor1.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    cursor2.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    assert_fetch_one(cursor1)
    assert_fetch_one(cursor2)
    print "Double buffer multiple passed"    
    cursor1.close()
    cursor2.close()
    db.close()    
    
    # Test if buffered after non-buffered fails
    db = connect(**pentakill)
    cursor1 = db.cursor(buffered=False)
    cursor2 = db.cursor(buffered=True)
    cursor1.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    try:
        cursor2.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    except:
        print "Bufferd after non-buffered passed"
    #print cursor2.__iter__().next()
    assert_fetch_one(cursor1)
    assert_fetch_fail(cursor2)
    cursor1.close()
    cursor2.close()
    db.close()
    
    # Test if non-buffered after buffered succeeds
    db = connect(**pentakill)
    cursor1 = db.cursor(buffered=True)
    cursor2 = db.cursor(buffered=False)
    cursor1.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    cursor2.execute("SELECT * FROM summoners WHERE s_id = 2576538")
    assert_fetch_one(cursor1)
    assert_fetch_one(cursor2)
    print "Non-bufferd after buffered passed"
    cursor1.close()
    cursor2.close()
    db.close()