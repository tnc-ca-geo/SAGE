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


#Script to take LandTrendr stack outputs and summarize across iGDEs for training and applying a model


####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, changeDetectionLib, taskManagerLib, assetManagerLib
from geeViz.geeView import *

####################################################################################################
#Define user parameters:

# Options defined in SAGE_Initialize:
# Start and end year of training data
# AnnualDGWField (prefix in front of annual DGW values, in training GDEs)
# GDE ID Name (ID attribute for each GDE)
# Well ID Name (ID attribute for each well)
# TrainingGDEs - these are filtered and prepped in SAGE_Initialize
# DGW null, min, and max values
# Input and output paths and naming

####################################################################################################
#                     Prep
####################################################################################################
# If we want to view the output in the viewer, all the input needs to be changed to "all_users_can_read"
# (This can also be done in the playground using the "Share" function).
if sage.viewTrainingTable:

  for applyYear in range(sage.startApplyYear, sage.endApplyYear+1):
    assetManagerLib.updateACL(sage.applyTableDir + '/' + sage.applyTableName + '_' + str(applyYear), all_users_can_read = True)
  assetManagerLib.updateACL(sage.trainingGDECollection, all_users_can_read = True)
  assetManagerLib.updateACL(sage.applyGDECollection, all_users_can_read = True)

# Get initial training GDE collection and filter
trainingGDEs = ee.FeatureCollection(sage.trainingGDECollection)

# Only include GDEs greater than a minimum size.
trainingGDEs = trainingGDEs.filter(ee.Filter.gte(sage.gdeSizeAttribute, sage.minGDESize))

# Only include shallow wells, or some other defining characteristic
if sage.filterWellTypeByAttributeOrValue == 'attribute':
  trainingGDEs = trainingGDEs.filter(ee.Filter.stringContains(sage.wellDepthAttribute, sage.wellDepthFilterName))
elif sage.filterWellTypeByAttributeOrValue == 'value':
  trainingGDEs = trainingGDEs.filter(ee.Filter.And(ee.Filter.gt(sage.wellDepthAttribute, sage.wellDepthMin), ee.Filter.lt(sage.wellDepthAttribute, sage.wellDepthMax)))

# Create a Unique ID for each GDE / well combination
trainingGDEs = trainingGDEs.map(lambda f: f.set('unique_id', f.getNumber(sage.gdeIdName).format().cat('_').cat(f.getNumber(sage.wellIdName).format())))

####################################################################################################
#                     Get Training Table
####################################################################################################
# Since we have overlap between the training GDEs and the apply GDEs (all training GDEs are in the apply GDE collection),
# we just use the predictor tables created for the apply GDEs using 4applyTableExporter.py, and join it with the
# formatted training GDE tables.

years = range(sage.startTrainingYear, sage.endTrainingYear+1)
outTraining = []
for yr in years:
  print(yr)
  #Set up fields to select from training features
  #Will only need the DGW for that year and id
  #Will pull geometry and all other fields from that year's apply table
  yearDGWField = sage.annualDGWField + str(yr)
  fromFields = [yearDGWField, sage.gdeIdName, sage.wellIdName]
  toFields = ['dgw', sage.gdeIdName, sage.wellIdName]

  # get training GDEs for this year
  igdesYr = trainingGDEs.select(fromFields, toFields)
 
  igdesYr = igdesYr.map(lambda f: f.set('dgw',ee.Number(f.get('dgw')).float()))

  # Filter out any null DGW values
  igdesYr = igdesYr.filter(ee.Filter.neq('dgw', sage.dgwNullValue))
  
  # Filter out max and min DGW values
  igdesYr = igdesYr.filter(ee.Filter.lte('dgw', sage.maxDGW))
  igdesYr = igdesYr.filter(ee.Filter.gte('dgw', sage.minDGW))
  
  
  #Bring in apply training table to join to to get geometry and all other fields
  yrEnding = '_{}'.format(yr)
  applyTrainingTableYr = sage.applyTableDir + '/' + sage.applyTableName + yrEnding
  applyTrainingTableYr = ee.FeatureCollection(applyTrainingTableYr)

  # Join the apply Tables with the training GDEs. This will only retain the training GDEs
  igdesYr = sage.joinFeatureCollectionsReverse(igdesYr, applyTrainingTableYr, sage.gdeIdName)

  outTraining.append(igdesYr)
  
#Combine all years into a single collection
outTraining = ee.FeatureCollection(outTraining).flatten()

Map.addLayer(outTraining, {'strokeColor':'F0F'}, 'Training Features', False) #,'layerType':'geeVectorImage'

# Export
t = ee.batch.Export.table.toAsset(**{\
    'collection': outTraining, 
    'description': sage.trainingTableName,
    'assetId': sage.trainingTablePath})

print('Exporting:', sage.trainingTableName)
t.start()

####################################################################################################
#                   Visualize in geeView() if Selected
####################################################################################################
if sage.viewTrainingTable:

  Map.view()

else:

  taskManagerLib.trackTasks()




