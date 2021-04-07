#Script to take Landsat and DAYMET composites and run Landtrendr over them
####################################################################################################
from iGDE_lib import *
####################################################################################################
#Define user parameters:
startYear = 1984
endYear  = 2019

indexList = ['vp_mean']#,'prcp_mean']#['blue','green','red','nir','swir1','swir2','temp','NBR','NDMI','NDVI','SAVI','EVI','brightness','greenness','wetness','tcAngleBG','tmin_mean','tmax_mean','prcp_mean']

multDict = {'blue':10000,'green':10000,'red':10000,'nir':10000,'swir1':10000,'swir2':10000,'temp':10,'NBR':10000,'NDMI':10000,'NDVI':10000,'SAVI':10000,'EVI':10000,'brightness':10000,'greenness':10000,'wetness':10000,'tcAngleBG':10000,'prcp_mean':100,'tmin_mean':100,'tmax_mean':100,'srad_mean':10,'swe_mean':1, 'vp_mean':10};

changeDirDict['prcp_mean'] = -1
changeDirDict['tmin_mean'] = 1
changeDirDict['tmax_mean'] = 1
changeDirDict['swe_mean'] = -1
changeDirDict['vp_mean'] = 1
changeDirDict['srad_mean'] = 1
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

####################################################################################################
#Bring in composites and DAYMET data
composites = ee.ImageCollection(compositeCollection)\
        .filter(ee.Filter.eq('startJulian',152))\
        .map(lambda img: multBands(img,1,[0.0001,0.0001,0.0001,0.0001,0.0001,0.0001,1,1,1,1,1]))\
        .map(simpleAddIndices)\
        .map(getTasseledCap)\
        .map(simpleAddTCAngles)\
        .map(addSAVIandEVI)
daymet = ee.ImageCollection(daymetCollection)
daymet = daymet.filter(ee.Filter.stringContains('system:index','V4'))

#Join collections
joined = ee.ImageCollection(joinCollections(composites,daymet))

# Map.addTimeLapse(composites,vizParamsFalse,'Composites',False)
Map.addLayer(joined,{},'Composites and Daymet Time Series',False)
for indexName in indexList:
  # lt = landtrendrWrapper(composites,startYear,endYear,indexName,changeDirDict[indexName],run_params,distParams,mmu)
  
  # slt =simpleLANDTRENDR(composites,startYear,endYear,indexName, run_params,lossMagThresh = -0.15,lossSlopeThresh = -0.1,gainMagThresh = 0.1,gainSlopeThresh = 0.1,slowLossDurationThresh = 3,chooseWhichLoss = 'largest',chooseWhichGain = 'largest',addToMap = True,howManyToPull = 2)
  
  prepDict = prepTimeSeriesForLandTrendr(joined, indexName, run_params)
  run_params = prepDict['run_params']
  countMask = prepDict['countMask']

  # Run LANDTRENDR
  rawLt = ee.Algorithms.TemporalSegmentation.LandTrendr(**run_params).select([0])

  ltStack = getLTvertStack(rawLt,run_params)

  
  ltC = simpleLTFit(ltStack,startYear,endYear,indexName).select(['.*_fitted'])
  tsJoined = joinCollections(joined.select([indexName]),ltC)

  # Map.addLayer(prepDict['run_params']['timeSeries'],{},'Prepped-'+indexName,False)
  # Map.addLayer(rawLt,{},'Raw LT-'+indexName,True)
  # Map.addLayer(ltStack,{},'vertStack LT-'+indexName,True)
  Map.addLayer(tsJoined,{},'Fit C LT-'+indexName,True)

  forExport = ee.Image(LT_VT_vertStack_multBands(ltStack, None, multDict[indexName])).int16()
  print(forExport.bandNames().getInfo())
  # Map.addLayer(forExport,{},'forExport-'+indexName)

  #Export  stack
  # exportName = outputName + '_Stack_'+indexName + '_'+str(startYear) + '_' + str(endYear) + '_' + str(startJulian) + '_' + str(endJulian)
  # exportPath = exportPathRoot + '/'+ exportName

  #Set up proper resampling for each band
  #Be sure to change if the band names for the exported image change
  # pyrObj = {'_yr_':'mode','_dur_':'mode','_mag_':'mean','_slope_':'mean'}
  # possible = ['loss','gain']
  # how_many_list = ee.List.sequence(1,howManyToPull).getInfo()
  # outObj = {}
  # for p in possible:
  #   for key in pyrObj.keys():
  #     for i in how_many_list:
  #       i = int(i)
  #       kt = indexName + '_LT_'+p + key+str(i)
  #       outObj[kt]= pyrObj[key]

  
  # #Export output
  # exportToAssetWrapper(ltOutStack,exportName,exportPath,outObj,studyArea,scale,crs,transform)


####################################################################################################
Map.view()