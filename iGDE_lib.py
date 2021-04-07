
#Module imports
from  geeViz.changeDetectionLib import *
Map.clearMap()
####################################################################################################
#Define user parameters:

# Specify study area: Study area
# Can be a featureCollection, feature, or geometry
California = ee.Feature(ee.FeatureCollection('TIGER/2016/States')\
            .filter(ee.Filter.eq('NAME','California'))\
            .first())\
            .convexHull(10000)\
            .buffer(10000)\
            .geometry()


daymetCollection = 'projects/igde-work/raster-data/DAYMET-Collection'
compositeCollection = 'projects/igde-work/raster-data/composite-collection'

trainingStartYear = 1985
trainingEndYear = 2018

applyStartYear = 1985
applyEndYear = 2019

