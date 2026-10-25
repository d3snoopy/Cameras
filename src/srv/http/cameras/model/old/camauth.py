from run.db import query_db
from run.db import modify_db
from flask import request
import string
import random
from hashlib import md5
import sys

def check_password(environ, user, password):
    #TODO: need a way to pull some form of token from environ so we can reset the login on a per-session basis.
    userObj = query_db('SELECT * FROM camUser WHERE userName = ?', (user, ), one=True)

    if userObj is None:
        return None
    else:
        valToHash = str(password + userObj['passSalt'])
        providedHash = md5(valToHash.encode('utf-8')).hexdigest()
        savedHash = userObj['passHash']
        if providedHash == savedHash:
            return userObj['rowid']
        else:
            return False


def change_user(userName, newPassword, userLevel, new):
    #Function to create or update user credentials.
    #Make sure to verify that it's OK for your user to do this BEFORE you call this function.
    #with app.app_context():
        userObj = query_db('SELECT rowid, passSalt FROM camUser WHERE username = ?', (userName, ), one=True)


        if not new and userObj is None:
            return "Username " + userName + " was not found, "

        if new and userObj is not None:
            return "Username " + userName + " already exists and cannot be created, "

        if new:
            newSalt = ''.join(random.choice(string.ascii_letters) for _ in range(10))
            valToHash = str(newPassword + newSalt)
            PassHash = md5(valToHash.encode('utf-8')).hexdigest()
            qRes = modify_db('INSERT INTO camUser(userName, passHash, passSalt, authLevel) VALUES (?, ?, ?, ?)', (userName, PassHash, newSalt, userLevel))

            return "Added new user " + userName + ", "
        elif newPassword:
            valToHash = str(newPassword + userObj['passSalt'])
            PassHash = md5(valToHash.encode('utf-8')).hexdigest()
            qRes = modify_db('UPDATE camUser SET passHash = ?, authLevel = ? WHERE rowid = ?',
                    (PassHash, userLevel, userObj['rowid']))
            return "Updated password for " + userName + ", "
        else:
            modify_db('UPDATE camUser SET authLevel = ? WHERE rowid = ?',
                    (userLevel, userObj['rowid']))
            return "Updated privileges for " + userName + ", "


def processForm(isAdmin, username):
  #with app.app_context():
    status = ''
    print(request.form, file=sys.stderr)
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
          status += auth.change_user(u['userName'], request.form[passStr], u['authLevel'], False)

        privLvl = 'priv' + str(u['rowid'])
        if request.form[privLvl] != str(u['authLevel']):
           status += auth.change_user(u['userName'], False, request.form[privLvl], False)

        delStr = 'delete' + str(u['rowid'])
        if delStr in request.form:
          modify_db('DELETE FROM camUser WHERE rowid = ?', (u['rowid'], ))
          status += "Deleted user: " + u['userName'] + ", "

    return status


def createForm(isAdmin, status, username):
  #with app.app_context():
    if not isAdmin: return None, status
    userList = list()
    users = query_db("SELECT rowid, userName, authLevel FROM camUser WHERE userName != ?",
            (username, ))

    for u in users:
      userList.append({'Name':u['userName'], 'Number':u['rowid'], 'Priv':u['authLevel']})

    return userList, status
