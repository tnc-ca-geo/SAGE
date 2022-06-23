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


# Script to download Random Forest prediction tables to Google Drive


####################################################################################################

import SAGE_Initialize as sage
from geeViz import getImagesLib, changeDetectionLib, taskManagerLib, assetManagerLib
from geeViz.geeView import *

####################################################################################################
#Define user parameters:

# Options defined in SAGE_Initialize:
# RF prediction table location and names
# Export path in Google Drive
# Whether or not to remove the geometry from the output table


####################################################################################################
#                     Prep
####################################################################################################
#Find predicted tables
tables = [i['id'] for i in ee.data.getList({'id': sage.predTableDir})]
tables = [i for i in tables if os.path.basename(i).find(sage.predTableNameStart) > -1]

#Set up a dummy location to simplify geometry with to save space
dummyLocation = ee.Geometry.Point([-111,45])

#Export each table
for table in tables:

  collection = ee.FeatureCollection(table)

  if sage.removeGeometry:
    #Get rid of full geometry info to make table smaller
    collection = collection.map(lambda f: f.setGeometry(dummyLocation))


  description = os.path.basename(table)
  print('Exporting: ', description)
  t = ee.batch.Export.table.toDrive(**{\
    'collection': collection, 
    'description': description, 
    'folder': sage.outputPredDriveDir})
  t.start()

taskManagerLib.trackTasks()







