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

####################################################################################################
#Library containing globals for entire SAGE monitoring processing framework
####################################################################################################
#Module imports
import threading, time, glob, json, pdb, ee, os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
ee.Initialize()

####################################################################################################
#Define user parameters:

#-------------------------------------------------
#				GEE Credentials
#-------------------------------------------------
# These are used for Multi-Credential Exporting
# If you don't have more than one GEE credential to use, you can ignore this.
token_dir = os.path.dirname(ee.oauth.get_credentials_path())
# tokens can either be 'All' or a list of token names
tokens = ['credentialsLC', 'credentialsRCR1'] #'All'
if tokens == 'All':
	tokens = glob.glob(os.path.join(token_dir,'*'))
else:
	tokens = [os.path.join(token_dir, i) for i in tokens]

#-------------------------------------------------
#			Study Area, Years, and CRS/Transform/Scale
#-------------------------------------------------
# Specify study area: Study area
# Can be a featureCollection, feature, geometry, or state name
studyArea = 'California'

# CRS- must be provided.  
# Common crs codes: Web mercator is EPSG:4326, USGS Albers is EPSG:5070, 
# WGS84 UTM N hemisphere is EPSG:326+ zone number (zone 12 N would be EPSG:32612) and S hemisphere is EPSG:327+ zone number
crs = 'EPSG:5070'

# Specify transform if scale is null and snapping to known grid is needed
transform = [30,0,-2361915.0,0,-30,3177735.0]

# Specify scale if transform is null
scale = None

#Specify training and model application years
startTrainingYear = 1985 # First year of training data (i.e. depth to groundwater observations AND Landsat observations. Earliest year for Landsat = 1985)
endTrainingYear = 2018 # Last year of training data
startApplyYear = 1985 # First year to predict depth to groundwater (must have Landsat available, so minimum year = 1985)
endApplyYear = 2021 # Last year to predict depth to groundwater (latest full summer season)


#-------------------------------------------------
#				Global: Paths and Naming
#-------------------------------------------------
runname = 'sage-test'

#----Input Data----
# Apply GDEs. This is your master collection of GDEs that you want to apply the model to.
applyGDECollection = 'projects/ee-contour-tnc/assets/sage/input-data/Apply_GDEs'
# Training GDEs. This a subset of the applyGDECollection and should have annual observations of depth to groundwater already added to them and be filtered to 
# remove GDEs with no groundwater observations.
# There may be multiple wells within a km of one GDE polygon. A separate feature should be made for each well/GDE combination.
trainingGDECollection = 'projects/ee-contour-tnc/assets/sage/input-data/Training_GDEs'

#----Output & Intermediate Steps-----
# Save all SAGE output to this folder. The code will create the appropriate subfolders.
rootFolder = 'projects/ee-contour-tnc/assets/sage'

# Predictor image collections
rasterDataRoot = rootFolder + '/Raster-Data'
daymetCollection = rasterDataRoot + '/DAYMET-Collection' # Where to save Daymet annual composites
compositeCollection = rasterDataRoot + '/Landsat-Collection' # Where to save Landsat annual composites
ltCollection = rasterDataRoot + '/LandTrendr-Collection' # Where to save LandTrendr outputs of Daymet and Landsat (will be saved together)

# Training Tables
tableRoot = rootFolder + '/Tables'
trainingTableDir = tableRoot + '/Training-Tables' # Where to save training tables, i.e. annual tables of predictor observations for each GDE used for training
trainingTableName = 'Training_Table_{}_{}'.format(startTrainingYear, endTrainingYear) # Prefix for training tables. .
trainingTablePath = trainingTableDir + '/' + trainingTableName

# Apply Tables
applyTableDir = tableRoot + '/Apply-Tables' # Where to save the tables of predictor observations for each GDE you're going to apply the model on
applyTableName = 'Apply_Table'

# Prediction Tables
predTableDir = tableRoot + '/RF-Results-Tables' # Where to save the tables of predicted depth to groundwater for each GDE
predTableNameStart = 'Pred_Table'

# Export Path in Google Drive
outputPredDriveDir = 'RF-Pred-'+runname

# Local Folder where to save Model Information
outputLocalRFModelInfoDir = '/Users/leahcampbell/home/contour/tnc/gdepulse/sage_methods'


#-------------------------------------------------
#				Predictor Layer Options
#-------------------------------------------------
#--------------------Landsat Composites (1_GetLandsatWrapper.py)------------------------

# Update the startJulian and endJulian variables to indicate your seasonal 
# constraints. This supports wrapping for tropics and southern hemisphere.
# If using wrapping and the majority of the days occur in the second year, the system:time_start will default 
# to June 1 of that year.Otherwise, all system:time_starts will default to June 1 of the given year
# startJulian: Starting Julian date 
# endJulian: Ending Julian date
startJulian = 152
endJulian = 273

# Specify start and end years for all analyses
# More than a 3 year span should be provided for time series methods to work 
# well. If providing pre-computed stats for cloudScore and TDOM, this does not 
# matter
landsatStartYear = min(startApplyYear, startTrainingYear)
landsatEndYear = max(endApplyYear, endTrainingYear)

exportLandsat = True # Export Landsat composites to asset.
viewLandsat = False # Can visualize Landsat composites in geeView()

# There are additional options listed in getLandsatWrapper.py
# You should not need to change them unless you would like to change the details of the
# compositing methods.

#--------------------Daymet Composites (2_GetClimateWrapper.py)------------------------
# Specify collection to use (V3 or V4)
daymetInputCollection = 'NASA/ORNL/DAYMET_V4'

# Daymet years are the water year (Oct 1 to Oct 1). We call the 2003-2004 water year "2004" when aligning it with Landsat composites,
# but we need to start with 2003 here, hence we subtract 1 from the years we would expect here:
daymetStartYear = min(startApplyYear, startTrainingYear) - 1
daymetEndYear = max(endApplyYear, endTrainingYear) - 1

exportDaymet = True # Export Daymet composites to asset
viewDaymet = False # Can visualize Daymet composites in geeView()

# Which fields to export
daymetExportBands = ['prcp.*','srad.*','swe.*','tmax.*','tmin.*','vp.*']


#--------------------LandTrendr (3_LandtrendrWrapper.py)------------------------
#Specify years to run LandTrendr over
landtrendrStartYear = landsatStartYear
landtrendrEndYear  = landsatEndYear

# Whether to Export LandTrendr stack outputs
exportLandtrendrStack = True

#Whether to view outputs in geeViz
viewLandTrendr = False

# If you have more than one GEE credential available to you, this will automatically run the exports using multiple tokens
# Credentials are usually stored in a hidden folder called '.config/earthengine' in your home directory (on both Mac and PC)
# Credentials to use are defined above as the "tokens" variable
landtrendrUseMultiCredentials = False

#Which bands/indices (Landsat and Daymet) to run LandTrendr across
landtrendrIndexList = ['blue','green','red','nir','swir1','swir2','temp','NBR','NDMI','NDVI','SAVI','EVI','brightness','greenness','wetness','tcAngleBG','tmin_mean','tmax_mean','prcp_mean','srad_mean','vp_mean']

# Define parameters for the LandTrendr algorithm. You should not need to change these options, but you can find more information about each
# option in the GEE ee.Algorithms.TemporalSegmentation.LandTrendr() documentation.
landtrendr_run_params = { \
	'maxSegments':            6, # Maximum number of segments to be fitted on the time series.
	'spikeThreshold':         0.9, # Threshold for dampening the spikes (1.0 means no dampening).
	'vertexCountOvershoot':   3, # The initial model can overshoot the maxSegments + 1 vertices by this amount. Later, it will be pruned down to maxSegments + 1.
	'preventOneYearRecovery': True, # Prevent segments that represent one year recoveries.
	'recoveryThreshold':      0.25, # If a segment has a recovery rate faster than 1/recoveryThreshold (in years), then the segment is disallowed.
	'pvalThreshold':          0.05, # If the p-value of the fitted model exceeds this threshold, then the current model is discarded and another one is fitted using the Levenberg-Marquardt optimizer.
	'bestModelProportion':    0.75, # Allows models with more vertices to be chosen if their p-value is no more than (2 - bestModelProportion) times the p-value of the best model.
	'minObservationsNeeded':  6, # Min observations needed to perform output fitting.
}


#-------------------------------------------------
#				Training and Apply Data Options
#-------------------------------------------------
# !!!! All Depth to Groundwater Values should be POSITIVE, reflecting the absolute value of the depth below surface !!!!!!!!!!!!

#Specify parameters to filter well data for modeling (the min and max DGW should be positive, reflecting the absolute value of the depth below surface)
minDGW = 0 # Minimum depth to groundwater
maxDGW = 20 # Maximum depth to groundwater
dgwNullValue = -999.0 # How are null depth to groundwater values saved in the GDE polygons?

# SAGE is built to be applied on shallow wells only. We filter out any well that is not a shallow perf. well. 
# The attribute name for this in the California dataset is "Depth_Str",
# and we filter to include only "Shallow: perf." wells.
# Some datasets just have a constant "well depth" attribute instead, so there is the option to filter by a min and max value OR by an attribute string.
# Option to filter by an attribute as described above ('attribute') or by a well depth value ('value'):
filterWellTypeByAttributeOrValue = 'attribute'
if filterWellTypeByAttributeOrValue == 'attribute':
	wellDepthAttribute = 'Depth_Str' # the name of the attribute we use to find the right kind of well
	wellDepthFilterName = 'Shallow: perf.' # the name of the kind of well we want.
elif filterWellTypeByAttributeOrValue == 'value':
	wellDepthAttribute = 'Well_Depth' # this is not the annual depth to groundwater value, this is the well depth, which is constant.
	# The default values here assume that your well depth attribute is positive. If it is negative, use negative values for your thresholds.
	wellDepthMin = 0 # min depth below ground we will keep
	wellDepthMax = 100 # max depth below ground we will keep

# Parameters for filtering GDEs
minGDESize = 900 # Minimum size of GDE polygon (m2)
gdeSizeAttribute = 'Shape_Area' # Name of the area (m2) attribute in the GDE polygons

# In Training GDEs, GDE ID Attribute Name and Well ID Attribute Name - will combine to create specific GDE/Well combination identifiers
gdeIdName = 'POLYGON_ID'
wellIdName = 'STN_ID'

# Prefix for the annual depth attribute in each GDE. Should be followed by the year with no spaces.
annualDGWField = 'Depth'

#--------------------Apply Tables (4_ApplyTableExporter.py)------------------------
# If you have more than one GEE credential available to you, this will automatically run the exports using multiple tokens
# Credentials are usually stored in a hidden folder called '.config/earthengine' in your home directory (on both Mac and PC)
# Credentials to use are defined above as the "tokens" variable
applyTablesUseMultiCredentials = False

# Choose which bands from LandTrendr to summarize when making training tables. If you are unsure which bands you will want to include in the model, err on the side of too many.
# Options are '.*_fitted','.*_mag','.*_diff','.*_dur','.*_slope'
ltBands = ['.*_fitted','.*_mag','.*_diff']

# Here you can list any additional predictor layers/ strata that you want to add to your GDEs.
# Any layer should be uploaded to GEE.
# These layers are separated by format (raster vs. vector) below.
# Each entry in the list should be a dictionary with the format:
# {assetName: 'Full path to asset',
#  assetAttributes: 'Name(s) of the attributes (if vector) or band name (if raster). Should be list format even if there is only one.',
#  gdeAttributes: 'What to call these attributes in the GDE (can be the same as assetAttribute). Should be list format even if there is only one.'}
rasterStrataToAdd = []
vectorStrataToAdd = [\
	{'assetName': 'projects/ee-contour-tnc/assets/sage/input-data/Static-Predictor-Layers/Ecoregion_Biome_CA_2020',
		'assetAttributes': ['BIOME','EAA_ID'],
		'gdeAttributes': ['Biome_Number','Ecoregion_Number']},
	{'assetName': 'projects/ee-contour-tnc/assets/sage/input-data/Static-Predictor-Layers/Hydrologic_Regions',
		'assetAttributes': ['OBJECTID'],
		'gdeAttributes': ['Hydroregion_Number']},
	{'assetName': 'projects/ee-contour-tnc/assets/sage/input-data/Static-Predictor-Layers/CA_Bulletin_118_Groundwater_Basins',
		'assetAttributes': ['OBJECTID'],
		'gdeAttributes': ['Groundwater_Basin_ID']},
	{'assetName': 'USGS/WBD/2017/HUC08',
		'assetAttributes': ['huc8'],
		'gdeAttributes': ['HUC08']},
]


#--------------------Training Table (5_TrainingTableExporter.py)------------------------

viewTrainingTable = False


#-------------------------------------------------
#				Modeling Options
#-------------------------------------------------
#--------------------Modeling Options (6_ModelFitApply.py)------------------------

# Which properties to use as predictors in the model
# Aside from the LandTrendr properties (e.g., .*_fitted'), these should all be property names that are added to each GDE 
# using the rasterStrataToAdd and vectorStrataToAdd variables above,
# or are already properties in the apply GDE collection 
# '.*_fitted' and '.*_mag' refer to the fitted values and magnitude of change from LandTrendr segments of both Landsat and Daymet
# Other possible LandTrendr outputs include: '.*_fitted','.*_mag','.*_diff','.*_dur','.*_slope',
# **but any option you choose must be also be in the ltBands variable above**.
# 'huc8','Ecoregion_Number', and 'Biome_Number' are automatically added for any GDE in the US.
# 'Macrogroup_Number' and 'Hydroregion_Number' are from California-specific datasets (macrogroup was added to the California set of GDEs)
predictors = ['.*_fitted','.*_mag','HUC08','Ecoregion_Number','Biome_Number','Macrogroup','Hydroregion_Number'] 

# Runs of models to iterate across
# Specify a descriptive name and then the selectors of the predictor fields
# For a normal run, just leave this as-is. If you want to efficiently run several iterations of the model with different predictor variables,
# this can be useful.
modelRuns = [[runname, predictors],
	# ['climate',['.*mean_LT_fitted','.*mean_LT_mag']], # example of a different run
]

# If you have more than one GEE credential available to you, this will automatically run the exports using multiple tokens
# Credentials are usually stored in a hidden folder called '.config/earthengine' in your home directory (on both Mac and PC)
# Credentials to use are defined above as the "tokens" variable
modelApplyUseMultiCredentials = False

randomForestParameters = {
	'numberOfTrees': 90, # The number of decision trees to create.
	'variablesPerSplit': None, # The number of variables per split. If unspecified, uses the square root of the number of variables.
	'minLeafPopulation': 1, # Only create nodes whose training set contains at least this many points.
	'bagFraction': 0.5, # The fraction of input to bag per tree.
	'maxNodes': None, # The maximum number of leaf nodes in each tree. If unspecified, defaults to no limit.
	'seed': 0, # The randomization seed.
}


#--------------------Download to Outputs to Google Drive (7_DownloadOutputs.py)------------------------

# When exporting CSVs of output to Drive, should we remove the geometry of each GDE polygon?
# This saves a significant amount of time if only using the tables in CSV format
# Really the only reason to keep them is if you anticipate re-importing the table into GEE
removeGeometry = True

# If there are other strata that you want to keep for analysis that were not included as predictor variables, you can add them in here. 
# This will not necessarily be used.
# These should be in the same format as rasterStrataToAdd and vectorStrataToAdd, above in the Apply Tables section
exportRasterStrataToAdd = []
exportVectorStrataToAdd = []
# example format:
# exportVectorStrataToAdd = [\
# 	{'assetName': 'projects/ee-contour-tnc/assets/sage/input-data/Static-Predictor-Layers/CA_Bulletin_118_Groundwater_Basins',
# 		'assetAttributes': ['OBJECTID'],
# 		'gdeAttributes': ['Groundwater_Basin_ID']},
# ]

#--------------------Summarize Trends (8_TrendSummaries.py)------------------------
#Directory containing exported modeled DGW tables
table_dir = '/Users/leahcampbell/home/contour/tnc/gdepulse/sage_methods/sage-test/rf-prediction-tables'

#Directory for output pickles and csv tables to go
summary_table_dir = '/Users/leahcampbell/home/contour/tnc/gdepulse/sage_methods/sage-test'

# Whether to show a couple example linear fit plots using plt.show()
showExamplePlots = True

# These are start and end year pairs for time periods within which we evaluate trends.
year_sets =[[2016,2021]]   #[[1985,2019],[1985,2002],[2003,2019]] #

# Formatting for the final output table. 
# Specify which columns to keep from the original table
keep_columns = ['POLYGON_ID','matchesN','matchesReduced','Hydroregion_Number','Groundwater_Basin_ID']
# Which columns to keep from the OLS output
column_names = ['POLYGON_ID','matchesN','matchesReduced','Hydroregion_Number','Groundwater_Basin_ID','N','StartYear','EndYear','Years','Preds','Training_DGW','OLS_Intercept','OLS_Slope','OLS_Pvalue','OLS_SigDir']

#************ Should not need to modify below this line *************************


####################################################################################################
#							Functions
###################################################################################################
# Functions used here and in other SAGE scripts


def spatialJoin(f1,f2,properties):
	#Define a spatial filter as geometries that intersect.
	spatialFilter = ee.Filter.intersects(
    leftField='.geo',\
    rightField='.geo',\
    maxError=10\
  	)
  
	#Define a save all join.
	saveAllJoin = ee.Join.saveAll(\
    	matchesKey= 'matches'\
  	)
  
 	#Apply the join.
	intersectJoined = saveAllJoin.apply(f1, f2, spatialFilter)

	def joinWrapper(f):
		props = ee.Feature(ee.List(f.get('matches')).get(0))
		f = ee.Feature(f).copyProperties(props,properties)
		propNames = ee.List(f.propertyNames())
		propNames = propNames.removeAll(['matches'])
		return ee.Feature(f).select(propNames)
	out = intersectJoined.map(joinWrapper)
	return out

def innerOuterJoin(primary,secondary,matchFieldName,propertyName,reducer):
	def wrapper(f):
		f = ee.Feature(f)
		name = f.get(matchFieldName)
		secondaryT = secondary.filter(ee.Filter.eq(matchFieldName,name))
		matchesN = secondaryT.size()
		values = ee.Array(secondaryT.toList(10000000).map(lambda f: ee.Feature(f).get(propertyName))).reduce(reducer,[0])
		values = ee.Number(values.toList().get(0))
		values = ee.Algorithms.If(matchesN.gt(0),values,-9999)
		f = f.setMulti({'matchesReduced':values,'matchesN':matchesN})
		return f
	joined = primary.map(lambda f:wrapper(f))
	return joined;

def joinFeatureCollectionsReverse(primary,secondary,fieldName):
	#Use an equals filter to specify how the collections match.
	f = ee.Filter.equals(\
    leftField=fieldName,\
    rightField=fieldName\
  	)
  
	#Define the join.
	innerJoin = ee.Join.inner('primary', 'secondary')
  
	#Apply the join.
	joined = innerJoin.apply(primary, secondary, f)

	def wrapper(f):
		p = ee.Feature(f.get('primary'))
		s = ee.Feature(f.get('secondary'))
		return s.copyProperties(p)
	joined = joined.map(wrapper)
	return joined



#Function to initialize from specified token
#Does not un-initialize any existing initializations, but will point to this set of credentials    
def initializeFromToken(token_path_name):
    print('Initializing GEE using:',token_path_name)
    refresh_token = json.load(open(token_path_name))['refresh_token']
    c = Credentials(
          None,
          refresh_token=refresh_token,
          token_uri=ee.oauth.TOKEN_URI,
          client_id=ee.oauth.CLIENT_ID,
          client_secret=ee.oauth.CLIENT_SECRET,
          scopes=ee.oauth.SCOPES)
    ee.Initialize(c)

def limitThreads(limit):
  while threading.activeCount() > limit:
    time.sleep(1)
    print(threading.activeCount(),'threads running')

def new_set_maker(in_list,threads):

    print (threads)
    out_sets =[]
    for t in range(threads):
        out_sets.append([])
    i =0
    for il in in_list:

        out_sets[i].append(il)
        i += 1
        if i >= threads:
            i = 0
    return out_sets

# Function to get static predictor layers
# vectorStrataToAdd and rasterStrataToAdd must be lists of dictionaries, as explained above in the
# Apply Tables section.
def addStrata(applyGDEs, vectorStrataToAdd, rasterStrataToAdd):

  # Add any strata that are in vector format
  for strat in vectorStrataToAdd:
    # Load collection and filter to study area
    collection = ee.FeatureCollection(strat['assetName']).filterBounds(studyArea)
    # Rename selected attributes
    collection = collection.map(lambda f: f.select(strat['assetAttributes'], strat['gdeAttributes']))

    # Join to apply GDEs
    applyGDEs = spatialJoin(applyGDEs, collection, strat['gdeAttributes'])

  # Add any strata that are in raster format
  for strat in rasterStrataToAdd:
    # Load image
    image = ee.Image(strat['assetName']).select(strat['assetAttributes'])
    # Get original attributes:
    origNames = applyGDEs.first().propertyNames().getInfo()
    # Reduce to GDE collection
    applyGDEs = image.reduceRegions(**{\
      'collection': applyGDEs,
      'reducer': ee.Reducer.first(),
      'scale': sage.scale,
      'crs': sage.crs,
      'crsTransform': sage.transform})
    # Rename attributes. 
    if len(strat['assetAttributes'] == 1):
      applyGDEs = applyGDEs.select(origNames+['first'], origNames+[strat['gdeAttributes']])
    else:
      applyGDEs = applyGDEs.select(origNames+[strat['assetAttributes']], origNames+[strat['gdeAttributes']])

  return applyGDEs

def shortTrackTasks(credential_path = None):
	if credential_path != None: initializeFromToken(tokens[i])

	tasks = ee.data.getTaskList()
	ready = [i for i in tasks if i['state'] == 'READY']
	running = [i for i in tasks if i['state'] == 'RUNNING']
	failed = [i for i in tasks if i['state'] == 'FAILED']
	completed = [i for i in tasks if i['state'] == 'COMPLETED']
	running_names = [[str(i['description']),str(timedelta(seconds = int(((time.time()*1000)-int(i['start_timestamp_ms']))/1000)))] for i in running]
	failed_names = [[str(i['description']),str(i['error_message'])] for i in failed]
	completed_names = [str(i['description']) for i in completed]
	now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	print(len(ready),'tasks ready',now)
	print(len(running),'tasks running',now)
	# print(len(failed),'tasks failed',now)
	# print(len(completed),'tasks completed',now)
	print('Running names:')
	for rn in running_names: print(rn)
	# for fn in failed_names:print(fn)
	# for cn in completed_names:print('Completed '+cn)

	print()
	print()
	time.sleep(2)

####################################################################################################
#					Set Up for All SAGE Scripts
####################################################################################################
#---------------------Reset study area if it is a state name-------------------------
states = ee.FeatureCollection('TIGER/2016/States')
if studyArea in states.aggregate_histogram('NAME').getInfo():
	studyArea = ee.Feature(states\
            .filter(ee.Filter.eq('NAME',studyArea))\
            .first())\
            .convexHull(10000)\
            .buffer(10000)\
            .geometry()

#---------------------Create Folders if They Do Not Already Exist-------------------------
if not ee.data.getInfo(rootFolder):
	ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, rootFolder)
if not ee.data.getInfo(rasterDataRoot):
	ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, rasterDataRoot)
if not ee.data.getInfo(tableRoot):
	ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, tableRoot)
if not ee.data.getInfo(trainingTableDir):
	ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, trainingTableDir)
if not ee.data.getInfo(applyTableDir):
	ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, applyTableDir)
if not ee.data.getInfo(predTableDir):
	ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, predTableDir)





