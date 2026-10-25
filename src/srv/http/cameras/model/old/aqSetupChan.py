#Functions to process our Channels for a device.
#import sys
from aqctrl.run.db import query_db, modify_db, update_vals
from aqctrl.aqctrl import app
from flask import request
from aqctrl.run import devices

#For each field that you want to gather:
#(Name for field and for page, db column name, field macro name, (options if applicable))
dbTypesMaps = (('name', 'AQname'), ('color', 'chColor'), ('type', 'chType'), ('rowid', 'rowid'))
checkBoxMaps = (('active', 'chActive'), )

def processForm(devID):
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()
    
    devChans = query_db('SELECT rowid, * FROM AQchannel WHERE chDevice=?', (devID, ))
    if not devChans:
      return None

    devChans, Null = checkThisDev(devChans, devID)

    #Update our existing channels.
    #Iterate over each channel and try to update.
    for c in devChans:
      update_vals(dbTypesMaps, 'AQchannel', c['rowid'], checkBoxMaps)          

    return errors


def createForm(devID, errors):
  #Set up our page elements to create the form.
  with app.app_context():
    devChans = query_db('SELECT rowid, * FROM AQchannel WHERE chDevice=?', (devID, ))
    ###print(devChans, file=sys.stderr)
    if not devChans:
      return None, None

    devChans, thisDevIn = checkThisDev(devChans, devID)

    #Build our type options.
    typeOpts = query_db('SELECT rowid, * FROM chanType WHERE chInput=?', (int(thisDevIn), ))
    types = dict()
    for t in typeOpts:
      types[t['rowid']] = t['chTypeName']

    chanVals=list()

    #Seed our values for existing types.
    for c in devChans:
      ct=dict()
      for p in dbTypesMaps:
        ct[p[0]]=c[p[1]]
      for p in checkBoxMaps:
        ct[p[0]]=c[p[1]]
      chanVals.append(ct)

    seedVals=dict()
    seedVals['chanVals'] = chanVals
    seedVals['types'] = types
    seedVals['devID'] = devID
    return seedVals, errors


def checkThisDev(devChans, devID):
  with app.app_context():
    thisDevdb = query_db('SELECT * FROM hostDevice WHERE rowid=?', (devID, ), True)
    thisDev = devices.listOpts()[thisDevdb['devType']]()
    thisDevIn = thisDev.inDev

    devChans = query_db('SELECT rowid, * FROM AQchannel WHERE chDevice=?', (devID, ))

    return devChans, thisDevIn
