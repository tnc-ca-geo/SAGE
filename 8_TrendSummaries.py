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


#Notebook to summarize modeled depth to groundwater values across various geographic areas


####################################################################################################
import os,subprocess
import pandas as pd
import os,glob,datetime, pdb
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import statsmodels.api as sm
import mapply # pip install mapply
import SAGE_Initialize as sage

####################################################################################################

# You must have downloaded the Random Forest prediction tables using 7_DownloadOutputs.py
# That script will export the tables to Google Drive, and you need to move them to the localPredTablePath
# on your computer.

# NOTE that this is developed specifically for the needs of the California SAGE study.
# If you do not have 'Hydroregion_Number' and 'Groundwater_Basin_ID' in your study area, this script may need some
# editing in order for it to work for your particular case.

####################################################################################################
#                     Parameters and Paths
####################################################################################################


####################################################################################################
#                     Functions
####################################################################################################
#Run ordinary least squares regression
#Function to run ols for a specified POLYGON_ID for a set of years
def apply_ols(id, df, startYear, endYear, alpha = 0.05):
	
	#Set up the years
	years = np.arange(startYear,endYear+1)

	#Filter out rows for the id and years
	dft = df[df.POLYGON_ID == id]
	dft = dft[dft.year.isin(years)].sort_values('year', axis = 0)
	
	#Pull other columns (should be the same for a given POLYGON_ID)
	keep = dft[sage.keep_columns].values[0]
	
	#Pull in variables for OLS and fit model
	y = dft['modeled_DGW'].values*-1 # response
	
	#Pull in training values if available
	training = dft['matchesReduced'].values*-1
	years = dft['year'].values
	X = years  # predictor
	X = sm.add_constant(X)  # Adds a constant term to the predictor
	res = sm.OLS(y,X)
	
	#Pull out results
	intercept = res.fit().params[0]
	slope = res.fit().params[1]
	pvalue = res.fit().pvalues[1]
	
	#Threshold p value
	olsSig = pvalue <= alpha
	if not olsSig:
		sigDir =  'no trend'
	elif olsSig and slope < 0:
		sigDir = 'decreasing'
	elif olsSig and slope > 0:
		sigDir =  'increasing'
	elif olsSig and slope == 0:
		sigDir =  'flat'
   
	out_line = list(keep)
	
	#Convert list variables into a single string that is not comma delimited for use in GEE
	years = np.array2string(years, max_line_width = 50000, separator='!SEP!').replace('[','').replace(']','')
	y = np.array2string(y, max_line_width = 50000, separator='!SEP!').replace('[','').replace(']','')
	training = np.array2string(training, max_line_width = 50000, separator='!SEP!').replace('[','').replace(']','')
	
	
	out_line.extend([len(y),startYear,endYear,years,y,training,intercept,slope,pvalue,sigDir])
   
	return out_line

#Plot some results
def plot_fit(row, startYear, endYear):
	fig, ax = plt.subplots(figsize=(12, 8))

	id = row['POLYGON_ID']
	xs = [float(yr) for yr in row['Years'].split('!SEP!')]
	ys = [float(p) for p in row['Preds'].split('!SEP!')]
	predicted = np.multiply(row['OLS_Slope'], xs) + row['OLS_Intercept']
   
	plt.title('{}-{} ID: {} Slope: {}  OLS P: {} OLS Sig: {}'.format(startYear,endYear,id,round(row['OLS_Slope'],6),round(row['OLS_Pvalue'],6),row['OLS_SigDir']))
	ax.plot(xs,ys)
	ax.plot(xs, predicted)

	ax.legend(['Modeled DGW', 'OLS Fit'])
	ax.set_xlabel('Year')
	ax.set_ylabel('DGW')

	plt.show()

####################################################################################################
#                     Prep
####################################################################################################

#Make dir if it doesn't exist
if not os.path.exists(sage.summary_table_dir):
	os.makedirs(sage.summary_table_dir)   

#Read in tables
#Will only read in csvs if pickle version doesn't exist
tables = glob.glob(os.path.join(sage.table_dir,'*.csv'))
full_pickle = os.path.join(sage.summary_table_dir,'All_Tables.pckl')
if not os.path.exists(full_pickle):
	li = []
	for filename in tables:
		print('Reading in: ',filename)
		df = pd.read_csv(filename, index_col=None, header=0, skipinitialspace=True)#, usecols=use_colummns)
		li.append(df)
	df = pd.concat(li, axis=0, ignore_index=True)
	df.to_pickle(full_pickle)
	out_csv =  os.path.splitext(full_pickle)[0]+'.csv'
	df.to_csv(out_csv)
else:
	print('Reading in:',full_pickle)
	df = pd.read_pickle(full_pickle)

print(df.head())

####################################################################################################
#                     Prep
####################################################################################################

for startYear, endYear in sage.year_sets:
	out_pickle = os.path.join(sage.summary_table_dir,'DGW_Trends_{}-{}.pckl'.format(startYear,endYear))
	if not os.path.exists(out_pickle):
		print('processing', startYear, endYear)
		ids = np.unique(df.POLYGON_ID)
#         print(ids)
		total = len(ids)
		out = []
		for i, id in enumerate(ids):
			print(id)
			try:
				out_line = apply_ols(id, df, startYear, endYear)
				out.append(out_line)
			except Exception as e:
				print(e)

		out = pd.DataFrame(out, columns = sage.column_names)
		print(out.head(3))

		print(out_pickle)
		out.to_pickle(out_pickle)
		out_csv =  os.path.splitext(out_pickle)[0]+'.csv'
		out.to_csv(out_csv,index = False)
	else:
		print('Already created: ',out_pickle)


#Plot the first 2 igdes for each year set
if sage.showExamplePlots:
	for startYear, endYear in sage.year_sets:
		print(startYear,endYear)
		out_pickle = os.path.join(sage.summary_table_dir,'DGW_Trends_{}-{}.pckl'.format(startYear,endYear))
		out = pd.read_pickle(out_pickle)
		out.head(2).apply(plot_fit, args = (startYear,endYear), axis=1)
   

#Group summarize trend results
group_fields = ['statewide','Hydroregion_Number','Groundwater_Basin_ID']
pd.options.display.float_format = '{:.4}'.format
for group_field in group_fields:
	summary_counts_table = []
	i = 0
	out_columns = []
	for startYear,endYear in sage.year_sets:
		out_pickle = os.path.join(sage.summary_table_dir,'DGW_Trends_{}-{}.pckl'.format(startYear,endYear))
		out = pd.read_pickle(out_pickle)
		out['statewide'] = 1
		print(out.shape)
		df = out
		if i == 0:
			med_slope =out.groupby([group_field])['OLS_Slope'].agg(['count','median'])
		else:
			med_slope =out.groupby([group_field])['OLS_Slope'].agg(['median'])

		counts = out.groupby([group_field])['OLS_SigDir'].value_counts(normalize=True)

		t = pd.concat([med_slope,counts.unstack()],axis = 1)
		columnsT = ['OLS_Median_Trend_{}_{}'.format(startYear,endYear),'OLS_Decreasing_Trend_Sig_{}_{}'.format(startYear,endYear),'OLS_Increasing_Trend_Sig_{}_{}'.format(startYear,endYear),'OLS_No_Trend_Sig_{}_{}'.format(startYear,endYear)]
		if i == 0:
			columns = ['count']
			columns.extend(columnsT)
		else:
			columns = columnsT
		t.columns = columns
		summary_counts_table.append(t)
		i+=1

	summary_counts_table = pd.concat(summary_counts_table, axis=1)
	print(summary_counts_table)
	out_csv =  os.path.join(sage.summary_table_dir, group_field + '_Summary.csv')
	summary_counts_table.to_csv(out_csv)


