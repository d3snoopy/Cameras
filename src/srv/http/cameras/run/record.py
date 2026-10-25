from cameras.run.db import query_db, get_db
from cameras.run.status import putStatus
import os, time, subprocess, re, threading, queue
from datetime import datetime, timedelta
stopEvent = threading.Event()
statuses = queue.Queue()

#TODO: Test with Supervisor to see if a TERM from supervisor stops things relatively cleanly or if it gets all crazy.
# If it doesn't close cleanly, then add some code to try to gracefully stop on SIGTERM or SIGINT

"""
import signal
import time

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, signum, frame):
    self.kill_now = True

if __name__ == '__main__':
  killer = GracefulKiller()
  while not killer.kill_now:
    time.sleep(1)
    print("doing something in a loop ...")

  print("End of the program. I was killed gracefully :)")
"""

class recorder:
  def __init__(self):
    self.db = get_db(newdb = True, appContext = False)
    self.extension = ".mp4"
    self.readDB()
    self.threads = dict()
    return

  def start(self):
    while True: #This restarts everything if we got updates and broke out of the housekeeping loop below.
      if not self.storeLoc:
        #The storage location is blank, which indicates no recording to be done.
        recStatus = {1:{'name':'All Cameras', 'status':'No recording configured'}}
        putStatus(recStatus)
        time.sleep(60) #There's a decent chance that we're here because the db isn't configured, so default to checking for an update every 60 seconds.
        self.readDB()
        continue

      self.housekeeper()
      stopEvent.clear()
      recStatus = dict()

      if not os.path.exists(self.storeLoc): os.mkdir(self.storeLoc)

      self.threads = dict()
      #Do the recording stuff.
      for c in self.cameras:
        recStatus[c['id']] = {'name':c['name'], 'status':'Starting'}
        t = threading.Thread(target=record_video, args=(c, ))
        self.threads[c['id']]=t

      #Start all the threads.
      for t in self.threads.values():
        t.start()

      putStatus(recStatus)
      #Loop on our housekeeping thread.
      while True:
        time.sleep(1.0)

        if stopEvent.is_set(): break

        #Check for new status info and send it out if updated.
        self.newPut = False
        while not statuses.empty():
          self.newPut = True
          newStatus = statuses.get()
          recStatus[newStatus[0]]['status'] = newStatus[1]

        if datetime.now() > self.nextHousekeeping: self.housekeeper()

        if self.newPut: putStatus(recStatus) #Puts the rec status in /tmp for the website to read and display.

      #If we got here, we're doing a restart. Wait for all the threads to finish.
      for t in threads:
        t.join()


  def readDB(self):
    recSettings = query_db("SELECT * FROM recSettings WHERE rowid = 1", db=self.db, one=True)
    if not recSettings: #This means the db isn't populated yet. Doing this will punt up to the no recordings configured loop in the start method.
      self.storeLoc = None
      return

    self.storeLoc = recSettings["saveLoc"]+'/recordings'
    self.storeSpace = recSettings["freeTarget"]*1073741824 #GB to b
    self.recTime = recSettings["saveTime"]
    
    camSettings = query_db("SELECT * FROM camSettings WHERE rowid <= ?", (recSettings['numCam'], ), db=self.db) #The numCam limit prevents orphan configs from being used.
    self.cameras = list()
    for c in camSettings:
      name = re.sub(r'\W+', '', c["name"])
      self.cameras.append({'name':str(c["rowid"])+"-"+name, 'rtspUrl':c["vidLink"], 'storeLoc':self.storeLoc, 'storeDur':self.recTime, 'extension':self.extension, 'id':c["rowid"]})

    self.lastEdit = recSettings["lastEdit"]

    return

  def housekeeper(self):
    if query_db("SELECT lastEdit FROM recSettings WHERE rowid = 1", db=self.db, one=True)["lastEdit"]>self.lastEdit:
      self.readDB()
      stopEvent.set()

    #Free up space
    free_space_up_to(self.storeSpace, self.storeLoc, self.extension)

    #Try to restart any threads that errored out.
    for k, v in self.threads.items():
      if not v.is_alive():
        recStatus[k]['status'] = 'Restarting'
        self.newPut = True
        t = threading.Thread(target=record_video, args=(cameras[k], ))
        self.threads[k] = t
        t.start()

    #Set the next time to do this housekeeping.
    self.nextHousekeeping = datetime.now() + timedelta(minutes=self.recTime) #Housekeeping once per recTime
    return


#Utility functions.
#Delete files until we reach the perscribed free space.
def free_space_up_to(free_bytes_required, rootfolder, extension=".mp4"):
  file_list= files_to_delete(rootfolder, extension)
  while file_list:
    statv= os.statvfs(rootfolder)
    if statv.f_bfree*statv.f_bsize >= free_bytes_required:
      break
    os.remove(file_list.pop())

  #Cleanup empty folders
  for root, dirs, files in os.walk(rootfolder):
    if not len(dirs) and not len(files):
      os.rmdir(root)


#List file from oldest to newest.
def files_to_delete(rootfolder, extension=".mp4"):
    return sorted(
        (os.path.join(dirname, filename)
        for dirname, dirnames, filenames in os.walk(rootfolder)
        for filename in filenames
        if filename.endswith(extension)),
        key=lambda fn: os.stat(fn).st_mtime,
        reverse=True)


def record_video(c):
  while True:
    thispath = c['storeLoc'] + "/" + str(datetime.now().year) + "/" + str(datetime.now().month) + "/" + str(datetime.now().day) + "/"
    #Create the year/month/day folder if it doesn't exist.
    if not os.path.exists(thispath): os.makedirs(thispath)

    #Count the number of files for this camera exist in this folder.
    #c = [f for r, d, files in os.walk(thispath) for f in files if f.startswith(c['name'])].len() + 1
    #Set up the hour and minutes for the filename.
    endStr = str(datetime.now().hour)+str(datetime.now().minute)

    filename = thispath+c['name']+"-"+endStr+c['extension'] #Note that we strip non-alphanumeric off the name

    command = [
      'ffmpeg',
      '-rtsp_transport', 'tcp',
      '-i', c['rtspUrl'],
      "-c:v", "copy",
      "-c:a", "copy",
      '-t', convTime(c['storeDur']),
      filename]
    process = subprocess.Popen(
      command,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL
    )
    statuses.put((c['id'], 'Recording'))

    while not process.poll():
      if stopEvent.is_set():
        process.terminate()
        statuses.put((c['id'], 'Terminated'))
        return
      time.sleep(1.0)

    if process.returncode != 0:
      statuses.put((c['id'], 'Error Recording'))
      return

    statuses.put((c['id'], 'Finished'))



def generate_frames(rtsp_url):
  command = [
    'ffmpeg',
    '-rtsp_transport', 'tcp',
    '-i', rtsp_url,
    '-f', 'mjpeg',
    '-q:v', '2',
    '-r', '15',
    '-'
  ]
  process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    bufsize=0
  )
  buffer = b''
  try:
    while True:
      chunk = process.stdout.read(4096)
      if not chunk:
        break
      buffer += chunk
      while True:
        start = buffer.find(b'\xff\xd8')
        end = buffer.find(b'\xff\xd9')
        if start != -1 and end != -1 and end > start:
          frame = buffer[start:end+2]
          buffer = buffer[end+2:]
          yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
            b'\r\n' + frame + b'\r\n')
        else:
          break
  finally:
    process.terminate()


def generate_image(rtsp_url):
  from cv2 import VideoCapture, imencode
  try:
    video = VideoCapture(rtsp_url)
    #Flush a few frames, to try to make sure we get a clean image.
    for i in range(6):
      ret, frame = video.read()

    ret, jpeg = imencode('.jpg', frame)
    return jpeg.tobytes()
  except:
    return None


def convTime(duration):
  #Converts a duration in minutes to hours:minutes:seconds
  hours = int(duration/60)
  minutes = duration%60

  return(f"{hours:02}:{minutes:02}:00")
