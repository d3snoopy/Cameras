from cameras.run.db import query_db
#rom cameras.cameras import app
from os import statvfs
from os.path import exists
import json

def getStatus():
  status = dict()

  if query_db('SELECT rowid FROM recSettings', ()): #This catches an unconfigured db.
    saveLoc = query_db('SELECT saveLoc FROM recSettings WHERE rowid = 1', one=True)['saveLoc']
  else:
    saveLoc = None

  if saveLoc:
    status['saveLoc'] = saveLoc
    if exists(saveLoc):
      status['freespace'] = sizeof_fmt(statvfs(saveLoc).f_frsize * statvfs(saveLoc).f_bavail)
    else:
      status['freespace'] = 'Cannot determine free space'

  if exists("/tmp/camStatus"):
    with open("/tmp/camStatus","r") as f: status['camStatus'] = json.load(f)

  return status


def putStatus(status):
  # Status is a list of dictionaries with the keys 'name' and 'status'
  with open("/tmp/camStatus","w") as f: json.dump(status, f)
  return exists("/tmp/camStatus")


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
