# Shallow Groundwater Estimation Tool (SAGE)
> Remote monitoring of groundwater-dependent ecosystems in shallow aquifers
* Contains all methods outlined in Rohde M. M., T. Biswas, I. W. Housman, L. S. Campbell, K. R. Klausmeyer, and J. K. Howard, 2021: A Machine Learning Approach to Predict Groundwater Levels in California Reveals Ecosystems at Risk. Frontiers in Earth Sciences, 9. https://doi.org/10.3389/feart.2021.784499

## Primary POCs
* Primary technical contacts
  * Ian Housman - ian.housman@gmail.com
  * Leah Campbell - lcampbell@contourgroupconsulting.com 
  
* Primary manuscript author
  * Melissa Rohde - melissa.rohde@tnc.org 

## Dependencies
* Python 3
* earthengine-api (Python package)
* geeViz (Python package)

## Using
* Ensure you have Python 3 installed
  * <https://www.python.org/downloads/>
  
* Ensure the Google Earth Engine api is installed and up-to-date
  * `pip install earthengine-api --upgrade`
  * `conda update -c conda-forge earthengine-api`

* Ensure geeViz is installed and up-to-date
  * `pip install geeViz --upgrade`

* Running scripts
  * Each script is intended to run sequentially to reproduce the methods used in Rohde et al 2021.

## Abstract
* Groundwater dependent ecosystems (GDEs) are increasingly threatened worldwide, but the shallow groundwater resources that they are reliant upon are seldom monitored. In this study, we used satellite-based remote sensing to model groundwater levels under groundwater dependent ecosystems across California, USA. Depth to groundwater was modelled for a 35-year period (1985-2019) within all groundwater dependent ecosystems across the state (n=95,135). Our model was developed within Google Earth Engine using Landsat satellite imagery, climate data, and field-based groundwater data (n=627 shallow (<30 m) monitoring wells) as predictors in a Random Forest model. Our findings show that (1) 44% of groundwater dependent ecosystems have experienced a significant long-term decline in groundwater levels compared to 28% with a significant increase; (2) groundwater level declines have intensified during the most recent two decades, with 39% of groundwater dependent ecosystems experiencing declines in the 2003-2019 period compared to 27% in the 1985-2002 period; and (3) groundwater declines are most prevalent within GDEs existing in areas of the state where sustainable groundwater management is absent. Our results indicate that declining shallow groundwater levels may be adversely impacting California’s groundwater dependent ecosystems. Particularly where groundwater levels have fallen beneath plant roots or streams thereby affecting key life processes, such as forest recruitment/succession, or hydrological processes, such as streamflow that affects aquatic habitat. In the absence of groundwater monitoring well data, our model and findings can be used to help state and local water agencies fill in data gaps of shallow groundwater conditions, evaluate potential effects on GDEs, and improve sustainable groundwater management policy in California.
