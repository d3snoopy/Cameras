from flask import render_template, Flask, request, redirect, url_for, flash, g, send_file, Response, current_app
from flask_login import LoginManager, UserMixin, login_required, fresh_login_required, login_user, logout_user, current_user
from cameras.run.db import query_db, modify_db
from cameras.run.status import getStatus, sizeof_fmt
from os.path import exists
#import re
import requests

import os, time
import cv2

app = Flask(__name__)

if not exists('appkey'):
  with open('appkey', 'wb') as f:
    from os import urandom
    f.write(urandom(20).hex().encode('utf-8'))

with open('appkey', 'rb') as f:
  app.secret_key = f.read()


login_manager = LoginManager(app)
login_manager.login_view = "login"

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    db.init_db()
    print('Initialized the database.')

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Things for authentication.
class User(UserMixin):
  def __init__(self, id, username, passHash, authLevel):
    self.id = str(id)
    self.username = username
    self.passHash = passHash
    self.authLevel = authLevel
    self.authenticated = False

  def is_active(self):
    return True

  def is_anonymous(self):
     return False

  def is_authenticated(self):
    return self.authenticated

  def get_id(self):
    return self.id

# Our user manager callback.
@login_manager.user_loader
def load_user(user_id):
  u = query_db('SELECT * FROM camUser WHERE rowid = ?', (user_id, ), one=True)
  if u is None:
    return None
  else:
    return User(int(u['rowid']), u['userName'], u['passHash'], u['authLevel'])

# Login page for users.
@app.route('/login', methods=['GET', 'POST'])
def login():
  if current_user.is_authenticated:
    return redirect(url_for('index'))

  from cameras.model.admin import change_user, check_password
  error = ''
  if request.method == 'POST':
    user = request.form['username']
    password = request.form['password']

    #Decide if this is the initial user setup.
    userRes = query_db('SELECT rowid FROM camUser', ())
    if not userRes:
      pass2 = request.form['password2']
      if password == pass2 and password and user:
        change_user(user, password, 3, True)
      else:
        error = 'Passwords do not match or fields blank'

    else:
      myUser = check_password(None, user, password)
      if myUser:
        if 'remCheck' in request.form.keys():
          remCheck = True
        else:
          remCheck = False

        login_user(load_user(myUser), remember=remCheck)
        return redirect(url_for('index'))
      else:
        error = 'Invalid Username/Password'

  #Need to decide if this is a fresh db, if so, we're asking the user to create an initial user
  userRes = query_db('SELECT rowid FROM camUser', ())
  if not userRes:
    #There are no users in the DB, need to get the user to create one.
    headStr = 'Create Admin User'
    double = True
  else:
    headStr = 'Camera Login'
    double = False

  return render_template('login.html', error=error, headStr=headStr, double=double)

@login_manager.needs_refresh_handler
def refresh():
  logout_user()
  return redirect('login')


@app.route('/logout')
@app.route('/resetlogin')
@login_required
def logout():
  logout_user()
  return redirect('login')


# Now, our pages
@app.route("/")
@login_required
def index():
    import cameras.model.index
    # Process our Index data.
    images = cameras.model.index.doIndex()

    return render_template('index.html', images=images, user=current_user.username, recStatus=getStatus())



@app.route('/admin', methods=['GET', 'POST'])
@fresh_login_required
def admin():
    import cameras.model.admin
    errors = dict()
    # Process the model.
    isAdmin = (current_user.authLevel > 2)
    isConfig = (current_user.authLevel > 1)
    status = ''
    if request.method == 'POST':
      status = cameras.model.admin.processForm(isAdmin, isConfig, current_user.username)

    userList, camConfig, camData = cameras.model.admin.createForm(isAdmin, isConfig, current_user.username)

    return render_template('admin.html', status=status, userList=userList, admin=isAdmin, config=isConfig, camConfig=camConfig, camData=camData, user=current_user.username, recStatus=getStatus())


@app.route('/stream/<camID>')
@login_required
def stream(camID):
    from cameras.run.record import generate_frames
    streamURL = query_db("SELECT vidLink FROM camSettings WHERE rowid = ?", (camID, ),one=True)['vidLink']

    return Response(generate_frames(streamURL), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/image/<camID>')
@login_required
def image(camID):
  from cameras.run.record import generate_image
  pic = generate_image(query_db("SELECT vidLink FROM camSettings WHERE rowid = ?", (camID, ),one=True)['vidLink'])

  return Response(pic,mimetype="image/jpeg")


@login_required
@app.route('/videos/<path:folders>')
@app.route('/videos/')
def mybrowser(folders=''):
    environ = request.environ
    path = environ.get('PATH_INFO')
    #print(path)
    path = path.split('videos')[1]
    #print(path)
    saveLoc = query_db('SELECT saveLoc FROM recSettings WHERE rowid = 1', one=True)['saveLoc']
    os_path = saveLoc+'/recordings'+path.rstrip('/')
    if path.endswith('/'):
        path_title = os_path.split('recordings')[1]+'/'
        if not exists(os_path):
          return render_template('videos.html', path_title='No Recordings Available', user=current_user.username, recStatus=getStatus())
        files = os.listdir(os_path)
        file_list = list()
        for file in files:
            #print(file)
            linkpath = environ.get('PATH_INFO')+file
            path = os_path+'/'+file
            if os.path.isdir(path):
              linkpath += '/'
              file += '/'
            size = os.path.getsize(path)
            date = os.path.getmtime(path)
            date = time.gmtime(date)
            date = time.strftime('%d-%b-%Y %H:%M',date)
            file_list.append((file, linkpath, date, size))

        #sort the results.
        sparam = request.args.get('sort', default=1, type=int)
        sdir = request.args.get('dir', default=1, type=int)
        if sdir:
          file_list.sort(key=lambda tup: tup[sparam])
        else:
          file_list.sort(key=lambda tup: tup[sparam], reverse=True)

        #make the file sizes human readable.

        file_list = [(val[0], val[1], val[2], sizeof_fmt(val[3])) for val in file_list]

        #Add in going up a directory.
        file_list = [('../', '../', '', '')] + file_list

        return render_template('videos.html', path_title=path_title, file_list=file_list, sparam=sparam, sdir=sdir, user=current_user.username, recStatus=getStatus())
    else:
      return send_file(os_path, conditional=True)


@app.route('/reboot', methods=['POST'])
@login_required
def reboot():
  if current_user.authLevel < 3: return render_template('badprivilges.html', user=current_user.username, recStatus=getStatus())

  with open('/tmp/reboot', 'w') as f:
    f.write('reboot')

  return 'Rebooting Server'


@app.route('/shutdown', methods=['POST'])
@login_required
def shutdown():
  if current_user.authLevel < 3: return render_template('badprivilges.html', user=current_user.username, recStatus=getStatus())

  with open('/tmp/shutdown', 'w') as f:
    f.write('shutdown')

  return 'Shutting Down Server'
