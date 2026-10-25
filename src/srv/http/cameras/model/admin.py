from cameras.run.db import query_db, modify_db
from cameras.cameras import app
from flask import request
from datetime import datetime, UTC
import bcrypt

def check_password(environ, user, password):
    with app.app_context():
        userObj = query_db('SELECT * FROM camUser WHERE userName = ?', (user, ), one=True)

        if userObj is None:
            return None
        else:
            plaintext = password.encode('utf-8')
            hashtext = userObj['passHash']
            if bcrypt.checkpw(plaintext, hashtext):
                return userObj['rowid']
            else:
                return False


def change_user(userName, newPassword, userLevel, new):
    #Function to create or update user credentials.
    #Make sure to verify that it's OK for your user to do this BEFORE you call this function.
    with app.app_context():
        userObj = query_db('SELECT rowid, authLevel FROM camUser WHERE username = ?', (userName, ), one=True)

        if not new and userObj is None:
            return "Username " + userName + " was not found, "

        if new and userObj is not None:
            return "Username " + userName + " already exists and cannot be created, "
        nPWD=newPassword.encode('utf-8')
        PassHash = bcrypt.hashpw(nPWD, bcrypt.gensalt())
        if new:
            qRes = modify_db('INSERT INTO camUser(userName, passHash, authLevel) VALUES (?, ?, ?)', (userName, PassHash, userLevel))

            return "Added new user " + userName + ", "
        else:
          retStr = ""
          if newPassword:
            qRes = modify_db('UPDATE camUser SET passHash = ?, authLevel = ? WHERE rowid = ?',
                    (PassHash, userLevel, userObj['rowid']))
            retStr += "Updated password for " + userName + ", "
          if userLevel != userObj['authLevel']:
            modify_db('UPDATE camUser SET authLevel = ? WHERE rowid = ?',
                    (userLevel, userObj['rowid']))
            retStr += "Updated privileges for " + userName + ", "
          return retStr


def processForm(isAdmin, username):
  with app.app_context():
    status = ''
    if 'saveLoc' in request.form.keys():
      #We're updating the camera stuff.
      modify_db('INSERT OR REPLACE INTO recSettings (rowid, saveLoc, saveTime, freeTarget, numCam, lastEdit) VALUES (?, ?, ?, ?, ?, ?)', (1, request.form['saveLoc'], request.form['saveTime'], request.form['freeTarget'], request.form['numCam'], int(datetime.now(UTC).timestamp())))

      for i in range(1, int(request.form['numCam'])+1):
        modify_db('INSERT OR REPLACE INTO camSettings (rowid, name, vidLink) VALUES (?, ?, ?)', (i, request.form['C-'+str(i)+'-name'], request.form['C-'+str(i)+'-vid']))

      return status

    if 'Change' in request.form.keys():
      #Handle self password change.
      if check_password(None, username, request.form['currPass']):
        if request.form['newPass1'] == request.form['newPass2']:
          status += "Updated your password, "
          usrLvl = query_db("SELECT * FROM camUser WHERE userName = ?",
            (username, ), one=True)['authLevel']
          change_user(username,
            request.form['newPass1'], usrLvl, False)
        else:
          status += "New password fields did not match, "
      else:
        status += "Current password provided not correct, "

      return status

    if isAdmin:
      users = query_db("SELECT rowid, userName, authLevel FROM camUser WHERE userName != ?",
            (username, ))
      if request.form['newUserPass'] and request.form['newUsername']:
        #Admin has entered info asking for a new user with password.
        status += change_user(request.form['newUsername'],
          request.form['newUserPass'],
          request.form['newUserPriv'],
          True)

      for u in users:
        passStr = 'pass' + str(u['rowid'])
        if request.form[passStr]:
          status += change_user(u['userName'], request.form[passStr], u['authLevel'], False)

        privLvl = 'priv' + str(u['rowid'])
        if request.form[privLvl] != str(u['authLevel']):
           status += change_user(u['userName'], False, request.form[privLvl], False)

        delStr = 'delete' + str(u['rowid'])
        if delStr in request.form:
          modify_db('DELETE FROM camUser WHERE rowid = ?', (u['rowid'], ))
          status += "Deleted user: " + u['userName'] + ", "

    return status


def createForm(isAdmin, status, username):
  with app.app_context():
    if not isAdmin: return None, status
    userList = list()
    users = query_db("SELECT rowid, userName, authLevel FROM camUser WHERE userName != ?",
            (username, ))

    for u in users:
      userList.append({'Name':u['userName'], 'Number':u['rowid'], 'Priv':u['authLevel']})

    camConfig = query_db("SELECT * FROM recSettings", one=True)
    camData = query_db("SELECT * FROM camSettings")

    if not camConfig:
      camConfig = {'numCam':1, 'freeTarget':10, 'saveTime':60}

    return userList, camConfig, camData, status
