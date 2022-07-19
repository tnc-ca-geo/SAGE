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


#Script to take LandTrendr stack outputs and summarize across iGDEs to create tables with zonal summaries of landtrendr outputs for all apply GDEs


####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, changeDetectionLib, taskManagerLib
from geeViz.geeView import *
import pdb
####################################################################################################
#Define user parameters:

# Options defined in SAGE_Initialize:
# Start and end year 
# Study Area
# CRS, transform and scale
# Export image collection name
# Whether to export composites or visualize them in geeView

####################################################################################################
#                     Define Functions
####################################################################################################
#Function to get an image collection of LandTrendr outputs for all bands to then summarize with iGDE zonal stats (means)
def getLT(ltCollection, ltBands):

  #Bring in LandTrendr collectino
  c = ee.ImageCollection(ltCollection)

  #Get the IDs of LandTrendr bands/indices runs
  ids = c.aggregate_array('system:index').getInfo()
  outC = None

  #Iterate across each ID and convert LandTrendr stack to a collection
  for id in ids:
    startYear = int(id.split('_')[-2])
    endYear = int(id.split('_')[-1])
    indexName = id.split('_{}_'.format(startYear))[0].split('Stack_')[1]
    
    ltStack = c.filter(ee.Filter.eq('system:index',id)).first()
    fit = changeDetectionLib.simpleLTFit(ltStack, startYear, endYear, indexName).select(ltBands)

    if outC == None:
      outC = fit
    else:
      outC = ee.ImageCollection(getImagesLib.joinCollections(outC, fit))

  return outC

  # Make sure all our predictors are numbers, not strings
def formatPredictors(applyGDEs):
  predictors = [i for i in sage.predictors if i in applyGDEs.first().propertyNames().getInfo()]
  firstFeatureProperties = applyGDEs.first().getInfo()['properties']
  for predictorName in predictors:
    if type(firstFeatureProperties[predictorName]) == str:
      print('Formatting '+predictorName+' to String')
      groups = ee.Dictionary(applyGDEs.aggregate_histogram(predictorName))
      names = ee.List(groups.keys())
      numbers = ee.List.sequence(1,names.length())
      applyGDEs = applyGDEs.map(lambda f: f.set(predictorName+'_String', f.get(predictorName)))
      applyGDEs = applyGDEs.remap(names, numbers, predictorName)

  return applyGDEs

#Function to export model apply tables (tables to predict model across) for each year
def exportApplyTables(years, durFitMagSlope, applyGDEs, applyTableDir, applyTableName):
  #Iterate across each year to export a table of all iGDEs with zonal mean of LandTrendr outputs
  for yr in years:
    print(yr)
    
    #Get LandTrendr output for that year
    durFitMagSlopeYr = ee.Image(durFitMagSlope.filter(ee.Filter.calendarRange(yr,yr,'year')).first())
   
    #Compute zonal means
    igdesYr = durFitMagSlopeYr.reduceRegions(applyGDEs, ee.Reducer.mean(), sage.scale, sage.crs, sage.transform, 4)

    #Set zone field
    igdesYr = igdesYr.map(lambda f: f.set('year',yr))

    #Export table
    yrEnding = '_{}'.format(yr)
    outputName = applyTableName + yrEnding
    t = ee.batch.Export.table.toAsset(**{\
      'collection': igdesYr, 
      'description': outputName,
      'assetId': applyTableDir + '/' + outputName})

    print('Exporting:',outputName)
    t.start()


####################################################################################################
#                   Prep
####################################################################################################
#Bring in apply gdes (all igdes)
applyGDEs = ee.FeatureCollection(sage.applyGDECollection)
# Only include GDEs greater than a minimum size.
applyGDEs = applyGDEs.filter(ee.Filter.gte(sage.gdeSizeAttribute, sage.minGDESize))
# Union multi-geometries
applyGDEs = applyGDEs.map(lambda f: ee.Feature(f).dissolve(100))

# Add strata (static predictor layers) to applyGDEs
applyGDEs = sage.addStrata(applyGDEs, sage.vectorStrataToAdd, sage.rasterStrataToAdd)

# Make sure we aren't using strings in our predictor variables as this will make the model fail.
applyGDEs = formatPredictors(applyGDEs)

####################################################################################################
#                   Get Apply Tables
####################################################################################################

#Get fitted LT collection
durFitMagSlope = getLT(sage.ltCollection, sage.ltBands)

####################################################################################################
#                   Export
####################################################################################################

if sage.applyTablesUseMultiCredentials:

  sets = sage.new_set_maker(range(sage.startApplyYear, sage.endApplyYear+1), len(sage.tokens))
  for i, years in enumerate(sets):
    sage.initializeFromToken(sage.tokens[i])
    print(ee.String('Token works!').getInfo())
    print(years)
    exportApplyTables(**{\
      'years': years, 
      'durFitMagSlope': durFitMagSlope, 
      'applyGDEs': applyGDEs, 
      'applyTableDir': sage.applyTableDir,
      'applyTableName': sage.applyTableName})
    sage.shortTrackTasks()

else:

    exportApplyTables(**{\
      'years': range(sage.startApplyYear, sage.endApplyYear+1), 
      'durFitMagSlope': durFitMagSlope, 
      'applyGDEs': applyGDEs, 
      'applyTableDir': sage.applyTableDir,
      'applyTableName': sage.applyTableName})

taskManagerLib.trackTasks()

