import Image
import numpy as np
import utils
import ee
import os
import requests
import zipfile
import StringIO
import ImageEnhance
import ImageFilter

# Authenticate earth engine
utils.geeAuth()

def sharpenImage(img, enhance_factor = 1.7):
    # Accepts an image and returns a more detailed image with higher
    # contrast given by the `enhance_factor`, such that 1.7 gives an
    # image with 70% more contrast
    filtered = img.filter(ImageFilter.DETAIL)
    enhance_instance = ImageEnhance.Contrast(filtered)
    return enhance_instance.enhance(enhance_factor)

def grabImage(lon, lat, year, w = 4000):
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
    return {'lon' : lon, 'lat' : lat, 'url': url}
