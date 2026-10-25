#Functions to process our Schedules for a device - by source.
import sys
from aqctrl.run.db import query_db, modify_db, update_vals
from aqctrl.aqctrl import app
from flask import request
#from datetime import datetime
from aqctrl.run import devices
from aqctrl.run.plotting import chanPlot
#import aqctrl.model.aqSetup

#For each field that you want to gather:
#(Name for field and for page, db column name, field macro name, (options if applicable))
chanMaps = (('name', 'AQname'), ('rowid','rowid'), ('device','chDevice'))
CPSMaps = (('scale', 'CPSscale'), ('offset', 'CPStoff'), ('rowid','rowid'))
srcMaps = (('name', 'AQname'), ('scale', 'srcScale'), ('rowid','rowid'))
typeMaps = (('name', 'chTypeName'), ('scale', 'chScalingFactor'), ('max', 'chMax'), ('min', 'chMin'))

def processForm(ID):
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()
    #We are only updating CPSes.
    
    CPSids = set()
    for k in request.form.keys():
      if '_'  in k:
        CPSids.add(k.split('_')[1])

    for c in CPSids:
      update_vals(CPSMaps, 'AQCPS', c)

    return errors


def createForm(ID, errors):
  #Set up our page elements to create the form.
  with app.app_context():
    thisChan = query_db('SELECT * FROM AQchannel WHERE rowid=?', (ID, ), True)
    
    if thisChan is None:
      #The query didn't work, redirect.
      return None, None

    thisType = query_db('SELECT * FROM chanType WHERE rowid=?', (thisChan['chType'], ), True)
    theseCPS = query_db('SELECT * FROM AQCPS WHERE CPSchan=? AND CPSprof IS NOT NULL', (ID, ))
    theseSrc = query_db('SELECT * FROM AQsource WHERE rowid IN (SELECT CPSsrc FROM AQCPS WHERE CPSchan=?)', (ID, ))

    seedVals=dict()
    for p in chanMaps:
      seedVals[p[0]]=thisChan[p[1]]
    
    srcOpts=dict()
    typeOpts=dict()

    #Build up our info.
    for p in typeMaps:
      typeOpts[p[0]]=thisType[p[1]]

    for src in theseSrc:
      srcOpts[src['rowid']]=dict()
      srcOpts[src['rowid']]['CPS']=list()
      for p in srcMaps:
        srcOpts[src['rowid']][p[0]]=src[p[1]]

      #Now, seed info for our profiles.
      for CPS in theseCPS:
        if CPS['CPSsrc'] is src['rowid']:
          c=dict()
          for p in CPSMaps:
            c[p[0]]=CPS[p[1]]

          srcOpts[src['rowid']]['CPS'].append(c)


    #Get the device Name.
    thisDev = query_db('SELECT * FROM hostDevice WHERE rowid=?', (thisChan['chDevice'], ), True)
    

    seedVals['devName'] = devices.listOpts()[thisDev['devType']]().name+'_'+str(thisDev['busOrder'])
    seedVals['srcOpts'] = srcOpts
    seedVals['typeOpts'] = typeOpts
    seedVals['plots'] = dict()
    seedVals['plots'][0]={'id':0, 'name':seedVals['name']}
    seedVals['plots'][0]['data'], seedVals['plots'][0]['xName'], s1 = chanPlot(int(ID))

    return seedVals, errors
