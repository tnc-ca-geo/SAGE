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
#Script to take LandTrendr stack outputs and summarize across iGDEs for training and applying a model
####################################################################################################
from iGDE_lib import *
####################################################################################################
#User params defined in iGDE_lib.py
####################################################################################################
#Function to get an image collection of LandTrendr outputs for all bands to then summarize with iGDE zonal stats (means)
def getLT(ltCollection,ltBands):

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
    fit = simpleLTFit(ltStack,startYear,endYear,indexName).select(ltBands)

    if outC  == None:
      outC = fit
    else:
      outC = ee.ImageCollection(joinCollections(outC,fit))

  Map.addLayer(outC,{},'all fits',True)
  return outC
####################################################################################################
#Function to export model apply tables (tables to predict model across) for each year
def exportApplyTables(years,durFitMagSlope):
  #Iterate across each year to export a table of all iGDEs with zonal mean of LandTrendr outputs
  for yr in years:
    print(yr)
    
    #Get LandTrendr output for that year
    durFitMagSlopeYr = ee.Image(durFitMagSlope.filter(ee.Filter.calendarRange(yr,yr,'year')).first())
   
    #Compute zonal means
    igdesYr = durFitMagSlopeYr.reduceRegions(applyGDEs, ee.Reducer.mean(),scale,crs,transform,4)

    #Set zone field
    igdesYr = igdesYr.map(lambda f:f.set('year',yr))

    #Export table
    yrEnding = '_{}'.format(yr)
    outputName = outputApplyTableName+ yrEnding
    t = ee.batch.Export.table.toAsset(igdesYr, outputName,outputApplyTableDir + '/'+outputName)
    print('Exporting:',outputName)
    t.start()
####################################################################################################
#Wrapper function to export apply tables for a set of years with a set of credentials
def batchExportApplyTables(startApplyYear,endApplyYear,durFitMagSlope):
  sets = new_set_maker(range(startApplyYear,endApplyYear+1),len(tokens))
  for i,years in enumerate(sets):
    initializeFromToken(tokens[i])
    print(ee.String('Token works!').getInfo())
    print(years)
    exportApplyTables(years,durFitMagSlope)
    trackTasks()
####################################################################################################  
def getTrainingTable(startTrainingYear,endTrainingYear,dgwNullValue = -999,maxDGW = 20,minDGW = 0):
  years = range(startTrainingYear,endTrainingYear+1)
  outTraining = []
  for yr in years:
    print(yr)
    #Set up fields to select from training features
    #Will only need the DGW for that year and id
    #Will pull geometry and all other fields from that year's apply table
    yearDGWField = 'Depth{}'.format(yr)
    fromFields = [yearDGWField,'POLYGON_ID','STN_ID']
    toFields = ['dgw','POLYGON_ID','STN_ID']
  
    igdesYr = trainingGDEs.select(fromFields,toFields)
    
    igdesYr = igdesYr.map(lambda f: f.set('dgw',ee.Number(f.get('dgw')).float()))
    #Filter out training igdes for that year
    igdesYr = igdesYr.filter(ee.Filter.neq('dgw',dgwNullValue))
    
    igdesYr = igdesYr.filter(ee.Filter.lte('dgw',maxDGW))
    igdesYr = igdesYr.filter(ee.Filter.gte('dgw',minDGW))
    
    
    #Bring in apply training table to join to to get goemetry and all other fields
    yrEnding = '_{}'.format(yr)
    outputName = outputApplyTableName+ yrEnding
    applyTrainingTableYr = outputApplyTableDir + '/'+outputName
    applyTrainingTableYr = ee.FeatureCollection(applyTrainingTableYr)
    igdesYr = joinFeatureCollectionsReverse(igdesYr,applyTrainingTableYr,'POLYGON_ID')

    outTraining.append(igdesYr)
    
  #Combine all years into a single collection and export
  outTraining = ee.FeatureCollection(outTraining).flatten()
  Map.addLayer(outTraining,{'strokeColor':'F0F','layerType':'geeVectorImage'},'Training Features',False)
  t = ee.batch.Export.table.toAsset(outTraining, outputTrainingTableName,outputTrainingTablePath)
  print('Exporting:',outputTrainingTableName)
  t.start()

####################################################################################################
#Function calls
#Get fitted LT collection
#durFitMagSlope = getLT(ltCollection,ltBands)

#First, export model apply tables
# batchExportApplyTables(startApplyYear,endApplyYear,durFitMagSlope)

#Once apply tables are finished exporting, export model training table
# getTrainingTable(startTrainingYear,endTrainingYear,dgwNullValue,maxDGW,minDGW)

#View map
# Map.view()