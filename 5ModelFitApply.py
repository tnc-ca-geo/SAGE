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
#Script to fit a Random Forest model, apply it, and export the resulting tables
####################################################################################################
from iGDE_lib import *
####################################################################################################
#Define user parameters:

#Number of trees in RF model
nTrees =90

#Which iteration (can just set to 1)
runNumber = 6



#Runs of models to iterate across
#Specify a descriptive name and then the selectors of the predictor fields
runs = [['climate-spectral-strata',['.*_fitted','.*_mag','huc8','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],
# ['climate',['.*mean_LT_fitted','.*mean_LT_mag']],
]
# ['climate-strata',['.*mean_LT_fitted','.*mean_LT_mag','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\

# ['climate-spectral-strata-fitted-only',['.*_fitted','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\
# ['climate-spectral-strata-mag-only',['.*_mag','Ecoregion_Number','Biome_Number','Macrogroup_Number','Hydroregion_Number']],\
# ['climate-spectral',['.*_fitted','.*_mag']],\
# ['climate-spectral-fitted-only',['.*_fitted']],\
# ['climate-spectral-mag-only',['.*_mag']]\
# ]

####################################################################################################
#Bring in training table
trainingTable = ee.FeatureCollection(outputTrainingTablePath)
#Fix training table HUC8 issue
trainingTable = trainingTable.map(lambda f:f.set('huc8',ee.Number.parse(f.get('huc8'))))
####################################################################################################
#Function to fit RF model
def fitRFModel(trainingTable,predictorFields,runName):
  #Fit model
  rf = ee.Classifier.smileRandomForest(nTrees)
  rf = rf.setOutputMode('REGRESSION')
  trainingTable = trainingTable.filter(ee.Filter.notNull(predictorFields))
  trained = rf.train(trainingTable, 'dgw', predictorFields);
  return trained
#################################################################################################### 
#Function to get information about fitted model
def getRFModelInfo(rfModel,outputInfo):
  if not os.path.exists(outputInfo):
    modelInfo = rfModel.explain().getInfo()
    
    o = open(outputInfo,'w')
    o.write(json.dumps(modelInfo))
    o.close()
  with open(outputInfo) as f:
    modelInfo = json.load(f)
  print('Model info:',modelInfo)
  importance = modelInfo['importance']
  oob = round(modelInfo['outOfBagErrorEstimate'],2)
  #This line taken from: https://stackoverflow.com/questions/613183/how-do-i-sort-a-dictionary-by-value
  importance = {k: v for k, v in sorted(importance.items(), key=lambda item: item[1])}

  fig = plt.bar(importance.keys(),importance.values())
  plt.xticks(rotation = 60, fontsize = 10,ha = 'right')
  plt.title('Variable Importance | OOB Error: {}'.format(oob))
  # fig.savefig(os.path.splitext(outputInfo)[0] + '_importance.png')
  plt.show()
##################################################################
#Function to apply a fitted model across a set of years and corresponding apply tables and export predicted values
def applyRFModel(rfModel,years,predictorTable,predictorFields,runName):

  #Set up predicted output table name
  outputPredTableName = '{}_{}_'.format(outputPredTableNameStart,runName)
  outputPredTablePath = '{}/{}'.format(outputPredTableDir,outputPredTableName)
  print(outputPredTablePath)

  #Iterate across each year and apply model and export predictions
  for yr in years:
    print('Modeling:',yr)

    #Bring in apply table
    applyTrainingTableYr = ee.FeatureCollection('{}/{}_{}'.format(outputApplyTableDir,outputApplyTableName,yr))

    #Bring in obs from the training table for that year and join it when available so actual and predicted can be compared
    trainingYr = trainingTable.filter(ee.Filter.eq('year',yr))
    applyTrainingTableYr = innerOuterJoin(applyTrainingTableYr,trainingYr,'POLYGON_ID','dgw',ee.Reducer.mean())

    #Fix huc8 field issue
    applyTrainingTableYr = applyTrainingTableYr.map(lambda f:f.set('huc8',ee.Number.parse(f.get('huc8'))))

    #Filter out null values
    applyTrainingTableYr = applyTrainingTableYr.filter(ee.Filter.notNull(predictorFields))
    
    #Get model info
    modelInfo = ee.Dictionary(rfModel.explain())
    outOfBagErrorEstimate = modelInfo.get('outOfBagErrorEstimate')
    varImp = ee.Dictionary(modelInfo.get('importance')).toArray()

    #Apply model
    dgwPredicted = applyTrainingTableYr.classify(rfModel,'modeled_DGW').set({'predictor_classes':predictorFields,\
                                    'runName':runName,\
                                    'runNumber':runNumber,\
                                    'nTrees':nTrees,\
                                    'rfModel':rfModel,\
                                    'outOfBagErrorEstimate':outOfBagErrorEstimate,\
                                    'varImp':varImp\
                                    })
    #Export predictions         
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
    # applyRFModel(rfModel,years,trainingTable,predictorFields,runName)
    trackTasks()
####################################################################################################
#Function to export predicted dgw tables
def downloadModeledOutputs(removeGeometry = True):

  gwb = ee.FeatureCollection('projects/igde-work/igde-data/CA_Bulletin_118_Groundwater_Basins').select(['OBJECTID'],['Groundwater_Basin_ID'])

  #Find predicted tables
  tables = [i['id'] for i in ee.data.getList({'id':outputPredTableDir}) ]
  tables = [i for i in tables if os.path.basename(i).find(outputPredTableNameStart) > -1]

  #Set up a dummy location to simplify geometry with to save space
  dummyLocation = ee.Geometry.Point([-111,45])
  
  #Export each table
  for table in tables:

    collection = ee.FeatureCollection(table)

    # print(collection.size().getInfo())
    collection = spatialJoin(collection,gwb,['Groundwater_Basin_ID'])
    # print(collection.size().getInfo())

    if removeGeometry:
      #Get rid of full geometry info to make table smaller
      collection = collection.map(lambda f: f.setGeometry(dummyLocation))


    description = os.path.basename(table)
    print('Exporting: ', description)
    t = ee.batch.Export.table.toDrive(collection, description, outputPredDriveDir)
    t.start()
####################################################################################################
#Function calls
#Iterate across each run and fit, summarize, and apply model
for run in runs:

  #Get predictor field names
  predictorFields = ee.Feature(trainingTable.select(run[1]).first()).propertyNames().remove('system:index').getInfo()

  #Fit model
  rfModel  = fitRFModel(trainingTable,predictorFields,run[0])

  #Get model info
  getRFModelInfo(rfModel,os.path.join(outputLocalRFModelInfoDir,'dgwRFModelInfo-{}.json'.format(run[0])))

  #Apply and export model
  batchApplyRFModel(rfModel,trainingTable,predictorFields,run[0])

#Once the predictions are all exported, export them to Drive
# downloadModeledOutputs()
####################################################################################################
