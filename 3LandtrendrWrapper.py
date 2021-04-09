#Script to take Landsat and DAYMET composites and run Landtrendr over them
####################################################################################################
from iGDE_lib import *
####################################################################################################
#Define user parameters:

# Specify study area: Study area
# Can be a featureCollection, feature, or geometry
studyArea = California

#Specify years to run LandTrendr over
startYear = 1984
endYear  = 2019

#First piece of the name of the exported images
exportNamePrefix = 'LT_Stack'


# Provide location composites will be exported to
# This should be an asset folder, or more ideally, an asset imageCollection
exportPathRoot = ltCollection

# Export params
# Whether to LandTrendr stack outputs
exportLTStack = True

#Whether to view outputs in geeViz
viewOutputs = True


#Which bands/indices to run LandTrendr across
indexList = ['blue','green','red','nir','swir1','swir2','temp','NBR','NDMI','NDVI','SAVI','EVI','brightness','greenness','wetness','tcAngleBG','tmin_mean','tmax_mean','prcp_mean','srad_mean','vp_mean']

#Number to multiply fitted values by to get into 16 bit data space for exported LandTrendr stack assets
multDict = {'blue':10000,'green':10000,'red':10000,'nir':10000,'swir1':10000,'swir2':10000,'temp':10,'NBR':10000,'NDMI':10000,'NDVI':10000,'SAVI':10000,'EVI':10000,'brightness':10000,'greenness':10000,'wetness':10000,'tcAngleBG':10000,'prcp_mean':100,'tmin_mean':100,'tmax_mean':100,'srad_mean':10,'swe_mean':1, 'vp_mean':10};

#Add change directions for climate bands 
#Direction should be negative if it goes down when vegetation vigor goes down
changeDirDict['prcp_mean'] = -1
changeDirDict['tmin_mean'] = 1
changeDirDict['tmax_mean'] = 1
changeDirDict['swe_mean'] = -1
changeDirDict['vp_mean'] = 1
changeDirDict['srad_mean'] = 1



####################################################################################################
#Bring in composites and DAYMET data
composites = ee.ImageCollection(compositeCollection)\
        .filter(ee.Filter.calendarRange(startYear,endYear,'year'))\
        .map(lambda img: multBands(img,1,[0.0001,0.0001,0.0001,0.0001,0.0001,0.0001,1,1,1,1,1]))\
        .map(simpleAddIndices)\
        .map(getTasseledCap)\
        .map(simpleAddTCAngles)\
        .map(addSAVIandEVI)
daymet = ee.ImageCollection(daymetCollection)\
        .filter(ee.Filter.calendarRange(startYear,endYear,'year'))


#Join collections
joined = ee.ImageCollection(joinCollections(composites,daymet))

# Map.addTimeLapse(composites,vizParamsFalse,'Composites',False)
Map.addLayer(joined,{},'Composites and Daymet Time Series',False)
def batchLTExport(indexList,tokenPath):
  #Define landtrendr params
  run_params = { \
    'maxSegments':            6,\
    'spikeThreshold':         0.9,\
    'vertexCountOvershoot':   3,\
    'preventOneYearRecovery': True,\
    'recoveryThreshold':      0.25,\
    'pvalThreshold':          0.05,\
    'bestModelProportion':    0.75,\
    'minObservationsNeeded':  6\
  }
  for indexName in indexList:
    # lt = landtrendrWrapper(composites,startYear,endYear,indexName,changeDirDict[indexName],run_params,distParams,mmu)
    
    # slt =simpleLANDTRENDR(composites,startYear,endYear,indexName, run_params,lossMagThresh = -0.15,lossSlopeThresh = -0.1,gainMagThresh = 0.1,gainSlopeThresh = 0.1,slowLossDurationThresh = 3,chooseWhichLoss = 'largest',chooseWhichGain = 'largest',addToMap = True,howManyToPull = 2)
    
    prepDict = prepTimeSeriesForLandTrendr(joined, indexName, run_params)
    run_params = prepDict['run_params']
    countMask = prepDict['countMask']

    # Run LANDTRENDR
    rawLt = ee.Algorithms.TemporalSegmentation.LandTrendr(**run_params).select([0])

    #Convert to stack format and flip fitted values back
    ltStack = getLTvertStack(rawLt,run_params)
    ltStack = ee.Image(LT_VT_vertStack_multBands(ltStack, None, changeDirDict[indexName]))
    
    #Get fitted annual values for visualization
    ltC = simpleLTFit(ltStack,startYear,endYear,indexName).select(['.*_fitted'])
    tsJoined = joinCollections(joined.select([indexName]),ltC)

    # Map.addLayer(prepDict['run_params']['timeSeries'],{},'Prepped-'+indexName,False)
    # Map.addLayer(rawLt,{},'Raw LT-'+indexName,True)
    # Map.addLayer(ltStack,{},'vertStack LT-'+indexName,True)
    Map.addLayer(tsJoined,{'opacity':0},'Raw and Fitted '+indexName,True)

    forExport = ee.Image(LT_VT_vertStack_multBands(ltStack, None, multDict[indexName])).int16()

    Map.addLayer(forExport.clip(studyArea),{},'For Export '+indexName,False)

    #Export  stack
    exportName = '{}_{}_{}_{}'.format(exportNamePrefix,indexName, startYear, endYear) 
    
    exportPath = exportPathRoot + '/'+ exportName
    
    #Set up proper resampling for each band
    #Be sure to change if the band names for the exported image change
    pyrObj = {'yrs_vert_':'mode','fit_vert_':'mean'}
    possible = [str(i) for i in range(1,run_params['maxSegments']+2)]

    outObj = {}
    for p in possible:
      for key in pyrObj.keys():

        kt = '{}{}'.format(key,p)
        outObj[kt]= pyrObj[key]

    #Export output
    if exportLTStack:
      exportToAssetWrapper(forExport,exportName,exportPath,outObj,studyArea,scale,crs,transform)
####################################################################################################
if __name__ == '__main__':

  #Call on multi-threaded exporting
  sets = new_set_maker(indexList,len(tokens))
  for i,s in enumerate(sets):
    initializeFromToken(tokens[i])
    print(ee.String('Token works!').getInfo())
    batchLTExport(s,tokens[i])
    # tt = threading.Thread(target = batchLTExport, args = (s,tokens[i]))
    # tt.start()
    # time.sleep(0.1)

  # limitThreads(1)
  ####################################################################################################

  #Load the study region
  Map.addLayer(studyArea, {'strokeColor': '0000FF'}, "Study Area", True)
  Map.centerObject(studyArea)
  ####################################################################################################
  if viewOutputs:
    Map.view()