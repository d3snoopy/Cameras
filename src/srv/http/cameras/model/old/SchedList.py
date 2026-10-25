#Functions to process our Schedules for a device - base page.
#import sys
from aqctrl.run.db import query_db, modify_db
from aqctrl.aqctrl import app
from flask import request
#from os.path import exists

nMap = {'AQfunction': 'function', 'AQsource': 'source', 'AQchannel': 'channel', 'AQreactGrp': 'reactGrp'}

def processForm(listType):
  #Do the processing for the form elements.
  with app.app_context():
    errors=dict()
    
    #Two potential options: add a new function, or delete a function.
    for k in request.form:
      if 'delete' in k:
        myQuery = 'DELETE FROM '+listType+' WHERE rowid = ?'
        myVal = (k.split('_')[1], )
        modify_db(myQuery, myVal)
        return errors

    if 'new' in request.form:
      myQuery = 'INSERT INTO '+listType+' DEFAULT VALUES'
      modify_db(myQuery)

    return errors


def createForm(listType, errors, Qryflt=''):
  #Set up our page elements to create the form.
  with app.app_context():
    #Build our options.
    queryStr='SELECT * FROM '+listType

    #Add filter, if applicable.
    if Qryflt:
      queryStr+=Qryflt

    listOpts = query_db(queryStr)

    if not listOpts:
      #We don't have any of this type in our db, seed an initial set, if we're listing functions.
      if listType == 'AQfunction':
        seedInitialFunctions()
        #Re-query to get our newly created functions.
        listOpts = query_db('SELECT rowid, * FROM AQfunction')

    listInfo = list()
    for l in listOpts:
      thisOpt = dict()
      #Figure out if we have a plot ready.
      #if listType == 'AQchannel':
      #  #Update all of the plots.
      #  from aqctrl.run.plotting import chanPlot
      #  chanPlot(int(l['rowid']), imgName='channel'+str(l['rowid'])+'.png')
       
      #fName = nMap[listType]+str(l['rowid'])+'.png'
      #fStr = './aqctrl'+app.url_for('static', filename=fName)
      #if exists(fStr):
      #  thisOpt['plot'] = fName
      #else:
      thisOpt['plot'] = False

      thisOpt['name'] = l['AQname']
      thisOpt['rowid'] = l['rowid']
      listInfo.append(thisOpt) 

    seedVals=dict()
    seedVals['listInfo'] = listInfo
    return seedVals, errors


def seedInitialFunctions():
  #Function to create an initial set of functions for use.
  with app.app_context():
    #Values that we have to seed.
    seedKeys = ('ptValue', 'timePct', 'timeOffset', 'timeSE')
    defVals = 0
    seedList = (('Square', (
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':1, 'timePct':0, 'timeOffset':0.01, 'timeSE':0},
      {'ptValue':1, 'timePct':0, 'timeOffset':-0.01, 'timeSE':1},
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      )),('Inverse Square', (
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':0, 'timePct':0, 'timeOffset':0.01, 'timeSE':0},
      {'ptValue':0, 'timePct':0, 'timeOffset':-0.01, 'timeSE':1},
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      )),('Triangle', (
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':1, 'timePct':50, 'timeOffset':0, 'timeSE':0},
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      )),('Inverse Triangle', (
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':0, 'timePct':50, 'timeOffset':0, 'timeSE':0},
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      )),('Rising Slope', (
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      )),('Falling Slope', (
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      )),('Solar Motion', (
      {'ptValue':0, 'timePct':0, 'timeOffset':-2400, 'timeSE':0},
      {'ptValue':0.03, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      {'ptValue':0.18, 'timePct':0, 'timeOffset':1, 'timeSE':0},
      {'ptValue':1, 'timePct':0, 'timeOffset':7200, 'timeSE':0},
      {'ptValue':1, 'timePct':0, 'timeOffset':-7200, 'timeSE':1},
      {'ptValue':0.18, 'timePct':0, 'timeOffset':-1, 'timeSE':1},
      {'ptValue':0.03, 'timePct':0, 'timeOffset':0, 'timeSE':1},
      {'ptValue':0, 'timePct':0, 'timeOffset':2400, 'timeSE':1},
      )),('On', (
      {'ptValue':1, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      )),('Off', (
      {'ptValue':0, 'timePct':0, 'timeOffset':0, 'timeSE':0},
      )))


    ptQuery = 'INSERT INTO FnPoint ('
    for k in seedKeys:
      ptQuery+=k+', '

    ptQuery+='parentFn) VALUES ('
    ptVals = list()

    for s in seedList:
      #print(s[0], file=sys.stderr)
      fnQuery = 'INSERT INTO AQfunction (aqName) VALUES (?)'
      modify_db(fnQuery, (s[0], ))
      # There's probably a way to avoid this extra query?? TODO
      fnID = query_db('SELECT rowid FROM AQfunction WHERE aqName=?', (s[0], ), True)['rowid']
      for p in s[1]:
        for k in seedKeys:
          ptQuery+='?, '
          if k in p.keys():
            ptVals.append(p[k])
          else:
            ptVals.append(defVals)

        ptQuery+='?), ('
        ptVals.append(fnID)


    ptQuery=ptQuery[:-3]
    #print(ptQuery, file=sys.stderr)
    #print(ptVals, file=sys.stderr)
    modify_db(ptQuery, ptVals)

    #from aqctrl.run.plotting import fnPlot
    #fnPlot()

    return

