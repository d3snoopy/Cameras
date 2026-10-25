#Functions to process our Setup page.
#import sys
from aqctrl.run.db import query_db, modify_db
from aqctrl.aqctrl import app
from flask import request
from aqctrl.run import devices, busses, logging

valList = ('readInt', 'writeInt', 'checkInt', 'tempUnits', 'writeLog', 'readLog', 'reactLog', 'hostKey') #Note: 'hostKey' needs to be the last item.
dbTypesMaps = (('number', 'busOrder'),('type','devType'),('scale','scaleFactor'),
  ('max','maxVal'),('min','minVal'),('inv','invert'),('addr','busAddr'),('rowid','rowid'))
tempOpts = {'0':'°C', '1':'°F'}

def processForm():
  #Do the processing for the form elements.
  with app.app_context():
    #print(request.form, file=sys.stderr)
    errors=dict()
    newList = valList
    #Check our host key. Enforce alphanumeric and a maximum of 64 characters.
    if not request.form['hostKey'].isalnum() or len(request.form['hostKey'])>64:
      #We don't like the key input provided.
      errors['hostKey'] = 'Key must be alphanumeric and not more than 64 characters'
      newList = valList[:-1]

    newVals=tuple()
    query_str='UPDATE AQhost SET '
    for i in newList:
      newVals += (request.form[i], )
      query_str += i + '=?, '

    query_str = query_str[:-2]
    query_str += ' WHERE rowid = ?'
    newVals += (1, )
    modify_db(query_str, newVals)

    errors['devices'] = processDev()

    return errors


def createForm(errors):
  #Set up our page elements to create the form.
  with app.app_context():
    hostInfo=query_db('SELECT * FROM AQhost', (), True)
    if hostInfo is None:
      #Fresh db without an entry for the basic info.
      modify_db('INSERT INTO AQhost DEFAULT VALUES')
      hostInfo=query_db('SELECT * FROM AQhost', (), True)

    seedVals=dict()
    #Info for the overall setup.
    for i in valList:
      seedVals[i] = hostInfo[i]

    #List our bus info
    busInfo = list()
    devNums=list()
    devs=list()
    for b in busses.listOpts():
      devNums.append(0)
      busInfo.append(b().retOpts())
      devs.append(list())

    #Populate known device info.
    hostDevs=query_db('SELECT rowid, * FROM hostDevice ORDER BY busType, busOrder ASC')
    for d in hostDevs:
      dev=dict()
      for pair in dbTypesMaps:
        dev[pair[0]]=d[pair[1]]

      devs[d['busType']].append(dev)
      devNums[d['busType']] += 1

    devSubNames = list()
    devSubTypes = buildSubTypes()
    for k, v in devSubTypes.items():
      devSubNames.append(dict())
      for j, d in v.items():
        devSubNames[k][j]=d().get('name')

    #Build dev Num Opts.
    devNumOpts = list()
    for d in devNums:
      a = dict()
      for i in range(max(d, 1)):
          a[i]=i
      devNumOpts.append(a)

    #Build the logging Opts.
    logPairs = (('readOpts', logging.readOpts), ('writeOpts', logging.writeOpts), ('reactOpts', logging.reactOpts))
    for o in logPairs:
      a = dict()
      for i, v in enumerate(o[1]()):
        a[i]=v().name
      seedVals[o[0]] = a

    seedVals['devNums'] = devNums
    seedVals['busInfo'] = busInfo
    seedVals['devSubNames'] = devSubNames
    seedVals['devs'] = devs
    seedVals['tempOpts'] = tempOpts
    seedVals['devNumOpts'] = devNumOpts
    #print(seedVals, file=sys.stderr)
    return seedVals, errors


def processDev():
  #Do the processing for our device setup stuff.
  #Iterate over our devtypes list.
  #print(request.form, file=sys.stderr)
  
  with app.app_context():
    error = dict()
    error['addr'] = dict()
    #Detect if we have an add button.
    for k in request.form:
      if 'AddDev' in k:
        busNum = k.split('_')[1]
        busses.listOpts()[int(busNum)]().addNewDev()

      if 'forget' in k:
        devNum = k.split('_')[1]
        modify_db('DELETE FROM AQlog WHERE assocDev=?', (devNum, ))
        modify_db('DELETE FROM aqChannel WHERE chDevice=?', (devNum, ))
        modify_db('DELETE FROM hostDevice WHERE rowid=?', (devNum, ))
        return
    
    #Gather the current info.
    hostDevs=query_db('SELECT * FROM hostDevice ORDER BY busType, busOrder ASC')

    #Generate counts for each dev type.
    devNums=list() #Counts of the number of devices on each bus.
    nextFill=list()
    busOrders=list()
    for t in busses.listOpts():
      devNums.append(0)
      busOrders.append(dict())
      nextFill.append(0)

    for d in hostDevs:
      devNums[d['busType']] += 1

    #Now, compare numbers of devices.
    for n, d in enumerate(busses.listOpts()):
      #Check to compare the number of devices in the form & in the db.
      thisKey = 'numDev' + str(n)
      if thisKey in request.form and int(request.form[thisKey]) > devNums[n]:
        #Looks like we need to create more.
        numToAdd = int(request.form[thisKey])-devNums[n]
        d().addNewDev(numToAdd)

      elif thisKey in request.form and int(request.form['numDev' + str(n)]) < devNums[n]:
        #Looks like we need to drop items from the db.
        #TODO: Do this more Manually. Find the IDs to Delete, delete the channels and logs, then delete the device.
        myQuery = 'DELETE FROM hostDevice WHERE busType=? AND busOrder>=?'
        modify_db(myQuery, (n, request.form['numDev' + str(n)]))
    
    #For the device details in the form, make updates.
    #Requery to get all of our db devices, post adds/removes.
    hostDevs=query_db('SELECT rowid, * FROM hostDevice ORDER BY busType, busOrder ASC')

    #Get our dev sub types.
    devSubTypes = buildSubTypes()

    #Go through each host Device and update as necessary.
    for d in hostDevs:
      query_str='UPDATE hostDevice SET '
      seedDefs=False
      doQuery=False
      newVals=list()
      b = d['busType']

      #If the device type has changed, also seed with default values.
      thisInput = 'type_'+str(d['rowid'])
      if thisInput in request.form.keys():
        thisDevType=int(request.form[thisInput])
        #print(thisDevType, file=sys.stderr)
        #print(d['devType'], file=sys.stderr)
        if d['devType'] != thisDevType:
          #The dev type changed.
          seedDefs=True
      else:
        #Either a new device or not in form, seed defaults and use default device type.
        seedDefs=True
        thisDevType=int(d['devType'])

      thisDev = devices.listOpts()[thisDevType]()
      error['addr'][d['rowid']] = ''
      #print(type(thisDev), file=sys.stderr)

      #Go through updating things.
      for p in dbTypesMaps:
        thisInput=p[0]+'_'+str(d['rowid'])
        #print(seedDefs, file=sys.stderr)
        if seedDefs or thisInput not in request.form.keys():
          if not hasattr(thisDev, 'def'+p[0]): continue
          thisVal = thisDev.get('def'+p[0])

        else:
          #Check for busOrder special case.
          if p[0] == 'number':
            busOrders[b], nextFill[b], thisVal = testOrder(busOrders[b],
              nextFill[b], request.form[thisInput])
          elif p[0] == 'addr':
            aAddr = thisDev.busType().allowedAddr
            if aAddr and request.form[thisInput] not in aAddr:
              thisVal = None
              error['addr'][d['rowid']] = 'Allowed ' + thisDev.busType().name + ' addresses are: ' + str(aAddr)
            else:
              thisVal = request.form[thisInput]
          else:
            thisVal = request.form[thisInput]

        newVals.append(thisVal)
        query_str += p[1]+'=?, '
        doQuery=True

      if seedDefs and 'devType' not in query_str:
        #Need to update the devType.
        query_str += 'devType=?, '
        newVals.append(thisDevType)

      if doQuery:
        query_str = query_str[:-2]
        query_str += ' WHERE rowid = ?'
        newVals.append(d['rowid'])
        #print(query_str, file=sys.stderr)
        #print(newVals, file=sys.stderr)
        modify_db(query_str, newVals)
  
        if seedDefs:
          dev = devices.listOpts()[thisDevType]()
          dev.initChans(d['rowid'])

    return error


def testOrder(busOrders, nextFill, formOrder):
  #Function to test and enforce our bus orders.
  #Test to see if this busOrder number has already been claimed.
  newOrder = formOrder
  if formOrder in busOrders.keys():
    #Already claimed, give out the nextFill number.
    newOrder = nextFill
  else:
    #Mark this number as claimed.
    busOrders[formOrder]=True

  #Find the next nextFill.
  while str(nextFill) in busOrders.keys():
    nextFill += 1

  return busOrders, nextFill, newOrder


def buildSubTypes():
  #Function to create our list of devsubtypes for DB associations.
  devSubTypes = dict()
  for dev in devices.listOpts():
    d=dev()
    b=d.get('busType')().getListNum()
    if b not in devSubTypes:
      devSubTypes[b] = dict()
    
    devSubTypes[b][d.getListNum()]=dev

  return devSubTypes
