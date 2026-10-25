from cameras.run.db import query_db
from cameras.cameras import app
#from PIL import Image
#import base64
#from io import BytesIO
#import requests

#Function to process our Index page.
def doIndex():
  with app.app_context():
    #Point to our images.
    images = list()

    #Test if we have any cameras configured:
    cfgRes = query_db('SELECT rowid FROM recSettings', ())
    if not cfgRes:
      return None

    numCam = int(query_db("SELECT numCam FROM recSettings", one=True)['numCam'])
    camSettings = query_db("SELECT * FROM camSettings WHERE rowid <= ?", (numCam, ))

    for c in camSettings:
      imgURL = c['imageLink']
      images.append({'name':c['name'], 'id':c['rowid']})

    return images


def getImage(URL):
  response = requests.get(URL, verify=False)
  data = BytesIO()
  im = Image.open(BytesIO(response.content))
  im.save(data, "JPEG")
  return base64.b64encode(data.getvalue())
