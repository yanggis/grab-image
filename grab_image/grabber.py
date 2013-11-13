import Image
import numpy as np
import utils
import ee
import re
import os
import requests
import zipfile
import StringIO
import ImageEnhance
import ImageFilter
import ImageOps

# Authenticate earth engine
utils.geeAuth()

def sharpenImage(img, enhance_factor = 1.7):
    # Accepts an image and returns a more detailed image with higher
    # contrast given by the `enhance_factor`, such that 1.7 gives an
    # image with 70% more contrast
    filtered = img.filter(ImageFilter.DETAIL)
    contrast = ImageOps.autocontrast(filtered)
    return contrast

def grabImage(lon, lat, year, w = 8000):
    # Note that we cannot do pan-sharpening on pre-composited images,
    # since they don't have Band 8, which Landsat ETM+ does have.
    b = utils.createBox(lon, lat, w = w)
    poly = utils.formatPolygon(b)
    composite = ee.Image('L7_TOA_1YEAR/%s' % year).select('30', '20', '10')

    visparams = {'bands': ['30', '20', '10'], 'gain':  [1.4, 1.4, 1.1]} 
    visual_image = composite.visualize(**visparams)

    params = {'scale':30, 'crs':'EPSG:4326', 'region':str(b[:-1])}
    
    url = visual_image.getDownloadUrl(params)
    req = requests.get(url)

    # Convert the downloaded tif image to a numpy array
    z = zipfile.ZipFile(StringIO.StringIO(req.content))

    def _toArray(color):
        # Grab the image with the associated color (red, green, or
        # blue) and return a numpy array
        a = filter(lambda x: x.endswith('%s.tif' % color), z.namelist())
        p = z.extract(a[0])
        im = Image.open(p)
        os.remove(p)
        return np.array(im)
    
    tifs = filter(lambda x: x.endswith('.tif'), z.namelist())
    png_name = '%s.png' % tifs[0].split(".")[0]
    r, g, b = map(_toArray, ['red', 'green', 'blue'])

    # convert three separate image arrays into a square image where
    # each element is a triplet
    triplets = np.array([r, g, b]).swapaxes(0,2)
    data = np.transpose(triplets, axes = (1,0,2)) # correct for axis swap
    img = Image.fromarray(data, 'RGB')
    sharpenImage(img).save(png_name)

    url = utils.upload(png_name)
    os.remove(png_name)
    return url

def grabThumbs(lon, lat, x, y, year, w = 8000):
    # Grab landsat thumbnail with all visual parameters already baked
    # in instead of manipulating the image in python
    b = utils.createBox(lon, lat, w = w)
    poly = utils.formatPolygon(b)
    composite = ee.Image('L7_TOA_1YEAR/%s' % year).select('30', '20', '10')

    visparams = {'bands': ['30', '20', '10'], 'gain':  [2, 2, 1.7]} 
    visual_image = composite.visualize(**visparams)

    params = {'scale':30, 'crs':'EPSG:4326', 'region':str(b[:-1])}
    
    ee_url = visual_image.getThumbUrl(params)
    req = utils.download(ee_url)
    
    s = re.search('thumbid=(.*)&token=', ee_url)
    thumbid = s.group(1)
    
    filename = "%s.png" % thumbid
    Image.open("thumb").save(filename)
    destination_path = "validation/%s/%s/%s.png" % (x, y, year)
    aws_url = utils.upload(filename, destination_path)
    
    os.remove("thumb")
    os.remove(filename)
    return aws_url
