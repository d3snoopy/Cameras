#Functions to process our Schedules for a device - by source.
#import sys
from aqctrl.run.db import query_db, modify_db, update_vals
from aqctrl.aqctrl import app
from flask import request
from datetime import datetime, timedelta, UTC
#from os.path import exists
from aqctrl.run.plotting import srcPlot
#import aqctrl.run.devices as devices
#import aqctrl.model.aqSetup

#For each field that you want to gather:
#(Name for field and for page, db column name, field macro name, (options if applicable))
dbTypesMaps = (('name', 'AQname'), ('scale', 'srcScale'), ('type', 'chType'), ('rowid', 'rowid'))
CPSvalMaps = (('scale', 'CPSscale'), ('offset', 'CPStoff'), ('rowid','rowid'))
ProfvalMaps = (('rowid', 'rowid', False), ('start', 'profStart', 'now'), ('end', 'profEnd', 'now'), ('refresh', 'profRefresh', '24hr'), ('function','parentFunction', False))

def processForm(srcID):
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()
    #We are updating a particular source.

    #Test to see if we have a chType change; if so, we need to remove all channels used associations.
    newchtype = False
    thisSrc = query_db('SELECT chType FROM AQsource WHERE rowid=?', (srcID, ), True)
    #print(type(thisSrc['chType']), file=sys.stderr)
    #print(type(request.form['type_'+str(srcID)]), file=sys.stderr)
    #print((thisSrc['chType'] is not request.form['type_'+str(srcID)]), file=sys.stderr)
    if 'type_'+str(srcID) in request.form.keys() and thisSrc['chType'] is not int(request.form['type_'+str(srcID)]):
      #print('Type change', file=sys.stderr)
      #The type changed, need to delete all of our channel associations.
      modify_db('DELETE FROM AQCPS WHERE CPSsrc = ?', (srcID, ))
      newchtype = True

    #Update our existing channels.
    update_vals(dbTypesMaps, 'AQsource', srcID)

    #If we had a new chan type, we're done.
    if newchtype: return errors

    #No new channel type; there's more to update/process.
    #Move through updating channels and profiles.
    myCPS = query_db('SELECT * FROM AQCPS WHERE CPSsrc=?', (srcID, ))
    #Seed our db info about chan, profile mappings.
    dbCPS = dict()
    # keys will be channel IDs, with a dict as the value
    # inner keys are profile IDs, with a tuple with the CPSscale and CPStoff
    for i in myCPS:
      c = i['CPSchan']
      p = i['CPSprof']
      if c not in dbCPS.keys(): dbCPS[c]=dict()
      dbCPS[c][p] = (i['CPSscale'], i['CPStoff'])

    foundChan = set()
    foundProf = set()
    foundCPS = set()
    st = dict() #outer: profID: {year: , month:, etc}
    et = dict() #outer: profID: {year: , month:, etc}
    rt = dict() #outer: profID: {year: , month:, etc}
    profVals = dict() #outer: profID:[pairs]
    CPSmap = dict() #outer: CPSID:[pairs]
    for k in request.form:
      v = request.form[k]
      n=k.split('_')
      if 'chan' in k:
        #Move through our channels used options.
        #Name: chan_[AQchannel rowid]
        chID = int(n[1])
        foundChan.add(chID)
        #Want to be able to use checkboxes, so need to populate expectations and existing, then compare
        #If new: add a set to CPS, including a C_S where P is null
        if chID not in dbCPS.keys():
          modify_db('INSERT INTO AQCPS (CPSchan, CPSsrc) VALUES (?, ?)', (chID, srcID))
        #If removed: delete all CPS with this C
      
      elif 'prof' in k:
        #Move through our profiles.
        #First, parse info for the profile itself.
        pID=int(n[1])
        foundProf.add(pID)
        if pID not in profVals:
          profVals[pID]=list()
          st[pID]=dict()
          et[pID]=dict()
          rt[pID]=dict()

        match(n[2]):
          case 'start':
            st[pID][n[3]]=v

          case 'end':
            et[pID][n[3]]=v

          case 'refresh':
            rt[pID][n[3]]=v
    
          case 'function':
            profVals[pID].append((v, 'parentFunction'))

      elif 'CPS' in k:
        #This ia some CPS data.
        foundCPS.add(n[1])
        if n[1] not in CPSmap: CPSmap[n[1]]=list()
        match(n[2]):
          case 'scale':
            CPSmap[n[1]].append((k, 'CPSscale'))

          case 'offset':
            CPSmap[n[1]].append((k, 'CPStoff'))

      elif 'delP' in k:
        i = int(k.split('_')[1])
        modify_db('DELETE FROM AQprofile WHERE rowid=?', (i, ))


    #Set up our start, end, refresh strings for the DB.
    #print(st, file=sys.stderr)
    for p in foundProf:
      dVals = list()
      thisNames = ['profStart', 'profEnd', 'profRefresh']
      for i, a in enumerate([st, et, rt]):
        #Process.
        if i <2:
          #This is a start or an end - create timedate object, then output timestamp
          s = str()
          for e in ['year', 'month', 'day', 'hour', 'min', 'sec']:
            s += str(a[p][e]) + ', '

          tzOff = datetime.now().astimezone().strftime('%z')
          s += tzOff
          try:
            thisDate = datetime.strptime(s, '%Y, %m, %d, %H, %M, %S, %z')
          except ValueError:
            thisDate = datetime.now(UTC)

          profVals[p].append((thisDate.timestamp(), thisNames[i]))
        else:
          #This is the refresh - create a timedelta object, then output number of seconds delta
          try:
            thisDelta = timedelta(days=int(a[p]['day']), hours=int(a[p]['hour']),
              minutes=int(a[p]['min']), seconds=int(a[p]['sec']))
          except ValueError:
            thisDelta = timedelta(days=1)

          profVals[p].append((thisDelta.total_seconds(), thisNames[i]))


      #profVals[p].append((str(st[p]['year'])+', '+str(st[p]['month'])+', '+str(st[p]['day'])+
      #  ', '+str(st[p]['hour'])+', '+str(st[p]['min'])+', '+str(st[p]['sec']),'profStart'))
      #profVals[p].append((str(et[p]['year'])+', '+str(et[p]['month'])+', '+str(et[p]['day'])+
      #  ', '+str(et[p]['hour'])+', '+str(et[p]['min'])+', '+str(et[p]['sec']),'profEnd'))
      #profVals[p].append((str(rt[p]['year'])+', '+str(rt[p]['month'])+', '+str(rt[p]['day'])+
      #  ', '+str(rt[p]['hour'])+', '+str(rt[p]['min'])+', '+str(rt[p]['sec']),'profRefresh'))

    #Do the update on the maps we created. (profMap and CPSMap)
    #print(profVals, file=sys.stderr)
    for p, v in profVals.items():
      query_str='UPDATE AQprofile SET '
      queryvals = list()
      for pair in v:
        query_str+=pair[1]+'=?, '
        queryvals.append(pair[0])

      query_str = query_str[:-2]
      query_str += ' WHERE rowid=?'
      queryvals.append(p)

      modify_db(query_str, queryvals)

    for c, v in CPSmap.items():
      update_vals(v, 'AQCPS', c, appendRow=False)

    #Add CPS based on checkbox changes.
    for p in foundProf:
      for c in foundChan:
        if 'newC_'+str(p)+'_'+str(c) in request.form:
          modify_db('INSERT INTO AQCPS (CPSchan, CPSprof, CPSsrc) VALUES (?, ?, ?)', (c, p, srcID))

    for c in foundCPS:
      if 'CPS_'+str(c)+'_selected' not in request.form:
        modify_db('DELETE FROM AQCPS WHERE rowid=?', (c, ))

    #Delete all of the CPS for this src if the checkbox for a channel not found.
    #print(foundChan, file=sys.stderr)
    for c in dbCPS.keys():
      if c not in foundChan:
        modify_db('DELETE FROM AQCPS WHERE CPSchan=? AND CPSsrc=?', (c, srcID))


    #Test about adding a profile.
    if 'newP' in request.form:
      #Add the profile.
      modify_db('INSERT INTO AQprofile (parentSource) VALUES (?)', (srcID, ))
      p = query_db('SELECT last_insert_rowid()', one=True)['last_insert_rowid()']

      #Now, insert CPS for this profile & the selected channels.
      if foundChan:
        query_str = 'INSERT INTO AQCPS (CPSsrc, CPSprof, CPSchan) VALUES'
        query_vals = list()
        for c in foundChan:
          query_str+=' (?, ?, ?),'
          query_vals.extend([srcID, p, c])

        query_str=query_str[:-1]
        modify_db(query_str, query_vals)

    #Plot this source.
    #from aqctrl.run.plotting import srcPlot
    #print('plotting source' + str(srcID))
    #srcPlot(srcID)

    return errors


def createForm(srcID, errors):
  #Set up our page elements to create the form.
  with app.app_context():
    thisSrc = query_db('SELECT rowid, * FROM AQsource WHERE rowid=?', (srcID, ), True)
    
    if thisSrc is None:
      #The query didn't work, redirect to our general page.
      return None, None

    seedVals=dict()
    for p in dbTypesMaps:
      seedVals[p[0]]=thisSrc[p[1]]
    
    typeOpts=dict()
    #Build our type options.
    typeDB = query_db('SELECT * FROM chanType WHERE chOutput=?', (1, ))
    for t in typeDB:
      typeOpts[t['rowid']]=t['chTypeName']

    #Build our channel data.
    CPSDB = query_db('SELECT rowid, * FROM AQCPS WHERE CPSsrc=? ORDER BY CPSprof, CPSchan', (srcID, ))
    chanDB = query_db('SELECT * FROM AQchannel WHERE chType=?', (thisSrc['chType'], ))
    profDB = query_db('SELECT * FROM AQprofile WHERE parentSource=?', (srcID, ))
    functDB = query_db('SELECT * FROM AQfunction')

    #If no functions exist, run the seed functions function.
    count = 0
    for f in functDB:
      count += 1

    if not count:
      #Need to seed our functions.
      import aqctrl.model.SchedList
      aqctrl.model.SchedList.seedInitialFunctions()
      functDB = query_db('SELECT * FROM AQfunction')

    #Set up all of the profile data.
    selChans = set()
    profData = dict()

    for p in profDB:
      i=p['rowid']
      if i not in profData:
        profData[i] = dict()
        for a in ProfvalMaps:
          if not a[2]:
            profData[i][a[0]]=p[a[1]]
          else:
            #This is a date instance
            if p[a[1]]:
              if a[2] == 'now':
                #We are getting a timestamp from the db.
                td = datetime.fromtimestamp(p[a[1]], datetime.now().astimezone().tzinfo)
                profData[i][a[0]]=td.strftime('%Y, %m, %d, %H, %M, %S').split(', ')
              else:
                #We are getting a number of seconds offset from the db.
                td = p[a[1]]
                tdays = int(td/86400)
                rem = td%86400
                thrs = int(rem/3600)
                rem = rem%3600
                tmin = int(rem/60)
                tsec = rem%60
                profData[i][a[0]]=[0, 0, tdays, thrs, tmin, tsec]
            else:
              if a[2] == 'now':
                now=datetime.now()
                profData[i][a[0]]=now.strftime('%Y, %m, %d, %H, %M, %S').split(', ')
              else:
                profData[i][a[0]]=[0, 0, 0, 24, 0, 0]
        
        #fName = 'function'+str(p['parentFunction'])+'.png'
        #fStr = './aqctrl'+app.url_for('static', filename=fName)
        #if exists(fStr): profData[i]['image']='function'+str(p['parentFunction'])+'.png'
        profData[i]['chans']=dict()

    for a in CPSDB:
      #Add to a set of the selected channels.
      selChans.add(a['CPSchan'])

      #Populate the profile stuff.
      Pid = a['CPSprof']
      if not Pid:
        continue #This is a CPS just to mark that we want to use this channel and not linked to a profile.
      thisChan=dict()
      for i in CPSvalMaps:
        thisChan[i[0]]=a[i[1]]

      profData[Pid]['chans'][a['CPSchan']] = thisChan
 
    chanOpts=dict()
    for c in chanDB:
      chanOpts[c['rowid']]={'name':c['AQname'],'id':c['rowid'],'selected':c['rowid'] in selChans, 'active':c['chActive']}

    functOpts=dict()
    for f in functDB:
      functOpts[f['rowid']]=f['AQname']
    

    seedVals['typeOpts'] = typeOpts
    seedVals['chanOpts'] = chanOpts
    seedVals['profData'] = profData
    seedVals['selChans'] = selChans
    seedVals['functOpts'] = functOpts

    #Plotting for the source.
    #fName = 'source'+str(srcID)+'.png'
    #fStr = './aqctrl'+app.url_for('static', filename=fName)
    #if exists(fStr):
    #  seedVals['imgName']=fName
    seedVals['plots'] = dict()
    seedVals['plots'][0]={'id':0, 'name':seedVals['name']}
    seedVals['plots'][0]['data'], seedVals['plots'][0]['xName'], s1 = srcPlot(srcID)


    return seedVals, errors
