  """
   Copyright 2021 Ian Housman
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
#Script to get DAYMET climate date mean composites using the getImagesLib and view outputs using the Python visualization tools
#Acquires annual DAYMET composites and then adds them to the viewer
####################################################################################################
from iGDE_lib import *
####################################################################################################
#Define user parameters:

# Specify study area: Study area
# Can be a featureCollection, feature, or geometry
studyArea = California

#Specify collection to use (V3 or V4)
collectionName = 'NASA/ORNL/DAYMET_V4'

#Specify start and end years
#Script will take care of date wrapping for water year
startYear = 1983
endYear = 2019
startJulian = 274
endJulian = 273
timebuffer = 0
weights = [1]

#Specify method to summarize each year
#Some possible options are: ee.Reducer.mean(), ee.Reducer.percentile([n])
compositingReducer = ee.Reducer.mean()


# Provide location composites will be exported to
# This should be an asset folder, or more ideally, an asset imageCollection
exportPathRoot = daymetCollection

# Export params
# Whether to export composites
exportComposites = True

#which bands to export
exportBands = ['prcp.*','srad.*','swe.*','tmax.*','tmin.*','vp.*']



####################################################################################################
#End user parameters
####################################################################################################
####################################################################################################
####################################################################################################
#Start function calls
####################################################################################################
####################################################################################################
#Wrapper function to get climate data
# Supports:
# NASA/ORNL/DAYMET_V3
# NASA/ORNL/DAYMET_V4
# UCSB-CHG/CHIRPS/DAILY (precipitation only)
#and possibly others
def getClimateWrapper(collectionName,studyArea,startYear,endYear,startJulian,endJulian,timebuffer,weights,compositingReducer,exportComposites,exportPathRoot,crs,transform,scale,exportBands = None):
  args = formatArgs(locals())
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
  c = ee.ImageCollection(collectionName)\
           .filterBounds(studyArea.bounds())\
           .filterDate(startDate,endDate)\
           .filter(ee.Filter.calendarRange(startJulian,endJulian))

  #Set to appropriate resampling method
  c = c.map(lambda img: img.resample('bicubic'))
  Map.addLayer(c,{},'Raw Climate')

  #Create composite time series
  ts = compositeTimeSeries(c,startYear,endYear,startJulian,endJulian,timebuffer,weights,None,compositingReducer)
  ts = ts.map(lambda i : i.float())

  #Export composite collection
  if exportComposites:
    #Set up export bands if not specified
    if exportBands == None:
      exportBands = ee.List(ee.Image(ts.first()).bandNames())

    exportCollection(exportPathRoot,collectionName.split('/')[2],studyArea, crs,transform,scale,ts,startYear,endYear,startJulian,endJulian,compositingReducer,timebuffer,exportBands)
  
  return ts
####################################################################################################
#Call on wrapper
ts = getClimateWrapper(collectionName,studyArea,startYear,endYear,startJulian,endJulian,timebuffer,weights,compositingReducer,exportComposites,exportPathRoot,crs,transform,scale,exportBands)

Map.addLayer(ee.ImageCollection(ts),{},'Annual Climate Time Series',False)
####################################################################################################
#Load the study region
Map.addLayer(studyArea, {'strokeColor': '0000FF'}, "Study Area", True)
Map.centerObject(studyArea)
####################################################################################################
####################################################################################################
Map.view()