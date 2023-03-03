import logging
import numpy as np
import technical_indicators as TI

## Minimum price rounding.
pRounding = 8

def technical_indicators(candles):
    indicators = {}

    time_values     = [candle[0] for candle in candles]
    open_prices     = [candle[1] for candle in candles]
    high_prices     = [candle[2] for candle in candles]
    low_prices      = [candle[3] for candle in candles]
    close_prices    = [candle[4] for candle in candles]

    
    indicators.update({'macd':TI.get_MACD(close_prices, time_values=time_values, map_time=True)})
    
    indicators.update({'ema':{}})
    indicators['ema'].update({'ema40':TI.get_EMA(close_prices, 40, time_values=time_values, map_time=True)})
    

    return(indicators)



def other_conditions(custom_conditional_data, trade_information, previous_trades, position_type, candles, indicators, symbol):
    # Define defaults.
    can_order = True

    # Setup additional extra conditions for trading.
    if trade_information['market_status'] == 'COMPLETE_TRADE':
        trade_information['market_status'] = 'TRADING'

    trade_information.update({'can_order':can_order})
    return(custom_conditional_data, trade_information)


def long_exit_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    # Place Long exit (sell) conditions under this section.
    order_point = 0
    signal_id = 0
    macd = indicators['macd']

    if macd[0]['signal'] > macd[0]['macd']:
        order_point += 1
        print("Aha Satıyor Vallaha :O")
        if macd[0]['hist'] < macd[1]['hist']:
            return({'side':'SELL',
                'description':'LONG exit signal 1', 
                'order_type':'MARKET'})

    stop_loss_price = float('{0:.{1}f}'.format((trade_information['buy_price']-(trade_information['buy_price']*0.004)), pRounding))
    stop_loss_status = basic_stoploss_setup(trade_information, stop_loss_price, stop_loss_price, 'LONG')
    
    limit_loss_price = float('{0:.{1}f}'.format((trade_information['buy_price']+(trade_information['buy_price']*0.01)), pRounding))
    limit_loss_status = basic_limit_setup(trade_information, limit_loss_price)

    # Base return for waiting and updating order positions.
    if stop_loss_status:
        return(stop_loss_status)
    if limit_loss_price == prices:
        return(limit_loss_status)
    else:
        return({'order_point':'L_ext_{0}_{1}'.format(signal_id, order_point)})
    
def long_entry_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    # Place Long entry (buy) conditions under this section.
    order_point = 0
    signal_id = 0
    macd = indicators['macd']
    ema40 = indicators['ema']['ema40']

    if macd[0]['signal'] < macd[0]['macd']:
        order_point += 1
        print("Aha Gördü Vallaha :D")
        if macd[0]['hist'] > macd[1]['hist']:
            return({'side':'BUY',
                    'description':'LONG entry signal 1', 
                    'order_type':'MARKET'})

    # Base return for waiting and updating order positions.
    if order_point == 0:
        return({'order_type':'WAIT'})
    else:
        return({'order_type':'WAIT', 'order_point':'L_ent_{0}_{1}'.format(signal_id, order_point)})

def basic_stoploss_setup(trade_information, price, stop_price, position_type):
    # Basic stop-loss setup.
    if trade_information['order_type'] == 'STOP_LOSS_LIMIT':
        return

    return({'side':'SELL', 
        'price':price,
        'stopPrice':stop_price,
        'description':'{0} exit stop-loss'.format(position_type), 
        'order_type':'STOP_LOSS_LIMIT'})
    
def basic_limit_setup(trade_information, position_type):
    if trade_information['order_type'] == 'MARKET':
        return
    
    return({'side':'SELL',
        'description':'{0} exit stop-loss'.format(position_type), 
        'order_type':'MARKET'})
    


def short_exit_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    pass

def short_entry_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    pass


