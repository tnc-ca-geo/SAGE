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


#Script to take Landsat and DAYMET composites and run Landtrendr over them


####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, changeDetectionLib, taskManagerLib, assetManagerLib
from geeViz.geeView import *
import pdb

####################################################################################################
#Define user parameters:

# Options defined in SAGE_Initialize:
# Start and end year 
# Study Area
# CRS, transform and scale
# Daymet Collection
# Landsat Collection
# Export image collection name
# Whether to export LandTrendr Outputs or visualize them in geeView

#--------The Following Options Are Default LandTrendr Methods and Do Not Need to Be Changed-----------
#Define user parameters:

#First piece of the name of the exported images
exportNamePrefix = 'LT_Stack'

#Number to multiply fitted values by to get into 16 bit data space for exported LandTrendr stack assets
multDict = {'blue':10000,'green':10000,'red':10000,'nir':10000,'swir1':10000,'swir2':10000,'temp':10,'NBR':10000,'NDMI':10000,'NDVI':10000,'SAVI':10000,'EVI':10000,'brightness':10000,'greenness':10000,'wetness':10000,'tcAngleBG':10000,'prcp_mean':100,'tmin_mean':100,'tmax_mean':100,'srad_mean':10,'swe_mean':1, 'vp_mean':10};

#Add change directions for climate bands 
#Direction should be negative if it goes down when vegetation vigor goes down
#changeDirDict = getImagesLib.changeDirDict.copy()
getImagesLib.changeDirDict['prcp_mean'] = -1
getImagesLib.changeDirDict['tmin_mean'] = 1
getImagesLib.changeDirDict['tmax_mean'] = 1
getImagesLib.changeDirDict['swe_mean'] = -1
getImagesLib.changeDirDict['vp_mean'] = 1
getImagesLib.changeDirDict['srad_mean'] = 1

####################################################################################################
#                        End User Parameters
####################################################################################################

####################################################################################################
#                     Define Functions
####################################################################################################

def batchLTExport(\
  inputCollection, 
  indexList, 
  exportPathRoot, 
  exportNamePrefix):


  for indexName in indexList:

    prepDict = changeDetectionLib.prepTimeSeriesForLandTrendr(inputCollection, indexName, sage.landtrendr_run_params)
    run_params = prepDict['run_params']
    countMask = prepDict['countMask']

    # Run LANDTRENDR
    rawLt = ee.Algorithms.TemporalSegmentation.LandTrendr(**run_params).select([0])

    #Convert to stack format and flip fitted values back
    ltStack = changeDetectionLib.getLTvertStack(rawLt,run_params)
    ltStack = ee.Image(changeDetectionLib.LT_VT_vertStack_multBands(ltStack, None, getImagesLib.changeDirDict[indexName]))
    
    #Get fitted annual values for visualization
    ltC = changeDetectionLib.simpleLTFit(ltStack, sage.landtrendrStartYear, sage.landtrendrEndYear, indexName).select(['.*_fitted'])
    tsJoined = getImagesLib.joinCollections(joined.select([indexName]), ltC)

    # Map.addLayer(prepDict['run_params']['timeSeries'],{},'Prepped-'+indexName,False)
    # Map.addLayer(rawLt,{},'Raw LT-'+indexName,True)
    # Map.addLayer(ltStack,{},'vertStack LT-'+indexName,True)
    Map.addLayer(tsJoined, {'opacity':0}, 'Raw and Fitted '+indexName, False)

    forExport = ee.Image(changeDetectionLib.LT_VT_vertStack_multBands(ltStack, None, multDict[indexName])).int16()

    Map.addLayer(forExport.clip(sage.studyArea), {}, 'For Export '+indexName, False)

    #Export stack
    exportName = '{}_{}_{}_{}'.format(exportNamePrefix, indexName, sage.landtrendrStartYear, sage.landtrendrEndYear) 
    
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
    if sage.exportLandtrendrStack:
      getImagesLib.exportToAssetWrapper(**{\
        'imageForExport': forExport,
        'assetName': exportName,
        'assetPath': exportPath,
        'pyramidingPolicyObject': outObj,
        'roi': sage.studyArea,
        'scale': sage.scale,
        'crs': sage.crs,
        'transform': sage.transform})
      

####################################################################################################
#               Bring in composites and DAYMET data
####################################################################################################
if not ee.data.getInfo(sage.ltCollection):
  print('Creating ' + sage.ltCollection)
  ee.data.createAsset({'type': 'ImageCollection'}, sage.ltCollection)
  assetManagerLib.updateACL(sage.ltCollection, all_users_can_read = True)

composites = ee.ImageCollection(sage.compositeCollection)\
        .filter(ee.Filter.calendarRange(sage.landtrendrStartYear, sage.landtrendrEndYear, 'year'))\
        .map(lambda img: changeDetectionLib.multBands(img,1,[0.0001,0.0001,0.0001,0.0001,0.0001,0.0001,1,1,1,1,1]))\
        .map(getImagesLib.simpleAddIndices)\
        .map(getImagesLib.getTasseledCap)\
        .map(getImagesLib.simpleAddTCAngles)\
        .map(getImagesLib.addSAVIandEVI)
daymet = ee.ImageCollection(sage.daymetCollection)\
        .filter(ee.Filter.calendarRange(sage.landtrendrStartYear, sage.landtrendrEndYear,'year'))

#Join collections
joined = ee.ImageCollection(getImagesLib.joinCollections(composites,daymet))

# Map.addTimeLapse(composites,vizParamsFalse,'Composites',False)
Map.addLayer(joined, {}, 'Composites and Daymet Time Series', False)

####################################################################################################
#                   Export
####################################################################################################
if sage.landtrendrUseMultiCredentials:
  
  if __name__ == '__main__':      
      #Call on multi-threaded exporting to split up indices into even batches to export by each credential
      sets = sage.new_set_maker(sage.landtrendrIndexList, len(sage.tokens))
      for i, indexSet in enumerate(sets):
        sage.initializeFromToken(sage.tokens[i])
        print(ee.String('Token works!').getInfo())
        batchLTExport(**{\
          'inputCollection': joined, 
          'indexList': indexSet, 
          'exportPathRoot': sage.ltCollection, 
          'exportNamePrefix': exportNamePrefix})
        sage.shortTrackTasks()
        
else:

  sage.initializeFromToken(sage.tokens[0])
  batchLTExport(**{\
    'inputCollection': joined, 
    'indexList': sage.landtrendrIndexList, 
    'exportPathRoot': sage.ltCollection, 
    'exportNamePrefix': exportNamePrefix})

    
####################################################################################################
#             Visualize in geeView() if Selected
####################################################################################################
if sage.viewLandTrendr:
  #Load the study region
  Map.addLayer(sage.studyArea, {'strokeColor': '0000FF'}, "Study Area", True)
  Map.centerObject(sage.studyArea)

  Map.view()

else:
  print('Tasks for Current Token: ')
  taskManagerLib.trackTasks()



