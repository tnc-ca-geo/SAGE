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


#Script to fit a Random Forest model, apply it, and export the resulting tables

####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, changeDetectionLib, taskManagerLib, assetManagerLib
from geeViz.geeView import *
import pdb
import matplotlib.pyplot as plt

####################################################################################################
#Define user parameters:

# Options defined in SAGE_Initialize:
# Start and end apply year 
# Random Forest model parameters
# Predictor List
# Run name

#--------The Following Options Are Default Methods and Do Not Need to Be Changed-----------

#Which iteration (can just set to 1)
runNumber = 1

####################################################################################################
#                        End User Parameters
####################################################################################################

####################################################################################################
#                     Define Functions
####################################################################################################

#Function to fit RF model
def fitRFModel(trainingTable, predictorFields, runName):
  #Fit model
  rf = ee.Classifier.smileRandomForest(**sage.randomForestParameters)
  rf = rf.setOutputMode('REGRESSION')
  trainingTable = trainingTable.filter(ee.Filter.notNull(predictorFields))
  trained = rf.train(trainingTable, 'dgw', predictorFields)
  return trained

#Function to get information about fitted model
def getRFModelInfo(rfModel, outputInfo):

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

  fig = plt.figure()
  plt.bar(importance.keys(), importance.values())
  plt.xticks(rotation = 60, fontsize = 10,ha = 'right')
  plt.title('Variable Importance | OOB Error: {}'.format(oob))
  fig.savefig(os.path.splitext(outputInfo)[0] + '_importance.png')
  #plt.show()
  plt.close()

#Function to apply a fitted model across a set of years and corresponding apply tables and export predicted values
def applyRFModel(rfModel, years, predictorTable, predictorFields, runName):

  #Set up predicted output table name
  outputPredTablePath = '{}/{}'.format(sage.predTableDir, '{}_{}_'.format(sage.predTableNameStart, runName))
  print(outputPredTablePath)

  #Iterate across each year and apply model and export predictions
  for yr in years:
    print('Modeling:',yr)

    #Bring in apply table
    applyTrainingTableYr = ee.FeatureCollection('{}/{}_{}'.format(sage.applyTableDir, sage.applyTableName, yr))

    #Bring in obs from the training table for that year and join it when available so actual and predicted can be compared
    trainingYr = trainingTable.filter(ee.Filter.eq('year',yr))
    applyTrainingTableYr = sage.innerOuterJoin(applyTrainingTableYr, trainingYr, sage.gdeIdName,'dgw',ee.Reducer.mean())

    # #Fix huc8 field issue
    # applyTrainingTableYr = applyTrainingTableYr.map(lambda f:f.set('huc8',ee.Number.parse(f.get('huc8'))))

    #Filter out null values
    applyTrainingTableYr = applyTrainingTableYr.filter(ee.Filter.notNull(predictorFields))
    
    #Get model info
    modelInfo = ee.Dictionary(rfModel.explain())
    outOfBagErrorEstimate = modelInfo.get('outOfBagErrorEstimate')
    varImp = ee.Dictionary(modelInfo.get('importance')).toArray()

    #Apply model
    dgwPredicted = applyTrainingTableYr\
      .classify(rfModel, 'modeled_DGW')\
      .set({\
        'predictor_classes':predictorFields,
        'runName':runName,
        'runNumber':runNumber,
        'nTrees': sage.nTrees,
        'rfModel':rfModel,
        'outOfBagErrorEstimate':outOfBagErrorEstimate,
        'varImp':varImp\
      })

    #Export predictions         
    outputName = outputPredTablePath + str(yr)
    t = ee.batch.Export.table.toAsset(**{\
      'collection': dgwPredicted, 
      'description': outputName.split('/')[-1],
      'assetId': outputName})
    print('Exporting:',outputName)
    t.start()


####################################################################################################
#                         Prep
####################################################################################################
#Bring in training table
trainingTable = ee.FeatureCollection(sage.trainingTablePath)

####################################################################################################
#                         Run Model
####################################################################################################

#Function calls
#Iterate across each run and fit, summarize, and apply model
for run in sage.modelRuns:

  #Get predictor field namesss
  predictorFields = ee.Feature(trainingTable.select(run[1]).first()).propertyNames().remove('system:index').getInfo()
  
  #Fit model
  rfModel  = fitRFModel(trainingTable, predictorFields, run[0])

  #Get model info
  getRFModelInfo(rfModel, os.path.join(sage.outputLocalRFModelInfoDir, 'dgwRFModelInfo-{}.json'.format(run[0])))

  #Apply and export model
  if sage.modelApplyUseMultiCredentials:
    
    sets = sage.new_set_maker(range(sage.startApplyYear, sage.endApplyYear+1), len(sage.tokens))
    for i,years in enumerate(sets):
      sage.initializeFromToken(sage.tokens[i])
      print(ee.String('Token works!').getInfo())
      print(years)
      applyRFModel(rfModel, years, trainingTable, predictorFields, sage.runname)
      sage.shortTrackTasks()

  else:

    applyRFModel(rfModel, range(sage.startApplyYear, sage.endApplyYear+1), trainingTable, predictorFields, sage.runname)


taskManagerLib.trackTasks()

