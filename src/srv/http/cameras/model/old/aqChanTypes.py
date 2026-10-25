#Functions to process our Channel Types page.
#import sys
from aqctrl.run.db import query_db
from aqctrl.run.db import modify_db
from aqctrl.run.db import update_vals
from aqctrl.aqctrl import app
from flask import request
#import aqctrl.run.devices as devices

#For each field that you want to gather:
#(Name for field and for page, db column name, field macro name, (options if applicable))
dbTypesMaps = (('name', 'chTypeName'), ('variable', 'chVariable'), ('max', 'chMax'), ('min', 'chMin'), ('initialVal', 'chInitialVal'), ('scale', 'chScalingFactor'), ('units', 'chUnits'))
checkBoxMaps = (('control', 'chLevelCtl'), ('temp', 'typeTemp'), ('input', 'chInput'), ('output', 'chOutput'), ('invert', 'chInvert'), ('hideInvert', 'hideInvert'))


def processForm():
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()

    #Test for the delete button.
    for k in request.form:
      if 'delete' in k:
        Q1 = 'UPDATE AQchannel SET chType = NULL WHERE chType=?'
        myQuery = 'DELETE FROM chanType WHERE rowid = ?'
        myVal = (k.split('_')[1])
        modify_db(Q1, myVal)
        modify_db(myQuery, myVal)
        return errors
      
    #Test for the new button.
    if 'new' in request.form:
      #We need to create a new entry.
      myQuery = 'INSERT INTO chanType DEFAULT VALUES'
      modify_db(myQuery)
    else:
      #Upate values selected.
      myQuery = 'SELECT rowid FROM chanType'
      myTypes = query_db(myQuery)

      #Iterate over each chanType and try to update.
      for t in myTypes:
        update_vals(dbTypesMaps, 'chanType', t['rowid'], checkBoxMaps)

    return errors


def createForm(errors):
  #Set up our page elements to create the form.
  with app.app_context():
    chanTypes=query_db('SELECT rowid, * FROM chanType')

    seedVals=dict()
    cts=list()

    #Seed our values for existing types.
    for c in chanTypes:
      ct=dict()
      ct['rowid'] = c['rowid']
      for p in dbTypesMaps:
        ct[p[0]]=c[p[1]]
      for p in checkBoxMaps:
        ct[p[0]]=c[p[1]]

      #Decide about if controls should be disabled.
      ct['varCtls'] = not(ct['variable'] and ct['control'])
      ct['disCtls'] = not(ct['control'])
      cts.append(ct)

    seedVals['chanTypes'] = cts
    return seedVals, errors
