#! /usr/bin/env python3

import time
import numpy as np

""" Base file used for my crypto  trading Algorithms, Indicators and formatting. """

"""
[######################################################################################################################]
[#############################################] TAS & INCICATORS SECTION [##############################################]
[#############################################]v^v^v^v^v^v^vv^v^v^v^v^v^v[##############################################]

### Indicators List ###
- BB
- RSI
- StochRSI
- Stochastic Oscillator
- SMA
- EMA
- SS
- MACD
- TR
- ATR
- DM
- ADX_DI
- Ichimoku
"""



## This function is used to calculate and return the RSI indicator.
def get_RSI(prices, time_values=None, rsiType=14, map_time=False):
    """ 
    This function uses 2 parameters to calculate the RSI-
    
    [PARAMETERS]
        prices  : The prices to be used.
        rsiType : The interval type.
    
    [CALCULATION]
        ---
    
    [RETURN]
        [
        float,
        float,
        ... ]
    """
    prices  = np.flipud(np.array(prices))
    deltas  = np.diff(prices)
    rsi     = np.zeros_like(prices)
    seed    = deltas[:rsiType+1]
    up      = seed[seed>=0].sum()/rsiType
    down    = abs(seed[seed<0].sum()/rsiType)
    rs      = up/down
    rsi[-1] = 100 - 100 /(1+rs)

    for i in range(rsiType, len(prices)):
        cDeltas = deltas[i-1]

        if cDeltas > 0:
            upVal = cDeltas
            downVal = 0
        else:
            upVal = 0
            downVal = abs(cDeltas)

        up = (up*(rsiType-1)+upVal)/rsiType
        down = (down*(rsiType-1)+downVal)/rsiType

        rs = up/down
        rsi[i] = 100 - 100 /(1+rs)

    fRSI = np.flipud(np.array(rsi[rsiType:]))

    fRSI.round(2)

    if map_time:
       fRSI = [ [ time_values[i], fRSI[i] ] for i in range(len(fRSI)) ]

    return fRSI


def get_stochastics(priceClose, priceHigh, priceLow, period=14):

    span = len(priceClose)-period
    stochastic = np.array([[priceHigh[i:period+i].max()-priceLow[i:period+i].min(), priceClose[i]-priceLow[i:period+i].min()] for i in range(span)])

    return stochastic



## This function is used to calculate and return SMA.
def get_SMA(prices, maPeriod, time_values=None, prec=8, map_time=False, result_format='normal'):
    """
    This function uses 3 parameters to calculate the Simple Moving Average-
    
    [PARAMETERS]
        prices  : A list of prices.
        ma_type : The interval type.
        ind_span: The span of the indicator.
    
    [CALCULATION]
        SMA = average of prices within a given period
    
    [RETURN]
        [
        float,
        float,
        ... ]
    """
    span = len(prices) - maPeriod + 1
    ma_list = np.array([np.mean(prices[i:(maPeriod+i)]) for i in range(span)])

    return_vals = ma_list.round(prec)

    if result_format == 'normal':
        return_vals = [ val for val in return_vals ]

    if map_time:
       return_vals = [ [ time_values[i], return_vals[i] ] for i in range(len(return_vals)) ]

    return return_vals


## This function is used to calculate and return EMA.
def get_EMA(prices, maPeriod, time_values=None, prec=8, map_time=False, result_format='normal'):
    """
    This function uses 3 parameters to calculate the Exponential Moving Average-
    
    [PARAMETERS]
        prices  : A list of prices.
        ma_type : The interval type.
        ind_span: The span of the indicator.
    
    [CALCULATION]
        weight = 2 / (maPerido + 1)
        EMA = ((close - prevEMA) * weight + prevEMA)
    
    [RETURN]
        [
        float,
        float,
        ... ]
    """
    span = len(prices) - maPeriod
    EMA = np.zeros_like(prices[:span])
    weight = (2 / (maPeriod +1))
    SMA = get_SMA(prices[span:], maPeriod, result_format='numpy')
    seed = SMA + weight * (prices[span-1] - SMA)
    EMA[0] = seed

    for i in range(1, span):
        EMA[i] = (EMA[i-1] + weight * (prices[span-i-1] - EMA[i-1]))

    return_vals = np.flipud(EMA.round(prec))

    if result_format == 'normal':
        return_vals = [ val for val in return_vals ]

    if map_time:
       return_vals = [ [ time_values[i], return_vals[i] ] for i in range(len(return_vals)) ]

    return return_vals


## This function is used to calculate and return Rolling Moving Average.
def get_RMA(prices, maPeriod, time_values=None, prec=8, map_time=False, result_format='normal'):
    """
    This function uses 3 parameters to calculate the Rolling Moving Average-
    
    [PARAMETERS]
        prices  : A list of prices.
        SS_type : The interval type.
        ind_span: The span of the indicator.
    
    [CALCULATION]
        RMA = ((prevRMA * (period - 1)) + currPrice) / period
    
    [RETURN]
        [
        float,
        float,
        ... ]
    """
    span = len(prices) - maPeriod
    SS = np.zeros_like(prices[:span])
    SMA = get_SMA(prices[span:], maPeriod)
    seed = ((SMA * (maPeriod-1)) + prices[span-1]) / maPeriod
    SS[0] = seed

    for i in range(1, span):
        SS[i] = ((SS[i-1] * (maPeriod-1)) + prices[span-i-1]) / maPeriod

    return_vals = np.flipud(SS.round(prec))

    if result_format == 'normal':
        return_vals = [ val for val in return_vals ]

    if map_time:
       return_vals = [ [ time_values[i], return_vals[i] ] for i in range(len(return_vals)) ]

    return return_vals


## This function is used to calculate and return the the MACD indicator.
def get_MACD(prices, time_values=None, Efast=12, Eslow=26, signal=9, map_time=False):
    """
    This function uses 5 parameters to calculate the Moving Average Convergence/Divergence-
    
    [PARAMETERS]
        prices  : A list of prices.
        Efast   : Fast line type.
        Eslow   : Slow line type.
        signal  : Signal line type.
    
    [CALCULATION]
        MACDLine = fastEMA - slowEMA
        SignalLine = EMA of MACDLine
        Histogram = MACDLine - SignalLine
    
    [RETURN]
        [{
        'fast':float,
        'slow':float,
        'his':float
        }, ... ]
    """
    fastEMA = get_EMA(prices, Efast)
    slowEMA = get_EMA(prices, Eslow)

    macdLine = np.subtract(fastEMA[:len(slowEMA)], slowEMA)
    signalLine = get_SMA(macdLine, signal)
    histogram = np.subtract(macdLine[:len(signalLine)], signalLine)

    macd = [({
        "macd":float("{0}".format(macdLine[i])), 
        "signal":float("{0}".format(signalLine[i])), 
        "hist":float("{0}".format(histogram[i]))}) for i in range(len(signalLine))]

    if map_time:
       macd = [ [ time_values[i], macd[i] ] for i in range(len(macd)) ]
       
    return(macd)



def get_DEMA(prices, maPeriod, prec=8):
    EMA1 = get_EMA(prices, maPeriod)
    EMA2 = get_EMA(EMA1, maPeriod)
    DEMA = np.subtract((np.dot(2,EMA1[:len(EMA2)])), EMA2)

    return DEMA.round(prec)



## This function is used to calculate and return the the MACD indicator.
def get_zeroLagMACD(prices, time_values=None, Efast=5, Eslow=35, signal=5, map_time=False):
    """
    This function uses 5 parameters to calculate the Moving Average Convergence/Divergence-

    Solution with thanks to @dsiens
    
    [PARAMETERS]
        prices  : A list of prices.
        Efast   : Fast line type.
        Eslow   : Slow line type.
        signal  : Signal line type.
    
    [CALCULATION]
        MACDLine = (2 * EMA(price, FAST) - EMA(EMA(price, FAST), FAST)) - (2 * EMA(price, SLOW) - EMA(EMA(price, SLOW), SLOW))
        SignalLine = 2 * EMA(MACD, SIG) - EMA(EMA(MACD, SIG), SIG))
        Histogram = MACDLine - SignalLine

    [RETURN]
        [{
        'fast':float,
        'slow':float,
        'his':float
        }, ... ]
    """
    z1 = get_DEMA(prices, Efast)
    z2 = get_DEMA(prices, Eslow)
    lineMACD = np.subtract (z1[:len(z2)], z2)
    lineSIGNAL = get_DEMA (lineMACD, signal)
    histogram = np.subtract(lineMACD[:len(lineSIGNAL)], lineSIGNAL)

    z_lag_macd = [({
        "macd":float("{0}".format(lineMACD[i])), 
        "signal":float("{0}".format(lineSIGNAL[i])), 
        "hist":float("{0}".format(histogram[i]))}) for i in range(len(lineSIGNAL))]

    if map_time:
       z_lag_macd = [ [ time_values[i], z_lag_macd[i] ] for i in range(len(z_lag_macd)) ]

    return(z_lag_macd)
