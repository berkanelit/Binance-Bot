import numpy as np

def get_SMA(prices, maPeriod, time_values=None, prec=8, map_time=False, result_format='normal'):

    span = len(prices) - maPeriod + 1
    ma_list = np.array([np.mean(prices[i:(maPeriod+i)]) for i in range(span)])

    return_vals = ma_list.round(prec)

    if result_format == 'normal':
        return_vals = [ val for val in return_vals ]

    if map_time:
       return_vals = [ [ time_values[i], return_vals[i] ] for i in range(len(return_vals)) ]

    return return_vals

def get_EMA(prices, maPeriod, time_values=None, prec=8, map_time=False, result_format='normal'):
    
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

def get_DEMA(prices, maPeriod, prec=8):
    EMA1 = get_EMA(prices, maPeriod)
    EMA2 = get_EMA(EMA1, maPeriod)
    DEMA = np.subtract((np.dot(2,EMA1[:len(EMA2)])), EMA2)

    return DEMA.round(prec)

def get_zeroLagMACD(prices, time_values=None, Efast=12, Eslow=26, signal=9, map_time=False):

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