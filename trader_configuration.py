import logging
import numpy as np
import time
import technical_indicators as TI

## Minimum fiyat yuvarlama.
pRounding = 8

def technical_indicators(candles):
    indicators = {}

    time_values     = [candle[0] for candle in candles]
    open_prices     = [candle[1] for candle in candles]
    high_prices     = [candle[2] for candle in candles]
    low_prices      = [candle[3] for candle in candles]
    close_prices    = [candle[4] for candle in candles]

    
    indicators.update({'macd':TI.get_zeroLagMACD(open_prices, time_values=time_values, map_time=True)})
    
    indicators.update({'hist':TI.get_zeroLagMACD(close_prices, time_values=time_values, map_time=True)})
    
    indicators.update({'ema':{}})
    indicators['ema'].update({'ema25':TI.get_EMA(open_prices, 25, time_values=time_values, map_time=True)})
    

    return(indicators)



def other_conditions(custom_conditional_data, trade_information, previous_trades, position_type, candles, indicators, symbol):
    # Varsayılanları tanımlayın.
    can_order = True

    # Ticaret için ek ekstra koşullar ayarlayın.
    if trade_information['market_status'] == 'COMPLETE_TRADE':
        trade_information['market_status'] = 'TRADING'

    trade_information.update({'can_order':can_order})
    return(custom_conditional_data, trade_information)


def long_exit_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    # Uzun çıkış (satış) koşullarını bu bölüme yerleştirin.
    order_point = 0
    signal_id = 0
    macd = indicators['macd']
    

    if macd[1]['signal'] < macd[1]['macd']:
     if macd[0]['signal'] > macd[0]['macd']:
        order_point += 1
        if macd[0]['hist'] < macd[1]['hist']:
            print("Satıyor...========================================================================================")
            return({'side':'SELL',
                'description':'Sat Sinyali Verildi.', 
                'order_type':'MARKET'})
    price = float('{0:.{1}f}'.format((trade_information['buy_price']+(trade_information['buy_price']*0.03)), pRounding))
    
    if float(prices['lastPrice']) >= price:
        return({'side':'SELL',
        'description':'Karlı Satış işlemi Gerçekleşti.', 
        'order_type':'MARKET'})
        
    if macd[0]['hist'] < macd[1]['hist']:
        return({'side':'SELL',
        'description':'Temnkinlli Satış işlemi Gerçekleşti.', 
        'order_type':'MARKET'})

    stop_loss_price = float('{0:.{1}f}'.format((trade_information['buy_price']-(trade_information['buy_price']*0.02)), pRounding))
    stop_loss_price2 = float('{0:.{1}f}'.format((trade_information['buy_price']-(trade_information['buy_price']*0.021)), pRounding))
    stop_loss_status = basic_stoploss_setup(trade_information, stop_loss_price2, stop_loss_price)
    
    
    # Bekleyen ve güncellenen emir pozisyonları için baz dönüş.
    if stop_loss_status:
        return(stop_loss_status)
    else:
        return({'order_point':'L_ext_{0}_{1}'.format(signal_id, order_point)})

def long_entry_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    # Uzun giriş (satın alma) koşullarını bu bölüme yerleştirin.
    order_point = 0
    signal_id = 0
    macd = indicators['macd']
    ema25 = indicators['ema']['ema25']
    macd2 = indicators['hist']
    
    if macd[1]['signal'] > macd[1]['macd']:
     if macd[0]['signal'] < macd[0]['macd']:
        order_point += 1
        if macd2[0]['hist'] > macd2[1]['hist']:
         if macd[0]['hist'] > macd[1]['hist']:
            print("Alıyor==========================================================================================")
            return({'side':'BUY',
                    'description':'Alım Sinyali Verildi.', 
                    'order_type':'MARKET'})

    # Bekleyen ve güncellenen emir pozisyonları için baz dönüş.
    if order_point == 0:
        return({'order_type':'WAIT'})
    else:
        return({'order_type':'WAIT', 'order_point':'L_ent_{0}_{1}'.format(signal_id, order_point)})

def basic_stoploss_setup(trade_information, price, stop_price):
    # Temel stop-loss kurulumu.
    if trade_information['order_type'] == 'STOP_LOSS_LIMIT':
        return
    print("Stop Los Göderiliyor=========================================================================")
    return({'side':'SELL', 
        'price':price,
        'stopPrice':stop_price,
        'description':'STOP LOSS çıkışı Gerçekleşti.', 
        'order_type':'STOP_LOSS_LIMIT'})
    
def short_exit_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    pass

def short_entry_conditions(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    pass
