#Functions to process our Status page.
import sys
from aqctrl.run.db import query_db, modify_db
from aqctrl.aqctrl import app
from flask import request
from aqctrl.run import plotting
from datetime import datetime, UTC
from os.path import exists
from json import load


def processForm():
  #Do the processing for the form elements.
  with app.app_context():
    #print(request.form, file=sys.stderr)
    errors=dict()

    #Need to build up GET parameters.
    plot1str = str()
    plot2str = str()
    p1l = list()
    p2l = list()

    #This checks for checkboxes for plotting.
    for f in request.form:
      #print(f)
      if '1chan_' in f:
        plot1str += f.split('_')[1] + ','
        p1l.append(f.split('_')[1])

      if '2chan_' in f:
        plot2str += f.split('_')[1] + ','
        p2l.append(f.split('_')[1])
    
      if 'delFav_' in f:
        #print(f)
        v = f.split('_')[1]
        #print(v)
        modify_db('DELETE FROM AQplot WHERE rowid=?', (v, ))

    #Setup the GET string.
    getStr = 'plot1=' + plot1str + '&plot2=' + plot2str
    #Get the left and right types.
    getStr += '&type1=' + str(int(request.form['1type']))
    getStr += '&type2=' + str(int(request.form['2type']))
    
    #Now, process the start and end times.
    plotStart = 0
    plotEnd = 0
    for i in (('day', 86400), ('hour', 3600), ('min', 60), ('sec', 1)):
      a = request.form['start_' + i[0]]
      try:
        b = int(a)
      except ValueError:
        b = 0
      plotStart += b*i[1]
      a = request.form['end_' + i[0]]
      try:
        b = int(a)
      except ValueError:
        b = 0
      plotEnd += b*i[1]

    #Add this start/end to the GET.
    getStr += '&start=' + str(plotStart)
    getStr += '&end=' + str(plotEnd)
      
    if 'saveFav' in request.form:
      saveFav(p1l, p2l, request.form['name'], plotStart, plotEnd)


    return errors, getStr #Only process if we're saving a favorite. Otherwise, handle all as a redirect.


def saveFav(p1l, p2l, pName, rStart, rEnd):
  #Test if the user asked us to add this to the home plot list..
  with app.app_context():
    toHome = False
    if 'toHome' in request.form:
      toHome = True

    #Save this favorite.
    modify_db('INSERT INTO AQplot (AQname, onHome, relStart, relEnd) VALUES (?, ?, ?, ?)',
      (pName, toHome, rStart, rEnd), logUpdate=False)

    #Get the rowid.
    r = query_db('SELECT last_insert_rowid()', one=True)['last_insert_rowid()']

    for i in p1l:
      modify_db('INSERT INTO plotChan (AQplot, chanNum, axisNum) VALUES (?, ?, ?)',
      (r, i, 1), logUpdate=False)

    for i in p2l:
      modify_db('INSERT INTO plotChan (AQplot, chanNum, axisNum) VALUES (?, ?, ?)',
      (r, i, 2), logUpdate=False)

  return


def createForm():
  #We are plotting in accordance with our GET parameters. Note that the POST redirects.
  #Get the GET parameters.
  with app.app_context():
    now = int(datetime.now(UTC).timestamp())
    l1r = request.args.get('plot1', default='', type=str)
    l2r = request.args.get('plot2', default='', type=str)
    type1 = request.args.get('type1', default=1, type=int)
    type2 = request.args.get('type2', default=1, type=int)
    start = request.args.get('start', default=0, type=int)
    end = request.args.get('end', default=86400, type=int)
    

    #print(start, file=sys.stderr)
    #print(end, file=sys.stderr)

    #Populate the lists into python lists.
    l1 = list()
    l1Sel = dict()
    for i in l1r.split(','):
      if i:
        l1.append(int(i))
        l1Sel[int(i)]=1


    l2 = list()
    l2Sel = dict()
    for i in l2r.split(','):
      if i:
        l2.append(int(i))
        l2Sel[int(i)]=1

  
    seedVals = dict()
    #First, populate the list of type choices.
    ret = query_db('SELECT rowid, chTypeName FROM chanType')
    typeOpts = dict()
    for r in ret:
      typeOpts[r['rowid']] = r['chTypeName']

    seedVals['typeOpts'] = typeOpts

    #Second, populate the list of channels for our two selected types.
    ret = query_db('SELECT rowid, AQname FROM AQchannel WHERE chType = ?', (type1, ))
    ch1Opts = dict()
    for r in ret:
      ch1Opts[r['rowid']] = r['AQname']

    seedVals['ch1Opts'] = ch1Opts

    ret = query_db('SELECT rowid, AQname FROM AQchannel WHERE chType = ?', (type2, ))
    ch2Opts = dict()
    for r in ret:
      ch2Opts[r['rowid']] = r['AQname']

    seedVals['ch2Opts'] = ch2Opts

    #Add the selected channels.
    seedVals['l1Sel'] = l1Sel
    seedVals['l2Sel'] = l2Sel
    seedVals['type1'] = type1
    seedVals['type2'] = type2
      
 
    #Add start/end to seedVals.
    #Need to do the math for day. hour, min, sec
    days = int(start/86400)
    ns = start-days*86400
    hours = int(ns/3600)
    ns = ns-hours*3600
    minutes = int(ns/60)
    seconds = ns-minutes*60
    startT = {'days':days, 'hours':hours, 'minutes':minutes, 'seconds':seconds}

    days = int(end/86400)
    ne = end-days*86400
    hours = int(ne/3600)
    ne = ne-hours*3600
    minutes = int(ne/60)
    seconds = ne-minutes*60
    endT = {'days':days, 'hours':hours, 'minutes':minutes, 'seconds':seconds}

    seedVals['start'] = startT
    seedVals['end'] = endT
    
    #Grab the plotting favorites.
    ret = query_db('SELECT * FROM AQplot')
    favPlots = list()
    if ret is not None:
      for r in ret:
        a = {'rowid':r['rowid'], 'name':r['AQname']}
        favPlots.append(a)

    seedVals['favPlots'] = favPlots

    #Now, command the plotting.
    #Use the host code to pull the DB data that we need.
    if l1 or l2:
      p = dict()
      p['data'], p['xName'], seedVals['timing'] = plotting.chanPlot(l1, l2, start=start+now, end=end+now)
      p['id'] = 0
      p['name'] = 'Custom Plot'
      seedVals['plot'] = {0: p}
    else:
      seedVals['plot'] = None

    #Get the current values.
    if exists('/tmp/aqctrl'):
      with open('/tmp/aqctrl', 'r') as f:
        seedVals['currVals'] = load(f)
    else:
      seedVals['currVals'] = False

    #Get the last ten logged events..
    ret = query_db('SELECT * FROM AQlog ORDER BY logDate DESC LIMIT 10')
    logVals = dict()
    if ret is not None:
      for r in ret:
        dateStr = datetime.fromtimestamp(r['logDate']).strftime('%d %b %Y, %I:%M%p %Z')
        logStr = 'Logged at: ' + dateStr + ' , ' + r['logEntry']
        if r['assocChan']: logStr += ' (Assoc Chan: ' + str(r['assocChan']) + ')'
        if r['assocDev']: logStr += ' (Assoc Dev: ' + str(r['assocDev']) + ')'
        logVals[r['rowid']]={'string':logStr, 'new':not(r['entryRead'])}

    #Also, show all new logged events.
    ret = query_db('SELECT * FROM AQlog WHERE entryRead = 0 ORDER BY logDate DESC')
    newLogs = dict()
    if ret is not None:
      for r in ret:
        if r['rowid'] in logVals:
          continue

        dateStr = datetime.fromtimestamp(r['logDate']).strftime('%d %b %Y, %I:%M%p %Z')
        logStr = 'Logged at: ' + dateStr + ' , ' + r['logEntry']
        if r['assocChan']: logStr += ' (Assoc Chan: ' + str(r['assocChan']) + ')'
        if r['assocDev']: logStr += ' (Assoc Dev: ' + str(r['assocDev']) + ')'
        newLogs[r['rowid']]={'string':logStr, 'new':not(r['entryRead'])}
      
      modify_db('UPDATE AQlog SET entryRead = ? WHERE entryRead = ?', (1, 0), logUpdate=False)

    seedVals['logStr'] = logVals
    seedVals['newLogs'] = newLogs

    return seedVals



def buildFav(i):
  #Function to build up the GET string for a given favorite.
  with app.app_context():
    dbFav = query_db('SELECT * FROM AQplot WHERE rowid=?', (i, ), True)
    dbChan = query_db('SELECT * FROM plotChan WHERE AQplot=?', (i, ))
    plot1str = str()
    plot2str = str()
    c1 = 0
    c2 = 0
    #Get our plot channels.
    for c in dbChan:
      if c['axisNum'] == 1:
        plot1str += str(c['chanNum']) + ','
        c1 = c['chanNum'] #Will use this later to get the type.
      else:
        plot2str += str(c['chanNum']) + ','
        c2 = c['chanNum']

    #Setup the GET string.
    getStr = '?plot1=' + plot1str + '&plot2=' + plot2str
    #Get the left and right types.
    if c1:
      ret = query_db('SELECT chType FROM AQchannel WHERE rowid=?', (c1, ), True)
      getStr += '&type1=' + str(ret['chType'])

    if c2:
      ret = query_db('SELECT chType FROM AQchannel WHERE rowid=?', (c2, ), True)
      getStr += '&type2=' + str(ret['chType'])
    
    #Now, get the start and end times.
    plotStart = dbFav['relStart']
    plotEnd = dbFav['relEnd']

    #Add this start/end to the GET.
    getStr += '&start=' + str(plotStart)
    getStr += '&end=' + str(plotEnd)

    return getStr
