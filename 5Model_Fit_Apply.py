#Script to take LandTrendr stack outputs and summarize across iGDEs for training and applying a model
####################################################################################################
from iGDE_lib import *
####################################################################################################

####################################################################################################
def getRFModel(trainingTable,predictorFields,runName):
  #Fit model
  rf = ee.Classifier.smileRandomForest(nTrees)
  rf = rf.setOutputMode('REGRESSION')
  trainingTable = trainingTable.filter(ee.Filter.notNull(predictorFields))
  trained = rf.train(trainingTable, 'dgw', predictorFields);
  
  n = trainingTable.size()
  # print('N training samples',n.getInfo());
  results = ee.Dictionary(ee.Dictionary(trained.explain()).get('importance'))
  # print(trained.explain().getInfo())
  importanceNames = ee.List(results.keys())
  importanceValues = ee.List(results.values())
  importanceNames = importanceNames.sort(importanceValues)
  importanceValues = importanceValues.sort()
  # print(importanceNames.getInfo(),importanceValues.getInfo())
  return trained
####################################################################################################
def applyRFModel(rfModel,years,predictorTable,predictorFields,runName):
  outputPredTableName = 'dgwRFModelingPredTable4_'+runName+'_'
  outputPredTablePath = '{}/{}'.format(outputPredTableDir,outputPredTableName)
  print(outputPredTablePath)
  for yr in years:
    print('Modeling:',yr)
    applyTrainingTableYr = ee.FeatureCollection('{}/{}_{}'.format(outputApplyTableDir,outputApplyTableName,yr))

    trainingYr = trainingTable.filter(ee.Filter.eq('year',yr))
    
    applyTrainingTableYr = innerOuterJoin(applyTrainingTableYr,trainingYr,'POLYGON_ID','dgw',ee.Reducer.mean())

    applyTrainingTableYr = applyTrainingTableYr.map(lambda f:f.set('huc8',ee.Number.parse(f.get('huc8'))))
    applyTrainingTableYr = applyTrainingTableYr.filter(ee.Filter.notNull(predictorFields))
    
    modelInfo = ee.Dictionary(rfModel.explain())
    outOfBagErrorEstimate = modelInfo.get('outOfBagErrorEstimate')
    varImp = ee.Dictionary(modelInfo.get('importance')).toArray()

#   // var predictors = ee.Image(applyImages.filter(ee.Filter.calendarRange(yr,yr,'year')).first());;
    dgwPredicted = applyTrainingTableYr.limit(20).classify(rfModel,'modeled_DGW').set({'predictor_classes':predictorFields,\
                                    'runName':runName,\
                                    'runNumber':runNumber,\
                                    'nTrees':nTrees,\
                                    'rfModel':rfModel,\
                                    'outOfBagErrorEstimate':outOfBagErrorEstimate,\
                                    'varImp':varImp\
                                    })
    
    # print(dgwPredicted.getInfo())
             
    outputName = outputPredTablePath +str(yr)
    t = ee.batch.Export.table.toAsset(dgwPredicted, outputName.split('/')[-1],outputName)
    print('Exporting:',outputName)
    t.start()
####################################################################################################
#Wrapper function to export predicted tables for a set of years with a set of credentials
def batchApplyRFModel(rfModel,trainingTable,predictorFields,runName):
  sets = new_set_maker(range(startApplyYear,endApplyYear+1),len(tokens))
  for i,years in enumerate(sets):
    initializeFromToken(tokens[i])
    print(ee.String('Token works!').getInfo())
    print(years)
    applyRFModel(rfModel,years,trainingTable,predictorFields,runName)
    # trackTasks()
####################################################################################################
nTrees =90
runNumber = 6




modelInfoTableDir = 'projects/igde-work/raster-zonal-stats-data/RF-ModelInfo-Tables';


runs = [['climate-spectral-strata',['.*_fitted','.*_mag','.*_diff','huc8','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\
['climate-strata',['.*mean_LT_fitted','.*mean_LT_mag','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\
['climate',['.*mean_LT_fitted','.*mean_LT_mag']],\
['climate-spectral-strata-fitted-only',['.*_fitted','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\
['climate-spectral-strata-mag-only',['.*_mag','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\
['climate-spectral',['.*_fitted','.*_mag']],\
['climate-spectral-fitted-only',['.*_fitted']],\
['climate-spectral-mag-only',['.*_mag']]\
]




outputTableDir = 'projects/igde-work/raster-zonal-stats-data/RF-Results-Tables'

trainingTable = ee.FeatureCollection(outputTrainingTablePath)
trainingTable = trainingTable.map(lambda f:f.set('huc8',ee.Number.parse(f.get('huc8'))))
# print(trainingTable.aggregate_histogram('year').getInfo())
modelInfos = []
for run in runs[:1]:
  predictorFields = ee.Feature(trainingTable.select(run[1]).first()).propertyNames().remove('system:index').getInfo()
  # print(predictorFields)
  rfModel  = getRFModel(trainingTable,predictorFields,run[0])
  #print(rfModel)
  batchApplyRFModel(rfModel,trainingTable,predictorFields,run[0])
#   f = ee.Feature(ee.Geometry.Point([0,0]))
#   modelInfo = {}
#   modelInfo['runName'] = run[0]
#   modelInfo['predVariables'] = ','.join(predictorFields)
#   modelInfo['nTrees'] = nTrees
#   var exp = ee.Dictionary(rfModel.explain());
#     var imp = ee.Dictionary(exp.get('importance'));
#     modelInfo.varImpNames = imp.keys();
#     modelInfo.varImpValues = imp.values();
#     modelInfo.nTrainingSamples =trainingTable.size();
    
#     modelInfo.varImpNames = modelInfo.varImpNames.sort(modelInfo.varImpValues).join(',');
#     modelInfo.varImpValues = modelInfo.varImpValues.sort(modelInfo.varImpValues).join(',');
    
#     modelInfo.outOfBagErrorEstimate = exp.get('outOfBagErrorEstimate');
    
#     f = f.set(modelInfo);
    
   
#     modelInfos.append(f)

# modelInfos = ee.FeatureCollection(modelInfos)
# modelInfos = modelInfos.set({
#     'nTrees':nTrees
#   })
# ####################################################################################################
#Function calls

#View map
# Map.view()