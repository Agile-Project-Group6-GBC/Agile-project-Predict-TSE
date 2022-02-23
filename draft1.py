# -*- coding: utf-8 -*-
"""Project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xjSJiqKBgNJP8j2XJaB8DXwYl-5dp4Fv

# Project Management Course - Applied AI Solutions Development

The dataset we will be using is from the Government of Canada website https://open.canada.ca/data/en/dataset/0e1e57aa-e664-41b5-a69f-d814d4407d62.  The dataset is 
an indexed time series of the Toronto Stock Exchange closing prices.  We will be building 3 forecasting models for comparison.  A SARIMAX (Seasonal 
AutoRegressive Moving Averages) model, Facebook's Neural Prophet, and a custom LSTM model.

Importing necessary libraries
"""

import warnings
import itertools
import numpy as np
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
plt.style.use('fivethirtyeight')
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.rcParams['axes.labelsize'] = 14
matplotlib.rcParams['xtick.labelsize'] = 12
matplotlib.rcParams['ytick.labelsize'] = 12
matplotlib.rcParams['text.color'] = 'k'
import os

"""# Data Exploration"""

# Importing our dataset to take a first look
df = pd.read_csv("10100125.csv")
df.head()

# The dataset appears to be a monthly record of the TSE's closing price, indexed to the year 2000 (1000 point index).  The TSE is then split into different industry composites,
# for example mining vs forest products.  The UOM_ID, scalar_factor, and secalar_id should be consistent throughout the dataset, this will need to be verified.  

df['REF_DATE'].min(), df['REF_DATE'].max()

# Our dataset appears to cover from Jan 1956 until Dec 2021.

# Checking the GEO feature to confirm all values say Canada, and this column is only provided for convenience when combining datasets
df['GEO'].value_counts()

# Confirmed, this feature will need to be dropped

# This code, after some research, is a geographic identifier.  It should be consistent and can be dropped
df['DGUID'].value_counts()

# Next we come to the description of the index provided.  We are only interested in the composite of the entire market.  The industry indexes are likely to have changed
# over the years.

df['Toronto Stock Exchange Statistics'].value_counts()

# As we can see the opening and closing prices weren't tracked for the first 150 time periods.

# We need to confirm that our intended subset spans the entire period we're looking for, and there's no name change
closing_subset = df.loc[df['Toronto Stock Exchange Statistics'] == 'Standard and Poor\'s/Toronto Stock Exchange Composite Index, close']

print(closing_subset.head())
print(closing_subset.tail())

# Here we confirm that our intended category spans the entirety of Jan 1956 to Dec 2021.

# Here we confirm that UOM is standardized throughout our dataset
closing_subset['UOM'].value_counts()

# Unnecessary feature
closing_subset['UOM_ID'].value_counts()

# Unnecessary feature
closing_subset['VECTOR'].value_counts()

# We can now safely assume that all other values are standardized and unnecessary for our model, we only need a subset of the closing TSE values and the time period

"""# Data Cleaning"""

# Here we create a subset to extract only data on the TSE records
df = df.loc[df['Toronto Stock Exchange Statistics'] == 'Standard and Poor\'s/Toronto Stock Exchange Composite Index, close']

# Then we can extract only the data and value columns
df = df[['REF_DATE', 'VALUE']].reset_index(drop=True)

"""# Data Exploration and Decomposition"""

# It's time to do some data exploration.  In order to prepare our data, we need to set the index in a datatime format, and have one column of values
Y = df['VALUE']
date = df['REF_DATE']
date = np.array(date,dtype=np.datetime64)
Series = pd.DataFrame(Y)
Series = Series.set_index(date, drop=True)
Series.head()

#plot close price
plt.figure(figsize=(10,6))
plt.grid(True)
plt.xlabel('Dates')
plt.ylabel('Close Prices')
plt.plot(df['VALUE'])
plt.title('Closing price')
plt.show()

# Here we plot our data to get a first look
Y.plot(figsize=(15, 6))
plt.title('First Look at Our Time Series')
plt.show()

"""Time series data can exhibit a variety of patterns, and it is often helpful to split a time series into several components, each representing an underlying pattern category.
If we assume an additive decomposition, then we can write yt=St+Tt+Rt,where yt is the data, St is the seasonal component, Tt is the trend-cycle component, and Rt is 
the remainder component, all at period t. Alternatively, a multiplicative decomposition would be written as yt=St×Tt×Rt.
The additive decomposition is the most appropriate if the magnitude of the seasonal fluctuations, or the variation around the trend-cycle, does not vary 
with the level of the time series. When the variation in the seasonal pattern, or the variation around the trend-cycle, appears to be proportional to the level
of the time series, then a multiplicative decomposition is more appropriate. 

The first graph represents the raw data of our model.  The 3 subsequent graphs represent the decomposed components of our raw data, that can be added together
to reconstruct the data shown in the top panel  The first graph is the raw data, the 2nd is the trend, 3rd is the seasonality component, and the 4th represents the 
residuals.
"""

# First we will check an additive decomposition with a period of 12, or 1 year
from pylab import rcParams
rcParams['figure.figsize'] = 18, 8
decomposition = sm.tsa.seasonal_decompose(Y, model='additive', freq=12)
fig = decomposition.plot()
plt.show()

# Here we check seasonality over 120 periods, or 10 years
from pylab import rcParams
rcParams['figure.figsize'] = 18, 8
decomposition = sm.tsa.seasonal_decompose(Y, model='additive', freq=120)
fig = decomposition.plot()
plt.show()

# Multiplicative model over 12 periods, or 1 year
from pylab import rcParams
rcParams['figure.figsize'] = 18, 8
decomposition = sm.tsa.seasonal_decompose(Y, model='multiplicative', freq=12)
fig = decomposition.plot()
plt.show()

#Multiplicative decomposition over a period of 120 periods, or 10 years
from pylab import rcParams
rcParams['figure.figsize'] = 18, 8
decomposition = sm.tsa.seasonal_decompose(Y, model='multiplicative', freq=120)
fig = decomposition.plot()
plt.show()

"""As we can see, a multiplicative model results is lower residuals.  Residuals are useful in checking whether a model has adequately captured the information in the data.
In addition, residuals should be uncorrelated, as we can see in our 120 period multiplicative model, the residuals appear to follow the trend of the seasonality chart,
meaning it has not captured the data well.

This will be useful information for hyperparameter tuning our models.

Non-linear models can be difficult for models.  We can see if transforming our data would be beneficial.

### Log Transform of our Signal
"""

from matplotlib import pyplot
from math import exp
from numpy import log

y = log(Y)
pyplot.figure(1)
# line plot
pyplot.subplot(211)
pyplot.plot(y)
# histogram
pyplot.subplot(212)
pyplot.hist(y)
pyplot.show()

"""Log transforming our signal turns the growth of our trendline from an exponential growth line to a linear growth line.  This will help our model performance"""

# Now if we do a 12 month decomposition the residuals appear as white noise (or random)
rcParams['figure.figsize'] = 18, 8
decomposition = sm.tsa.seasonal_decompose(y, model='multiplicative', freq=12)
fig = decomposition.plot()
plt.show()

"""# Forecast Models

### Neural Prophet

Neural Prophet is facebook's improvement upon their old forecasting package called Prophet.  The aim is to combine traditional forecasting techniques with neural network
models, in order to provide more readability than neural networks.
"""

from neuralprophet import NeuralProphet
import pandas as pd

# For Neural Prophet we only need 2 columns, time in a column called ds and Y for the values
neurodata = df[['REF_DATE', 'VALUE']]
neurodata.rename(columns = {'REF_DATE':'ds', 'VALUE':'y'}, inplace=True)
print(neurodata.head())
print(neurodata.tail())

# Applying our log transform
neurodata['y'] = np.log(neurodata['y'])

# The model has been built to be easy to deploy with only a couple lines of code.  Hyperparameter tuning is done with variables within the model, and takes some getting
# used to.  Here we have chosen 30 change points (which is a lot) because of the far reaching length of our time series, 1 hidden layer, and multiplicative since we're 
# dealing with economic data

m = NeuralProphet(seasonality_mode='multiplicative',  
                  num_hidden_layers=1, 
                  n_changepoints=30,
                  changepoints_range=1)
metrics = m.fit(neurodata, 
                freq="M")
forecast = m.predict(neurodata)

# We've built our model, now we need to forecast a period of 12 months to see how it performs
future = m.make_future_dataframe(neurodata, periods=12)
forecast = m.predict(future)

# First look at neuroprophet's predictions
forecasts_plot = m.plot(forecast)

fig_param = m.plot_parameters()

# This is our current signal, but our signal has been transformed.  We will need to reverse log transform our data back to get valid numbers

forecast['yhat1'] = np.exp(forecast['yhat1'])
forecasts_plot = m.plot(forecast)

!pip install pmdarima

import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('fivethirtyeight')
from pylab import rcParams
rcParams['figure.figsize'] = 10, 6
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima_model import ARIMA
from pmdarima.arima import auto_arima
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math

df_close = df['VALUE']
df_close.plot(style='k.')
plt.title('Scatter plot of closing price')
plt.show()

#Test for staionarity
def test_stationarity(timeseries):
    #Determing rolling statistics
    rolmean = timeseries.rolling(12).mean()
    rolstd = timeseries.rolling(12).std()
    #Plot rolling statistics:
    plt.plot(timeseries, color='blue',label='Original')
    plt.plot(rolmean, color='red', label='Rolling Mean')
    plt.plot(rolstd, color='black', label = 'Rolling Std')
    plt.legend(loc='best')
    plt.title('Rolling Mean and Standard Deviation')
    plt.show(block=False)
    
    print("Results of dickey fuller test")
    adft = adfuller(timeseries,autolag='AIC')
    # output for dft will give us without defining what the values are.
    #hence we manually write what values does it explains using a for loop
    output = pd.Series(adft[0:4],index=['Test Statistics','p-value','No. of lags used','Number of observations used'])
    for key,values in adft[4].items():
        output['critical value (%s)'%key] =  values
    print(output)
    
test_stationarity(df_close)

result = seasonal_decompose(df_close, model='multiplicative', freq = 30)
fig = plt.figure()  
fig = result.plot()  
fig.set_size_inches(16, 9)

from pylab import rcParams
rcParams['figure.figsize'] = 10, 6
df_log = np.log(df_close)
moving_avg = df_log.rolling(12).mean()
std_dev = df_log.rolling(12).std()
plt.legend(loc='best')
plt.title('Moving Average')
plt.plot(std_dev, color ="black", label = "Standard Deviation")
plt.plot(moving_avg, color="red", label = "Mean")
plt.legend()
plt.show()

#split data into train and training set
train_data, test_data = df_log[3:int(len(df_log)*0.9)], df_log[int(len(df_log)*0.9):]
plt.figure(figsize=(10,6))
plt.grid(True)
plt.xlabel('Dates')
plt.ylabel('Closing Prices')
plt.plot(df_log, 'green', label='Train data')
plt.plot(test_data, 'blue', label='Test data')
plt.legend()

model_autoARIMA = auto_arima(train_data, start_p=0, start_q=0,
                      test='adf',       # use adftest to find             optimal 'd'
                      max_p=3, max_q=3, # maximum p and q
                      m=1,              # frequency of series
                      d=None,           # let model determine 'd'
                      seasonal=False,   # No Seasonality
                      start_P=0, 
                      D=0, 
                      trace=True,
                      error_action='ignore',  
                      suppress_warnings=True, 
                      stepwise=True)
print(model_autoARIMA.summary())

model_autoARIMA.plot_diagnostics(figsize=(15,8))
plt.show()

model = ARIMA(train_data, order=(1, 0, 1))  
fitted = model.fit(disp=-1)  
print(fitted.summary())

from statsmodels.tsa.statespace.sarimax import SARIMAX

model = SARIMAX(train_data, order=(1, 0, 10),seasonal_order=(0,1,1,12))  
fitted = model.fit(disp=-1)  
print(fitted.summary())
