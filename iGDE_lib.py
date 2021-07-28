"""
MIT License

Copyright (c) 2021 Ian Housman

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
#Library containing globals for entire iGDE monitoring processing framework
####################################################################################################
#Module imports
from  geeViz.changeDetectionLib import *
import threading,time,glob,json, pdb
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
import matplotlib.pyplot as plt
Map.clearMap()
####################################################################################################
#Define user parameters:

# Specify study area: Study area
# Can be a featureCollection, feature, or geometry
California = ee.Feature(ee.FeatureCollection('TIGER/2016/States')\
            .filter(ee.Filter.eq('NAME','California'))\
            .first())\
            .convexHull(10000)\
            .buffer(10000)\
            .geometry()
studyArea = California

# CRS- must be provided.  
# Common crs codes: Web mercator is EPSG:4326, USGS Albers is EPSG:5070, 
# WGS84 UTM N hemisphere is EPSG:326+ zone number (zone 12 N would be EPSG:32612) and S hemisphere is EPSG:327+ zone number
crs = 'EPSG:5070'

# Specify transform if scale is null and snapping to known grid is needed
transform = [30,0,-2361915.0,0,-30,3177735.0]

# Specify scale if transform is null
scale = None

#Specify image collections
daymetCollection = 'projects/igde-work/raster-data/DAYMET-Collection'
compositeCollection = 'projects/igde-work/raster-data/composite-collection'
ltCollection = 'projects/igde-work/raster-data/LandTrendr-collection'

#Specify parameters to filter iGDEs with
minDGW = 0
maxDGW = 20
dgwNullValue = -999.0
minGDESize = 900

#Specify training and model application years
startTrainingYear = 1985
endTrainingYear = 2018
startApplyYear = 1985
endApplyYear = 2019

#Specify table locations
outputTrainingTableDir = 'projects/igde-work/raster-zonal-stats-data/RF-Training-Tables';
outputTrainingTableName = 'dgwRFModelingTrainingTable7_{}_{}'.format(startTrainingYear,endTrainingYear)
outputTrainingTablePath = outputTrainingTableDir + '/'+outputTrainingTableName

outputApplyTableDir = 'projects/igde-work/raster-zonal-stats-data/RF-Apply-Tables'
outputApplyTableName = 'dgwRFModelingApplyTable5'

outputPredTableDir = 'projects/igde-work/raster-zonal-stats-data/RF-Results-Tables'
outputPredTableNameStart = 'dgwRFModelingPredTable7'
runname = 'climate-spectral-strata-v7'
predictors = ['.*_fitted','.*_mag','huc8','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number','MXStatus']

outputPredDriveDir = 'rf-pred-results-tables-2021-redo3_v7'
outputLocalRFModelInfoDir = r'/Volumes/Seagate Backup Plus Drive/contour/tnc/gdepulse/iGDE_Monitor_Outputs'

#Choose which bands from LandTrendr to summarize
#Options are '.*_fitted','.*_mag','.*_diff','.*_dur','.*_slope'
ltBands = ['.*_fitted','.*_mag','.*_diff']

#Bring in training (igdes w well obs) and apply igdes (all igdes)
trainingGDEs = ee.FeatureCollection('projects/igde-work/igde-data/iGDE_AnnualDepth_renamed_oct2018_correctedDGW')
applyGDEs = ee.FeatureCollection('projects/igde-work/igde-data/i02_IndicatorsofGDE_Vegetation_v0_5_3_updated_macroclasses')

#Filter igdes
applyGDEs = applyGDEs.filter(ee.Filter.gte('Shape_Area',minGDESize))
applyGDEs = applyGDEs.map(lambda f:ee.Feature(f).dissolve(100))

trainingGDEs = trainingGDEs.filter(ee.Filter.gte('Shape_Area',minGDESize))
trainingGDEs = trainingGDEs.filter(ee.Filter.stringContains('Depth_Str','Shallow: perf.'))


###################################################################################################
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

def addStrata(applyGDEs):
	#applyGDEs = applyGDEs.limit(20)
	groups = ee.Dictionary(applyGDEs.aggregate_histogram('Macrogroup'))
	names = ee.List(groups.keys())
	numbers = ee.List.sequence(1,names.length())

	applyGDEs = applyGDEs.map(lambda f: f.set('Macrogroup_Number',f.get('Macrogroup')))
	applyGDEs = applyGDEs.remap(names,numbers,'Macrogroup_Number')
  
	huc8 = ee.FeatureCollection("USGS/WBD/2017/HUC08").filterBounds(studyArea)
	biome_ecoregion = ee.FeatureCollection('projects/igde-work/igde-data/ecoregion_biome_ca_2020').filterBounds(studyArea)
	biome_ecoregion = biome_ecoregion.map(lambda f: f.select(['BIOME','EAA_ID'],['Biome_Number','Ecoregion_Number']))

	hydroRegion = ee.FeatureCollection('projects/igde-work/igde-data/Hydrologic_Regions')
	hydroRegion = hydroRegion.map(lambda f: f.select(['OBJECTID'],['Hydroregion_Number']))

	mxStatus = ee.FeatureCollection('projects/igde-work/igde-data/iGDE_MXstatus').select(['POLYGON_ID','MXStatus'])

	huc8 = huc8.map(lambda f: f.set('huc8_int',ee.Number.parse(f.get('huc8'))))
	applyGDEs = spatialJoin(applyGDEs,huc8,['huc8'])
	applyGDEs = spatialJoin(applyGDEs,biome_ecoregion,['Biome_Number','Ecoregion_Number'])
	applyGDEs = spatialJoin(applyGDEs,hydroRegion,['Hydroregion_Number'])
	#applyGDEs = joinFeatureCollectionsReverse(mxStatus, applyGDEs, 'POLYGON_ID')

	# print(applyGDEs.aggregate_histogram('Hydroregion_Number').keys().length().getInfo())
	return applyGDEs



# Map.addLayer(applyGDEs,{'strokeColor':'00F','layerType':'geeVectorImage'}, 'Apply iGDEs')
applyGDEs = addStrata(applyGDEs)
Map.addLayer(applyGDEs,{'strokeColor':'00F','layerType':'geeVectorImage'}, 'Apply iGDEs w strata',False)


trainingGDEs = trainingGDEs.filter(ee.Filter.gte('Shape_Area',900)) # this is done earlier
trainingGDEs = trainingGDEs.filter(ee.Filter.stringContains('Depth_Str','Shallow: perf.'))
trainingGDEs = trainingGDEs.map(lambda f: f.set('unique_id',ee.String(f.get('POLYGON_ID')).cat('_').cat(ee.String(f.get('STN_ID')))))
Map.addLayer(trainingGDEs,{'strokeColor':'00F','layerType':'geeVectorImage'}, 'Training iGDEs w strata',False)

# Map.view()
###################################################################################################
token_dir = os.path.dirname(ee.oauth.get_credentials_path())
tokens = glob.glob(os.path.join(token_dir,'*'))
###################################################################################################
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
###############################################################
def limitThreads(limit):
  while threading.activeCount() > limit:
    time.sleep(1)
    print(threading.activeCount(),'threads running')
###############################################################
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

def trackTasks(credential_path = None):
	if credential_path != None:initializeFromToken(tokens[i])

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
	for rn in running_names:print(rn)
	# for fn in failed_names:print(fn)
	# for cn in completed_names:print('Completed '+cn)

	print()
	print()
	time.sleep(10)
	
###################################################################################################

