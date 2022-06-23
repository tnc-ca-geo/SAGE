"""
MIT License

Copyright (c) 2022 Ian Housman and Leah Campbell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


#Script to get DAYMET climate date mean composites using the getImagesLib and view outputs using the Python visualization tools
#Acquires annual DAYMET composites and then adds them to the viewer

####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, taskManagerLib, assetManagerLib
from geeViz.geeView import *

####################################################################################################
#Define user parameters:

# Options defined in SAGE_Initialize:
# Start and end year 
# Study Area
# CRS, transform and scale
# Export image collection name
# Whether to export composites or visualize them in geeView

#--------The Following Options Are Default DayMet Compositing Methods and Do Not Need to Be Changed-----------

# SAGE does Daymet compositing along the water year (Oct 1 - Oct 1). This script wraps the date around to the proper year
startJulian = 274
endJulian = 273

# Specify an annual buffer to include imagery from the same season 
# timeframe from the prior and following year. timeBuffer = 1 will result 
# in a 3 year moving window. If you want single-year composites, set to 0
timebuffer = 0

# Specify the weights to be used for the moving window created by timeBuffer
# For example- if timeBuffer is 1, that is a 3 year moving window
# If the center year is 2000, then the years are 1999,2000, and 2001
# In order to overweight the center year, you could specify the weights as
# [1,5,1] which would duplicate the center year 5 times and increase its weight for
# the compositing method. If timeBuffer = 0, set to [1]
weights = [1]

#Specify method to summarize each year
#Some possible options are: ee.Reducer.mean(), ee.Reducer.percentile([n])
compositingReducer = ee.Reducer.mean()


####################################################################################################
#                        End User Parameters
####################################################################################################

####################################################################################################
#                     Define Functions
####################################################################################################

#Wrapper function to get climate data
# Supports:
# NASA/ORNL/DAYMET_V3
# NASA/ORNL/DAYMET_V4
# UCSB-CHG/CHIRPS/DAILY (precipitation only)
#and possibly others
def getClimateWrapper(\
  daymetInputCollection,
  studyArea,
  startYear,
  endYear,
  startJulian,
  endJulian,
  timebuffer,
  weights,
  compositingReducer,
  exportComposites,
  exportPathRoot,
  crs,
  transform,
  scale,
  exportBands = None):

  args = getImagesLib.formatArgs(locals())
  if 'args' in args.keys():
    del args['args']
  print(args)

  #Prepare dates
  #Wrap the dates if needed
  wrapOffset = 0
  if startJulian > endJulian:
    wrapOffset = 365

  startDate = ee.Date.fromYMD(startYear,1,1).advance(startJulian-1,'day')
  endDate = ee.Date.fromYMD(endYear,1,1).advance(endJulian-1+wrapOffset,'day')
  print('Start and end dates:', startDate.format('YYYY-MM-dd').getInfo(), endDate.format('YYYY-MM-dd').getInfo())
  print('Julian days are:',startJulian,endJulian)

  #Get climate data
  c = ee.ImageCollection(daymetInputCollection)\
           .filterBounds(studyArea.bounds())\
           .filterDate(startDate,endDate)\
           .filter(ee.Filter.calendarRange(startJulian,endJulian))

  #Set to appropriate resampling method
  c = c.map(lambda img: img.resample('bicubic'))
  Map.addLayer(c, {}, 'Raw Climate', False)

  #Create composite time series
  ts = getImagesLib.compositeTimeSeries(**{\
    'ls': c, 
    'startYear': startYear, 
    'endYear': endYear, 
    'startJulian': startJulian,
    'endJulian': endJulian,
    'timebuffer': timebuffer,
    'weights': weights,
    'compositingMethod': None,
    'compositingReducer': compositingReducer})
  ts = ts.map(lambda i : i.float())

  #Export composite collection
  if exportComposites:
    #Set up export bands if not specified
    if exportBands == None:
      exportBands = ee.List(ee.Image(ts.first()).bandNames())

    getImagesLib.exportCollection(**{\
      'exportPathRoot': exportPathRoot,
      'outputName': daymetInputCollection.split('/')[2],
      'studyArea': studyArea, 
      'crs': crs,
      'transform': transform,
      'scale': scale,
      'collection': ts,
      'startYear': startYear,
      'endYear': endYear,
      'startJulian': startJulian,
      'endJulian': endJulian,
      'compositingReducer': compositingReducer,
      'timebuffer': timebuffer,
      'exportBands': exportBands})
  
  return ts

####################################################################################################
#                     Start Function Calls
####################################################################################################
if not ee.data.getInfo(sage.daymetCollection):
  print('Creating ' + sage.daymetCollection)
  ee.data.createAsset({'type': 'ImageCollection'}, sage.daymetCollection)
  assetManagerLib.updateACL(sage.daymetCollection, all_users_can_read = True)

ts = getClimateWrapper(**{\
  'daymetInputCollection': sage.daymetInputCollection,
  'studyArea': sage.studyArea,
  'startYear': sage.daymetStartYear,
  'endYear': sage.daymetEndYear,
  'startJulian': startJulian,
  'endJulian': endJulian,
  'timebuffer': timebuffer,
  'weights': weights,
  'compositingReducer': compositingReducer,
  'exportComposites': sage.exportDaymet,
  'exportPathRoot': sage.daymetCollection,
  'crs': sage.crs,
  'transform': sage.transform,
  'scale': sage.scale,
  'exportBands': sage.daymetExportBands})

####################################################################################################
#             Visualize in geeView() if Selected
####################################################################################################
if sage.viewDaymet:

  Map.addLayer(ee.ImageCollection(ts), {}, 'Annual Climate Time Series', False)

  #Load the study region
  Map.addLayer(sage.studyArea, {'strokeColor': '0000FF'}, "Study Area", True)
  Map.centerObject(sage.studyArea)

  Map.view()

else:

  taskManagerLib.trackTasks()


