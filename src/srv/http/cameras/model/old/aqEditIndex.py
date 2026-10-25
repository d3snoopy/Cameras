#Functions to process our Reactions.
#import sys
from aqctrl.run.db import query_db, modify_db, update_vals, seed_vals
from aqctrl.run.helpers import fToC, cToF
from aqctrl.run.reactions import listBehave
from aqctrl.aqctrl import app
from flask import request

#For each field that you want to gather:
#(Name for field and for page, db column name, field macro name, (options if applicable))
buttonMaps = (('rowid', 'rowid'), ('out', 'outChan'), ('behave', 'behave'), ('duration', 'duration'), ('function', 'AQfunction'), ('scale', 'scale'))


def processForm():
  #Do the processing for the form elements.
  with app.app_context():
    #print(request.form)
    errors=dict()
    #See about adding a new button.
    if 'newButton' in request.form.keys():
      #Need to add a button.
      modify_db('INSERT INTO homeButton DEFAULT VALUES')

    #See about favorite plots being checked, unchecked.
    uncheckFav = list()
    checkFav = list()
    dbFavs = query_db('SELECT rowid FROM AQplot')
    if dbFavs is not None:
      for f in dbFavs:
        if 'fav_'+str(f['rowid']) in request.form:
          checkFav.append(f['rowid'])
        else:
          uncheckFav.append(f['rowid'])

    #Now, update the DB to reflect the checks.
    s2 = '?, '
    s3 = ')'
    if uncheckFav:
      s1 = 'UPDATE AQplot SET onHome=0 WHERE rowid IN ('
      modify_db(s1 + (s2*len(uncheckFav))[:-2] + s3, uncheckFav, logUpdate=False)

    if checkFav:
      s1 = 'UPDATE AQplot SET onHome=1 WHERE rowid IN ('
      modify_db(s1 + (s2*len(checkFav))[:-2] + s3, checkFav, logUpdate=False)

    #Similar idea, with the channels.
    uncheckChan = list()
    checkChan = list()
    dbChan = query_db('SELECT rowid FROM AQchannel')
    if dbChan is not None:
      for c in dbChan:
        if 'chan_'+str(c['rowid']) in request.form:
          checkChan.append(c['rowid'])
        else:
          uncheckChan.append(c['rowid'])

    #Now, update the DB to reflect the checks.
    s2 = '?, '
    s3 = ')'
    if uncheckChan:
      s1 = 'DELETE FROM homeChan WHERE rowid IN ('
      modify_db(s1 + (s2*len(uncheckChan))[:-2] + s3, uncheckChan, logUpdate=False)

    if checkChan:
      s1 = 'INSERT INTO homeChan (chanNum) VALUES '
      s2 = '(?), '
      modify_db(s1 + (s2*len(checkChan))[:-2], checkChan, logUpdate=False)

    #Need to handle the button values.
    dbBChan = query_db('SELECT rowid FROM buttonChan') #In theory every form will contain every one
    if dbBChan is not None:
      for b in dbBChan:
        update_vals(buttonMaps, 'buttonChan', b['rowid'])

    for k, v in request.form.items():
      if 'delete' in k:
        myQuery = 'DELETE FROM buttonChan WHERE rowid = ?'
        myVal = (k.split('_')[1], )
        modify_db(myQuery, myVal, logUpdate=False)

      if 'delButton' in k:
        myQuery = 'DELETE FROM homeButton WHERE rowid = ?'
        myVal = (k.split('_')[1], )
        modify_db(myQuery, myVal, logUpdate=False)

      if 'name' in k:
        myQuery = 'UPDATE homeButton SET AQname=? WHERE rowid = ?'
        myVal = k.split('_')[1]
        modify_db(myQuery, (v, myVal), logUpdate=False)

      if 'newOut' in k:
        myQuery = 'INSERT INTO buttonChan (homeButton) VALUES (?)'
        myVal = (k.split('_')[1], )
        modify_db(myQuery, myVal, logUpdate=False)
        
    return errors


# modify_db('INSERT INTO homeButton (reactGrp) VALUES (?)', (ID, ))

    for k in request.form:
      if 'type' in k:
        foundRct.add(k.split('_')[1])

    #print(request.form)
    for i in foundRct:
      update_vals(reactMaps, 'AQreaction', i, reactCheck)

      #Need to adjust F to C if host units are F.
      dbHost = query_db('SELECT tempUnits FROM AQhost', one=True)
      thisCh = 'trigChan_'+str(i)
      if dbHost['tempUnits'] and thisCh in request.form:
        dbChan = query_db('SELECT typeTemp FROM chanType WHERE rowid IN (SELECT chType FROM AQchannel WHERE rowid=?)', (request.form[thisCh], ), True)
        s = 'trigVal_'+str(i)
        if dbChan is not None and dbChan['typeTemp'] and s in request.form:
          modify_db('UPDATE AQreaction SET triggerValue=? WHERE rowid=?', (fToC(float(request.form[s])), i))

    return errors


def createForm(errors):
  #Set up our page elements to create the form.
  with app.app_context():
    #First, set up the favorites.
    favList = list()
    dbFav = query_db('SELECT * FROM AQplot')
    if dbFav is not None:
      for p in dbFav:
        favList.append({'rowid':p['rowid'], 'name':p['AQname'], 'onHome':p['onHome']})

    seedVals = dict()
    seedVals['favList'] = favList

    #Next, our channels.
    chList = list()
    outChans = dict()
    homeList = list()
    dbChan = query_db('SELECT * FROM AQchannel LEFT JOIN chanType ON chanType.rowid = AQchannel.chType WHERE AQchannel.chActive=1')
    dbHomeChan = query_db('SELECT * FROM homeChan')
    if dbHomeChan is not None:
      for h in dbHomeChan:
        homeList.append(h['chanNum'])

    if dbChan is not None:
      for c in dbChan:
        onHome = (c['rowid'] in homeList)
        thisC = {'rowid':c['rowid'], 'name':c['AQname'], 'onHome':onHome, 'out':c['chOutput']}
        chList.append(thisC)
        if c['chOutput']:
          outChans[c['rowid']]=c['AQname']

    seedVals['chList'] = chList
    seedVals['outChans'] = outChans

    #Finally, handle our buttons.
    bList = list()
    dbB = query_db('SELECT * FROM homeButton')
    dbBCH = query_db('SELECT * FROM buttonChan')

    buttons = dict()
    if dbB is not None:
      for b in dbB:
        buttons[b['rowid']] = {'rowid':b['rowid'], 'name':b['AQname'], 'outCh':list()}


    if dbBCH is not None:
      for b in dbBCH:
        a = dict()
        for p in buttonMaps:
          a[p[0]]=b[p[1]]

        buttons[b['homeButton']]['outCh'].append(a)
        
    seedVals['buttons'] = buttons

    #Map our behavior options.
    behaveOpts=dict()
    for i, v in enumerate(listBehave()):
      behaveOpts[i]=v

    seedVals['behaveOpts']=behaveOpts

    #Map our output function options.
    functDB = query_db('SELECT * FROM AQfunction')

    #If no functions exist, run the seed functions function.
    count = 0
    for f in functDB:
      count += 1

    if not count:
      #Need to seed our functions.
      from aqctrl.model.SchedList import seedInitialFunctions
      seedInitialFunctions()
      functDB = query_db('SELECT * FROM AQfunction')

    functOpts=dict()
    for f in functDB:
      functOpts[f['rowid']]=f['AQname']
    
    seedVals['functOpts']=functOpts

    #print(seedVals)
    return seedVals, errors
