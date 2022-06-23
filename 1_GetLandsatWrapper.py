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
#Script to acquire annual Landsat composites using the getImagesLib and view outputs using the Python visualization tools
#Acquires Landsat, masks clouds and cloud shadows, composites, and then adds them to the viewer

####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, taskManagerLib, assetManagerLib
from geeViz.geeView import *

####################################################################################################

#Define user parameters:

# Options defined in SAGE_Initialize:
# Start and end year 
# Julian day range 
# Study Area
# CRS, transform and scale
# Export image collection name
# Whether to export composites or visualize them in geeView

#--------The Following Options Are Default Landsat Compositing Methods and Do Not Need to Be Changed-----------

# Specify an annual buffer to include imagery from the same season 
# timeframe from the prior and following year. timeBuffer = 1 will result 
# in a 3 year moving window. If you want single-year composites, set to 0
timebuffer =0

# Specify the weights to be used for the moving window created by timeBuffer
# For example- if timeBuffer is 1, that is a 3 year moving window
# If the center year is 2000, then the years are 1999,2000, and 2001
# In order to overweight the center year, you could specify the weights as
# [1,5,1] which would duplicate the center year 5 times and increase its weight for
# the compositing method. If timeBuffer = 0, set to [1]
weights = [1]

# Choose medoid or median compositing method. 
# Median tends to be smoother, while medoid retains 
# single date of observation across all bands
# The date of each pixel is stored if medoid is used. This is not done for median
# If not exporting indices with composites to save space, medoid should be used
compositingMethod = 'medoid'

# Choose Top of Atmospheric (TOA) or Surface Reflectance (SR) 
toaOrSR = 'SR'

# Choose whether to include Landat 7
# Generally only included when data are limited
includeSLCOffL7 = True

# Whether to defringe L4 and L5
# Landsat 4 and 5 data have fringes on the edges that can introduce anomalies into 
# the analysis.  This method removes them, but is somewhat computationally expensive
defringeL5 = True

# Choose cloud/cloud shadow masking method
# Choices are a series of booleans for cloudScore, TDOM, and elements of Fmask
# Fmask masking options will run fastest since they're precomputed
# Fmask cloud mask is generally very good, while the fMask cloud shadow
# mask isn't great. TDOM tends to perform better than the Fmask cloud shadow mask. cloudScore 
# is usually about as good as the Fmask cloud mask overall, but each fails in different instances.
# CloudScore runs pretty quickly, but does look at the time series to find areas that 
# always have a high cloudScore to reduce commission errors- this takes some time
# and needs a longer time series (>5 years or so)
# TDOM also looks at the time series and will need a longer time series
# If pre-computed cloudScore offsets and/or TDOM stats are provided below, cloudScore
# and TDOM will run quite quickly
applyCloudScore = False
applyFmaskCloudMask = True

applyTDOM = False
applyFmaskCloudShadowMask = True

applyFmaskSnowMask = True

# If applyCloudScore is set to True
# cloudScoreThresh: lower number masks more clouds.  Between 10 and 30 generally 
# works best
cloudScoreThresh = 20

# Whether to find if an area typically has a high cloudScore
# If an area is always cloudy, this will result in cloud masking omission
# For bright areas that may always have a high cloudScore
# but not actually be cloudy, this will result in a reduction of commission errors
# This procedure needs at least 5 years of data to work well
# Precomputed offsets can be provided below
performCloudScoreOffset = True

# If performCloudScoreOffset = true:
# Percentile of cloud score to pull from time series to represent a minimum for 
# the cloud score over time for a given pixel. Reduces comission errors over 
# cool bright surfaces. Generally between 5 and 10 works well. 0 generally is a
# bit noisy but may be necessary in persistently cloudy areas
cloudScorePctl = 10

# zScoreThresh: If applyTDOM is true, this is the threshold for cloud shadow masking- 
# lower number masks out less. Between -0.8 and -1.2 generally works well
zScoreThresh = -1

# shadowSumThresh:  If applyTDOM is true, sum of IR bands to include as shadows within TDOM and the 
#    shadow shift method (lower number masks out less)
shadowSumThresh = 0.35

# contractPixels: The radius of the number of pixels to contract (negative 
#    buffer) clouds and cloud shadows by. Intended to eliminate smaller cloud 
#    patches that are likely errors
# (1.5 results in a -1 pixel buffer)(0.5 results in a -0 pixel buffer)
# (1.5 or 2.5 generally is sufficient)
contractPixels = 1.5 

# dilatePixels: The radius of the number of pixels to dilate (buffer) clouds 
#    and cloud shadows by. Intended to include edges of clouds/cloud shadows 
#    that are often missed
# (1.5 results in a 1 pixel buffer)(0.5 results in a 0 pixel buffer)
# (2.5 or 3.5 generally is sufficient)
dilatePixels = 2.5

# Choose the resampling method: 'near', 'bilinear', or 'bicubic'
# Defaults to 'near'
# If method other than 'near' is chosen, any map drawn on the fly that is not
# reprojected, will appear blurred
# Use .reproject to view the actual resulting image (this will slow it down)
resampleMethod = 'bicubic'

# If available, bring in preComputed cloudScore offsets and TDOM stats
# Set to null if computing on-the-fly is wanted
# These have been pre-computed for all CONUS for Landsat and Setinel 2 (separately)
# and are appropriate to use for any time period within the growing season
# The cloudScore offset is generally some lower percentile of cloudScores on a pixel-wise basis
preComputedCloudScoreOffset = getImagesLib.getPrecomputedCloudScoreOffsets(cloudScorePctl)['landsat']

# The TDOM stats are the mean and standard deviations of the two IR bands used in TDOM
# By default, TDOM uses the nir and swir1 bands
preComputedTDOMStats = getImagesLib.getPrecomputedTDOMStats()
preComputedTDOMIRMean = preComputedTDOMStats['landsat']['mean']
preComputedTDOMIRStdDev = preComputedTDOMStats['landsat']['stdDev']


# correctIllumination: Choose if you want to correct the illumination using
# Sun-Canopy-Sensor+C correction. Additionally, choose the scale at which the
# correction is calculated in meters.
correctIllumination = False;
correctScale = 250 #Choose a scale to reduce on- 250 generally works well

# Set up Names for the export
outputName = 'Landsat'


####################################################################################################
#                        End User Parameters
####################################################################################################


####################################################################################################
#                     Start Function Calls
####################################################################################################
if not ee.data.getInfo(sage.compositeCollection):
  print('Creating ' + sage.compositeCollection)
  ee.data.createAsset({'type': 'ImageCollection'}, sage.compositeCollection)
  assetManagerLib.updateACL(sage.compositeCollection, all_users_can_read = True)

#Call on master wrapper function to get Landat scenes and composites
lsAndTs = getImagesLib.getLandsatWrapper(**{
  'studyArea': sage.studyArea,
  'startYear': sage.landsatStartYear,
  'endYear': sage.landsatEndYear,
  'startJulian': sage.startJulian,
  'endJulian': sage.endJulian,
  'timebuffer': timebuffer,
  'weights': weights,
  'compositingMethod': compositingMethod,
  'toaOrSR': toaOrSR,
  'includeSLCOffL7': includeSLCOffL7,
  'defringeL5': defringeL5,
  'applyCloudScore': applyCloudScore,
  'applyFmaskCloudMask': applyFmaskCloudMask,
  'applyTDOM': applyTDOM,
  'applyFmaskCloudShadowMask': applyFmaskCloudShadowMask,
  'applyFmaskSnowMask': applyFmaskSnowMask,
  'cloudScoreThresh': cloudScoreThresh,
  'performCloudScoreOffset': performCloudScoreOffset,
  'cloudScorePctl': cloudScorePctl,
  'zScoreThresh': zScoreThresh,
  'shadowSumThresh': shadowSumThresh,
  'contractPixels': contractPixels,
  'dilatePixels': dilatePixels,
  'correctIllumination': correctIllumination,
  'correctScale': correctScale,
  'exportComposites': sage.exportLandsat,
  'outputName': outputName,
  'exportPathRoot': sage.compositeCollection,
  'crs': sage.crs,
  'transform': sage.transform,
  'scale': sage.scale,
  'resampleMethod': resampleMethod,
  'preComputedCloudScoreOffset': preComputedCloudScoreOffset,
  'preComputedTDOMIRMean': preComputedTDOMIRMean,
  'preComputedTDOMIRStdDev': preComputedTDOMIRStdDev})

####################################################################################################
#             Visualize in geeView() if Selected
####################################################################################################
if sage.viewLandsat:
  #Separate into scenes and composites
  processedScenes = lsAndTs['processedScenes']
  processedComposites = lsAndTs['processedComposites']

  Map.addLayer(processedComposites.select(['NDVI','NBR']), {'addToLegend':'false'}, 'Time Series (NBR and NDVI)', False)
  for year in range(sage.landsatStartYear + timebuffer, sage.landsatEndYear + 1 - timebuffer):
       t = processedComposites.filter(ee.Filter.calendarRange(year,year,'year')).mosaic()
       Map.addLayer(t.float(), getImagesLib.vizParamsFalse, str(year), False)

  #Load the study region
  Map.addLayer(sage.studyArea, {'strokeColor': '0000FF'}, "Study Area", True)
  Map.centerObject(sage.studyArea)
  Map.view()
else:
  taskManagerLib.trackTasks()


