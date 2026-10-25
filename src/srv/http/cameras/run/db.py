import sqlite3
from os.path import exists
#import time

DATABASE = 'db/cam.db'
SCHEMA = 'db/db.sql'

#DB Related functions.
def get_db(newdb = False, appContext = True):
  if appContext:
    from flask import g
    db = getattr(g, '_database', None)
  else:
    db = None

  if db is None:
    if not exists(DATABASE): newdb = True
    if appContext:
      db = g._database = sqlite3.connect(DATABASE)
    else:
      db = sqlite3.connect(DATABASE)
    #db.execute("PRAGMA foreign_keys=ON")
    #db.execute('pragma journal_mode=wal')
    if newdb:
      with open(SCHEMA, 'r') as f:
        db.cursor().executescript(f.read())
      db.commit()

    db.row_factory = sqlite3.Row
  return db

def init_db():
    db = get_db(newdb = True)

def query_db(query, args=(), one=False, db=False):
    if not db: db = get_db()
    
    for i in range(10): #ten retries
      #try:
        cur = db.execute(query, args)
  
        rv = cur.fetchall()
        cur.close()
        break
      #except sqlite3.OperationalError:
      #  time.sleep(0.01)
      #  rv = None
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=(), logUpdate=True, db=False, doCommit=True):
    if not db: db = get_db()

    for i in range(10): #ten retries
      #try:
        cur = db.execute(query, args)
        if doCommit: db.commit()
        rv = cur.fetchall()
        cur.close()
        break
      #except sqlite3.OperationalError:
      #  time.sleep(0.01)
      #  rv = None

    return rv
