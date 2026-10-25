#Functions to process our Channel Types page.
#import sys
from aqctrl.run.db import query_db, modify_db, update_vals, seed_vals
from aqctrl.aqctrl import app
from flask import request
from os.path import exists
from aqctrl.run.plotting import fnPlot
#import aqctrl.run.devices as devices

#For each field that you want to gather:
functDbTypesMaps = (('name', 'AQname'), )
pointDbTypesMaps = (('value','ptValue'), ('percent','timePct'), ('offset','timeOffset'), ('align','timeSE'))


def processForm(functID):
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()
    #print(request.form, file=sys.stderr)
    #Test for the delete button.
    for k in request.form:
      if 'delete' in k:
        myQuery = 'DELETE FROM FnPoint WHERE rowid = ?'
        myVal = (k.split('_')[1], )
        modify_db(myQuery, myVal)
        return errors
      
    #Test for the new button.
    if 'new' in request.form:
      #We need to create a new entry.
      myQuery = 'INSERT INTO FnPoint (parentFn) VALUES (?)'
      modify_db(myQuery, (functID, ))
    else:
      #Upate values selected.
      myQuery = 'SELECT rowid FROM FnPoint WHERE parentFn=?'
      myPoints = query_db(myQuery, (functID, ))

      #Update the Function.
      update_vals(functDbTypesMaps, 'AQfunction', functID)

      #Iterate over each fnPoint and try to update.
      #print(request.form, file=sys.stderr)
      for p in myPoints:
        update_vals(pointDbTypesMaps, 'FnPoint', p['rowid'])

      #Update the plot for this function.
      #from aqctrl.run.plotting import fnPlot
      #fnPlot(functID)

    return errors


def createForm(functID, errors):
  #Set up our page elements to create the form.
  with app.app_context():
    thisFunct=query_db('SELECT rowid, * FROM AQfunction WHERE rowid=?', (functID, ))
    functPoints=query_db('SELECT rowid, * FROM FnPoint WHERE parentFn=?', (functID, ))

    seedVals=dict()
    pts=list()

    #Seed our values for existing points.
    seedVals = seed_vals(functDbTypesMaps, thisFunct, True)
    seedVals['points'] = seed_vals(pointDbTypesMaps, functPoints)
   
    #Plotting for the function.
    seedVals['plot'] = {0: {'id':0, 'name':seedVals['name'], 'data':{0:[{'color':'#FFFFFF', 'name':seedVals['name'], 'units':'%', 'data':fnPlot(functID)}]}, 'xName':'units'}}
    #print(seedVals['plot'])
    #fName = 'function'+str(functID)+'.png'
    #fStr = './aqctrl'+app.url_for('static', filename=fName)
    #print(fStr)
    #if exists(fStr):
      #print('file found!')
      #seedVals['imgName']=fName

    return seedVals, errors
