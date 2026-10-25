#Functions to process our Reactions.
#import sys
from aqctrl.run.db import query_db, modify_db, update_vals, seed_vals
from aqctrl.run.helpers import fToC, cToF
from aqctrl.aqctrl import app
from flask import request
#from datetime import datetime
from aqctrl.run import reactions
#import aqctrl.model.aqSetup

#For each field that you want to gather:
#(Name for field and for page, db column name, field macro name, (options if applicable))
#chanMaps = (('name', 'AQname'), ('rowid','rowid'))
reactMaps = (('type', 'criteriaType'), ('trigVal', 'triggerValue'), ('trigChan', 'monChan'), ('scale', 'rctScale'), ('offset', 'rctOffset'), ('duration', 'rctDuration'), ('function', 'rctFunct'))
reactCheck = (('expire', 'willExpire'), )
grpMaps = (('name', 'AQname'), ('chan', 'outChan'), ('behave', 'grpBehave'), ('detect', 'grpDetect'))
chTypeOpts = (('scale', 'chScalingFactor'), ('max', 'chMax'), ('min', 'chMin'), ('name', 'chTypeName'))
profMaps = (('function', 'parentFunction'), )

def processForm(ID):
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()
    
    #print(request.form, file=sys.stderr)
    
    if 'add' in request.form.keys():
      #Need to create a reaction.
      modify_db('INSERT INTO AQreaction (reactGrp) VALUES (?)', (ID, ))
      # p = query_db('SELECT last_insert_rowid()', one=True)['last_insert_rowid()']

    update_vals(grpMaps, 'AQreactGrp', ID, appendRow=False)

    foundRct = set()
    for k in request.form:
      if 'delete' in k:
        myQuery = 'DELETE FROM AQreaction WHERE rowid = ?'
        myVal = (k.split('_')[1], )
        modify_db(myQuery, myVal)
        return errors

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


def createForm(ID, errors):
  #Set up our page elements to create the form.
  with app.app_context():
    thisGrp = query_db('SELECT * FROM AQreactGrp WHERE rowid=?', (ID, ))
    
    if thisGrp is None:
      #The query didn't work, redirect.
      return None, None

    theseReact = query_db('SELECT * FROM AQreaction WHERE reactGrp=?', (ID, ))
 
    #Map our info
    seedVals=seed_vals(grpMaps, thisGrp, True)
    seedVals['reactions']=seed_vals(reactMaps + reactCheck, theseReact)

    #If temp units are faranheit, need to adjust values as applicable.
    dbHost = query_db('SELECT tempUnits FROM AQhost', one=True)
    if dbHost['tempUnits']:
      for i, r in enumerate(seedVals['reactions']):
        dbChan = query_db('SELECT typeTemp FROM chanType WHERE rowid IN (SELECT chType FROM AQchannel WHERE rowid=?)', (r['trigChan'], ), True)
        if dbChan is not None and dbChan['typeTemp']:
          t= seedVals['reactions'][i]['trigVal']
          seedVals['reactions'][i]['trigVal'] = cToF(t)

    #Map our type options.
    typeOpts=dict()
    for i, v in enumerate(reactions.listTypes()):
      typeOpts[i]=v().get('name')

    #Map our detection options.
    detectOpts=dict()
    for i, v in enumerate(reactions.listDetect()):
      detectOpts[i]=v
    seedVals['detectOpts']=detectOpts 

    #Map Chan Type Info
    thisChType = query_db('SELECT * FROM chanType WHERE rowid=(SELECT chType FROM AQchannel WHERE rowid=?)', (thisGrp[0]['outChan'], ))
    if thisChType:
      seedVals['chTypeOpts']=seed_vals(chTypeOpts, thisChType, True)
    else:
      seedVals['chTypeOpts']={'name':None, 'scale':None, 'max':None, 'min':None}

    seedVals['typeOpts']=typeOpts
    #Map our behavior options.
    behaveOpts=dict()
    for i, v in enumerate(reactions.listBehave()):
      behaveOpts[i]=v

    seedVals['behaveOpts']=behaveOpts

    #Map our monitor channel options.
    chanDB = query_db('SELECT * FROM AQchannel INNER JOIN chanType ON chanType.rowid = AQchannel.chType WHERE chActive = 1')
    inChans=dict()
    outChans=dict()

    for c in chanDB:
      #for i in c.keys():
      #  print(str(i) + ': ' + str(c[i]), file=sys.stderr)
      if c['chInput']:
        inChans[c['rowid']]=c['AQname']

      if c['chOutput']:
        outChans[c['rowid']]=c['AQname']

    seedVals['inChans']=inChans
    seedVals['outChans']=outChans

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

    return seedVals, errors
