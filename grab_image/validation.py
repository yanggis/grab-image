import pandas as pd
import requests
import StringIO
import random
import utils
import json
import os
from grabber import grabThumbs

def sampleCountryPts(n, eco):
    # Returns a subsample of size `n` from the ecoregion alerts, with
    # lat-lon coordinates, the dates, and the xy-tiles

    # construct query
    base = "http://wri-01.cartodb.com/api/v2"
    var = "x,y,date,lat,lon"
    sql = "SELECT %s FROM cdm_2013_11_08 WHERE ecoregion = '%s'" % (var, eco)
    query = "%s/sql?format=csv&q=%s" % (base, sql)

    # read the csv into a pandas data frame
    r = requests.get(query)
    df = pd.read_csv(StringIO.StringIO(r.content))

    # randomly sample `n` rows from ecoregion alerts, return subset
    rows = random.sample(df.index, n)
    sub  = df.ix[rows]

    return sub

def processRow(row):
    # Accepts a row (representing a single alert) from a pandas data
    # frame with the following fields; uploads the images for all
    # available cloud-free landsat composites and returns the row,
    # unchanged.
    x, y, date, lat, lon = row
    for year in range(2000, 2013):
        grabThumbs(lon, lat, x, y, year)

    return {'x':x, 'y':y, 'date':date, 'lat':lat, 'lon':lon}

def genNewImages(n, eco):
    # Uploads the landsat images for `n` alerts in the supplied
    # ecoregion.  Returns a list of dictionaries with identifying
    # information of each alert.
    df = sampleCountryPts(n, eco = eco)
    df.apply(processRow, axis = 1)

    d = [ 
        dict([
            (colname, row[i]) 
            for i,colname in enumerate(df.columns)
        ])
        for row in df.values
    ]

    return d

def updateIndex(new_items):
    # Accepts a list of dictionaries with new alerts.  Appends the new
    # alerts to `dict.json`, stored on S3, which contains information
    # on all alerts that have the landsat images already 
    json_file = 'dict.json'
    base = "http://landsatpostage.s3.amazonaws.com"
    a = requests.get("%s/validation/%s" % (base, json_file))
    old_items = json.loads(a.content)
    if old_items != None:
        d =  old_items + new_items
    else:
        d = new_items

    # dump the new and old entries into a local json file
    with open(json_file, 'w') as f:
        json.dump(d, f)

    # upload the json file and delete the local copy
    utils.upload(json_file, 'validation/%s' % json_file)
    os.remove(json_file)
    return d


def processPts(n, eco = 40158):
    # Process the landsat image stack for `n` alerts in the supplied
    # ecoregion; update the index file with the list of alerts that
    # have been processed. 
    new_items = genNewImages(n, eco)
    return updateIndex(new_items)
