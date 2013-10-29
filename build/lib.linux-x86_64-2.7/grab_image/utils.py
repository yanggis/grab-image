from shapely.geometry import box

import requests
import datetime
import boto
import ee
import os

import urllib2
import shutil
import urlparse

def msecToDate(msecs):
    # convert milliseconds to properly formatted date string
    secs = float(msecs)/1000
    d = datetime.datetime.utcfromtimestamp(secs)
    return d.strftime("%Y-%m-%d")

def tryParse(x):
    # Accepts an object and attempts to parse it to a float
    try: 
        y = float(x)
    except ValueError:
        y = x
    return y

def geeAuth(user_path = os.path.expanduser('~')):
    # Authenticate Earth Engine user.  Ensure that the *.p12 key file
    # is in your ~/.ssh/ directory.
    key_file = '%s/.ssh/ee-privatekey.p12' % user_path
    if os.path.exists(key_file):
        acct = os.environ['GEE_ACCT']
        ee.Initialize(ee.ServiceAccountCredentials(acct, key_file))
    else:
        raise Exception('Ensure GEE key file is in ~/.ssh directory')

def formatPolygon(coords):
    # Accepts a set of coordinates, in sequence, and checks that they
    # are formatted counter-clockwise; returns a polygon.  Works for
    # non-convex polygons.
    def edger(c0, c1):
        x0, y0 = c0 
        x1, y1 = c1
        return (x1 - x0) * (y1 + y0)

    coord_seq = range(0, len(coords)-1)
    coll = [edger(coords[i], coords[i+1]) for i in coord_seq]

    if sum(coll) > 0:
        coords = list(reversed(coords))

    return ee.Feature.Polygon(coords)

def createBox(lon, lat, w = 1000, ccw = True):
    # Returns the coordinates of the corners of the box around the
    # supplied latitude and longitude of the centroid, with the width
    # of the box equal to `w`, in meeters. (default counter-clockwise)
    deg = (w / 2) / (60.* 1602.) # convert from meters to degrees
    b = box(lon - deg, lat - deg, lon + deg, lat + deg, ccw)
    return list(map(list, b.exterior.coords))

def upload(filename, bucket_name='landsatpostage'):
    # Uploads the specified file to to a specified bucket
    conn = boto.connect_s3(os.environ['AWS_KEY'], os.environ['AWS_ID'])
    bucket = conn.create_bucket(bucket_name)
    key = bucket.new_key(key_name=filename)
    key.set_contents_from_filename(filename)
    bucket.set_acl('public-read', filename)
    url = key.generate_url(expires_in=0, query_auth=False, force_http=True)
    return url

def download(url, fileName=None):
    def getFileName(url,openUrl):
        if 'Content-Disposition' in openUrl.info():
            # If the response has Content-Disposition, try to get filename from it
            cd = dict(map(
                lambda x: x.strip().split('=') if '=' in x else (x.strip(),''),
                openUrl.info()['Content-Disposition'].split(';')))
            if 'filename' in cd:
                filename = cd['filename'].strip("\"'")
                if filename: return filename
        # if no filename was found above, parse it out of the final URL.
        return os.path.basename(urlparse.urlsplit(openUrl.url)[2])

    r = urllib2.urlopen(urllib2.Request(url))
    try:
        fileName = fileName or getFileName(url,r)
        with open(fileName, 'wb') as f:
            shutil.copyfileobj(r,f)
    finally:
        r.close()
