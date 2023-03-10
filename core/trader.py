#! /usr/bin/env python3
import os
import sys
import copy
import time
import logging
import datetime
import threading
import trader_configuration as TC

MULTI_DEPTH_INDICATORS = ['ema', 'sma', 'rma']
TRADER_SLEEP = 1

# Binance ile taban komisyon ücreti.
COMMISION_FEE = 0.00075

# Piyasa fiyatlandırması için temel düzen.
BASE_TRADE_PRICE_LAYOUT = {
    'lastPrice':0,           # Piyasa için görülen son fiyat.
    'askPrice':0,            # Piyasa için görülen son satış fiyatı.
    'bidPrice':0             # Piyasa için görülen son teklif fiyatı.
}

# Base layout for trader state.
BASE_STATE_LAYOUT = {
    'base_currency':0.0,     # Referans olarak kullanılan temel mac değeri.
    'force_sell':False,      # Tüccar tüm jetonları atmalıysa.
    'runtime_state':None,    # Gerçek tüccar nesnesinin bulunduğu durum.
    'last_update_time':0     # En son tüccarın tam görünümü tamamlandı.
}

# Base layout used by the trader.
BASE_MARKET_LAYOUT = {
    'can_order':True,        # Bot mevcut piyasada işlem yapabiliyorsa.
    'price':0.0,             # SATIN AL ile ilgili fiyat.
    'buy_price':0.0,         # Varlığın satın alma fiyatı.
    'stopPrice':0.0,         # stopPrice ilişkisi
    'stopLimitPrice':0.0,    # stopPrice Limit ilişkisi
    'tokens_holding':0.0,    # Tutulan jeton miktarı.
    'order_point':None,      # Karmaşık strateji ilerleme noktalarını görselleştirmek için kullanılır.
    'order_id':None,         # Verilen siparişe bağlı olan kimlik.
    'order_status':0,        # Verilen siparişin türü
    'order_side':'BUY',      # Mevcut siparişin durumu.
    'order_type':'WAIT',     # Sipariş türünü göstermek için kullanılır
    'order_description':0,   # Siparişin açıklaması.
    'order_market_type':None,# Verilen emrin piyasa türü.
    'market_status':None     # Piyasa tüccarının son durumu.  
}

# Market extra required data.
TYPE_MARKET_EXTRA = {
    'loan_cost':0,           # Kredi maliyeti.
    'loan_id':None,          # Kredi kimliği.
}

class BaseTrader(object):
    def __init__(self, quote_asset, base_asset, rest_api, socket_api=None, data_if=None):
        # Ana tüccar nesnesini başlatın.
        symbol = '{0}{1}'.format(base_asset, quote_asset)

        ## Pazar sembolü için kolay yazdırılabilir format.
        self.print_pair = '{0}-{1}'.format(quote_asset, base_asset)
        self.quote_asset = quote_asset
        self.base_asset = base_asset

        logging.info('[BaseTrader][{0}] Tüccar nesnesi ve boş nitelikler başlatılıyor.'.format(self.print_pair))

        ## Tüccar tarafından kullanılacak kalan API'yi ayarlar.
        self.rest_api = rest_api

        if socket_api == None and data_if == None:
            logging.critical('[BaseTrader][{0}] Başlatma başarısız oldu, botta socket_api VEYA data_if ayarlanmış olmalıdır.'.format(self.print_pair))
            return

        ## Soket/veri arayüzünü kurun.
        self.data_if = None
        self.socket_api = None

        if socket_api:
            ### Canlı piyasa verileri ticareti için kurulum soketi.
            self.candle_enpoint = socket_api.get_live_candles
            self.depth_endpoint = socket_api.get_live_depths
            self.socket_api = socket_api
        else:
            ### Geçmiş ticaret için kurulum veri arayüzü.
            self.data_if = data_if
            self.candle_enpoint = data_if.get_candle_data
            self.depth_endpoint = data_if.get_depth_data

        ## İşlem gören piyasa tarafından tüccar için varsayılan yolu ayarlayın.
        self.orders_log_path = 'logs/order_{0}_log.txt'.format(symbol)
        self.configuration = {}
        self.market_prices = {}
        self.wallet_pair = None
        self.custom_conditional_data = {}
        self.indicators = {}
        self.market_activity = {}
        self.trade_recorder = []
        self.state_data = {}
        self.rules = {}

        logging.debug('[BaseTrader][{0}] Başlatılan tüccar nesnesi.'.format(self.print_pair))


    def setup_initial_values(self, trading_type, run_type, filters):
        # Tüccar değerlerini başlat.
        logging.info('[BaseTrader][{0}] Verilerle tüccar nesnesi öznitelikleri başlatılıyor.'.format(self.print_pair))

        ## Gerekli ayarları doldurun.
        self.configuration.update({
            'trading_type':trading_type,
            'run_type':run_type,
            'base_asset':self.base_asset,
            'quote_asset':self.quote_asset,
            'symbol':'{0}{1}'.format(self.base_asset, self.quote_asset)
        })
        self.rules.update(filters)

        ## Varsayılan değerleri başlat.
        self.market_activity.update(copy.deepcopy(BASE_MARKET_LAYOUT))
        self.market_prices.update(copy.deepcopy(BASE_TRADE_PRICE_LAYOUT))
        self.state_data.update(copy.deepcopy(BASE_STATE_LAYOUT))

        if trading_type == 'MARGIN':
            self.market_activity.update(copy.deepcopy(TYPE_MARKET_EXTRA))

        logging.debug('[BaseTrader][{0}] Verilerle birlikte tüccar öznitelikleri başlatıldı.'.format(self.print_pair))


    def start(self, MAC, wallet_pair, open_orders=None):
        '''
        Tüccarı başlatın.
        Gerektirir: MAC (İzin Verilen Maks. Para Birimi, tüccarın BTC'de işlem yapmasına izin verilen maksimum miktar).
        -> Önceki ticareti kontrol edin.
            Yakın zamanda kapatılmamış bir işlem görülürse veya sipariş vermek için minimum sürenin üzerinde hesapta kalan para birimi görülürse, tüccarı otomatik olarak satmaya ayarlayın.
        
        -> Tüccar dizisini başlatın.
            Her şey yolunda olduğunda tüccar, piyasanın izlenmesine izin vermek için iş parçacığını başlatacaktır.
        '''
        logging.info('[BaseTrader][{0}] Tüccar nesnesi başlatılıyor.'.format(self.print_pair))
        sock_symbol = self.base_asset+self.quote_asset

        if self.socket_api != None:
            while True:
                if self.socket_api.get_live_candles()[sock_symbol] and ('a' in self.socket_api.get_live_depths()[sock_symbol]):
                    break

        self.state_data['runtime_state'] = 'SETUP'
        self.wallet_pair = wallet_pair
        self.state_data['base_currency'] = float(MAC)

        ## Bir iş parçacığında tüccarın ana bölümünü başlatın.
        threading.Thread(target=self._main).start()
        return(True)


    def stop(self):
        ''' 
        Tüccarı durdur.
        -> Tüccar temizleme.
            Tüccarı zarafetle durdurmak ve iş parçacığını ve piyasa emirlerini temiz bir şekilde ortadan kaldırmak için.
        '''
        logging.debug('[BaseTrader][{0}] Tüccarın durduruldu.'.format(self.print_pair))

        self.state_data['runtime_state'] = 'STOP'
        return(True)


    def _main(self):
        '''
        Tüccar döngüsü için ana gövde.
        -> Mum verilerinin tüccara beslenmesini bekleyin.
            Mumun verilerle doldurulup doldurulmadığını kontrol etmek için sonsuz döngü,
        -> Güncelleyiciyi arayın.
            Güncelleyici, göstergeleri yeniden hesaplamanın yanı sıra zamanlı kontroller yapmak için kullanılır.
        -> Sipariş Yöneticisini arayın.
            Sipariş Yöneticisi, şu anda YERLEŞTİRİLMİŞ siparişleri kontrol etmek için kullanılır.
        -> Tüccar Yöneticisini arayın.
            Tüccar Yöneticisi, göstergelerin mevcut durumlarını kontrol etmek ve ardından YERLEŞTİRİLEBİLECEK olan emirleri ayarlamak için kullanılır.
        '''
        sock_symbol = self.base_asset+self.quote_asset
        last_wallet_update_time = 0

        if self.configuration['trading_type'] == 'SPOT':
            position_types = ['LONG']
        elif self.configuration['trading_type'] == 'MARGIN':
            position_types = ['LONG', 'SHORT']

        ## Ana tüccar döngüsü
        while self.state_data['runtime_state'] != 'STOP':
            # Tüccar için gerekli verileri çekin.
            candles = self.candle_enpoint(sock_symbol)
            books_data = self.depth_endpoint(sock_symbol)
            self.indicators = TC.technical_indicators(candles)
            indicators = self.strip_timestamps(self.indicators)

            logging.debug('[BaseTrader] Tüccar verileri toplandı. [{0}]'.format(self.print_pair))

            socket_buffer_symbol = None
            if self.configuration['run_type'] == 'REAL':

                if sock_symbol in self.socket_api.socketBuffer:
                    socket_buffer_symbol = self.socket_api.socketBuffer[sock_symbol]

                # küresel soket arabelleğini alın ve kullanılmış pazarlar için cüzdanları güncelleyin.
                socket_buffer_global = self.socket_api.socketBuffer
                if 'outboundAccountPosition' in socket_buffer_global:
                    if last_wallet_update_time != socket_buffer_global['outboundAccountPosition']['E']:
                        self.wallet_pair, last_wallet_update_time = self.update_wallets(socket_buffer_global)
            
            # Market fiyatlarını güncel verilerle güncelleyin
            if books_data != None:
                self.market_prices = {
                    'lastPrice':candles[0][4],
                    'askPrice':books_data['a'][0][0],
                    'bidPrice':books_data['b'][0][0]}

            # Sipariş vermek için yeterli kripto olup olmadığını kontrol edin.
            if self.state_data['runtime_state'] == 'PAUSE_INSUFBALANCE':
                if self.wallet_pair[self.quote_asset][0] > self.state_data['base_currency']:
                    self.state_data['runtime_state'] = 'RUN' 

            if not self.state_data['runtime_state'] in ['STANDBY', 'FORCE_STANDBY', 'FORCE_PAUSE']:
                ## Tüccarın daha gelişmiş yönetimi için kullanılabilecek özel koşullar için arayın.

                for market_type in position_types:
                    cp = self.market_activity

                    if cp['order_market_type'] != market_type and cp['order_market_type'] != None:
                        continue

                    ## Aktif siparişleri yönetmek için.
                    if socket_buffer_symbol != None or self.configuration['run_type'] == 'TEST':
                        cp = self._order_status_manager(market_type, cp, socket_buffer_symbol)
                        
                    ## Özel koşullu eylemleri kontrol etmek için
                    self.custom_conditional_data, cp = TC.other_conditions(
                        self.custom_conditional_data, 
                        cp,
                        self.trade_recorder,
                        market_type,
                        candles,
                        indicators, 
                        self.configuration['symbol'])

                    ## Siparişlerin yerleşimini/koşul kontrolünü yönetmek için.
                    if cp['can_order'] and self.state_data['runtime_state'] == 'RUN' and cp['market_status'] == 'TRADING':
                        if cp['order_type'] == 'COMPLETE':
                            cp['order_type'] = 'WAIT'

                        tm_data = self._trade_manager(market_type, cp, indicators, candles)
                        cp = tm_data if tm_data else cp

                    if not cp['market_status']: 
                        cp['market_status'] = 'TRADING'

                    self.market_activity = cp

                    time.sleep(TRADER_SLEEP)

            current_localtime = time.localtime()
            self.state_data['last_update_time'] = '{0}:{1}:{2}'.format(current_localtime[3], current_localtime[4], current_localtime[5])

            if self.state_data['runtime_state'] == 'SETUP':
                self.state_data['runtime_state'] = 'RUN'
        

    def _order_status_manager(self, market_type, cp, socket_buffer_symbol):
        '''
        Bu, tüm aktif siparişlerin yöneticisidir.
        -> Kontrol emirleri (Test/Gerçek).
            Bu, test emirleri için hem alım hem de satım tarafını kontrol eder ve tüccarı buna göre günceller.
        -> Ticaret sonuçlarını izleyin.
            İlerlemeyi takip etmek için işlemlerin sonucunu izleyin ve not edin.
        '''
        active_trade = False
        
        if self.configuration['run_type'] == 'REAL':
            # Soket üzerinden gönderilen sipariş raporlarını yönetin.
            if 'executionReport' in socket_buffer_symbol:
                order_seen = socket_buffer_symbol['executionReport']
                if order_seen['i'] == cp['order_id']:
                    active_trade = True         # Yapılan güncelleme makina özlü sistemle çalışır 

        else:
            # Test siparişleri için temel güncelleme.
            if cp['order_status'] == 'PLACED':
                active_trade = True
                order_seen = None

        trade_done = False
        if active_trade:
            # Bir siparişin mevcut durumunu belirleyin.
            if self.state_data['runtime_state'] == 'CHECK_ORDERS':
                self.state_data['runtime_state'] = 'RUN'
                cp['order_status'] = None
            cp, trade_done, token_quantity = self._check_active_trade(cp['order_side'], market_type, cp, order_seen)

        ## Ticaret sonuçlarını izleyin.
        if trade_done:
            print("Ticaret Güncelleniyor")
            if self.configuration['run_type'] == 'REAL':
                print('order seen: ')
                print(order_seen)

            # Sipariş kaydediciyi güncelleyin.
            self.trade_recorder.append([time.time(), cp['price'], token_quantity, cp['order_description'], cp['order_side']])
            logging.info('[BaseTrader] Completed {0} order. [{1}]'.format(cp['order_side'], self.print_pair))

            if cp['order_side'] == 'BUY':
                cp['order_side'] = 'SELL'
                cp['order_point'] = None
                cp['buy_price'] = self.trade_recorder[-1][1]

            elif cp['order_side'] == 'SELL':
                cp['order_side'] = 'BUY'
                cp['buy_price'] = 0.0
                cp['order_point'] = None
                cp['order_market_type'] = None

                # Tüccar ticaret marjıysa ve çalışma türü gerçekse, o zaman tüm kredileri geri ödeyin.
                if self.configuration['trading_type']  == 'MARGIN':
                    if self.configuration['run_type'] == 'REAL' and cp['loan_cost'] != 0:
                        loan_repay_result = self.rest_api.margin_accountRepay(asset=self.base_asset, amount=cp['loan_cost'])

                # Bir dosyaya yazdırmak için verileri biçimlendirin.
                trB = self.trade_recorder[-2]
                trS = self.trade_recorder[-1]

                buyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(trB[0]))
                sellTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(trS[0]))

                outcome = ((trS[1]-trB[1])*trS[2])

                trade_details = 'BuyTime:{0}, BuyPrice:{1:.8f}, BuyQuantity:{2:.8f}, BuyType:{3}, SellTime:{4}, SellPrice:{5:.8f}, SellQuantity:{6:.8f}, SellType:{7}, Outcome:{8:.8f}\n'.format(
                    buyTime, trB[1], trB[2], trB[3], sellTime, trS[1], trS[2], trS[3], outcome) # (Sellprice - Buyprice) * tokensSold
                with open(self.orders_log_path, 'a') as file:
                    file.write(trade_details)

                # Tüccar değişkenlerini sıfırlayın.
                cp['market_status']     = 'COMPLETE_TRADE'
            cp['order_type']        = 'COMPLETE'
            cp['price']             = 0.0
            cp['stopPrice']         = 0.0
            cp['stopLimitPrice']    = 0.0
            cp['order_id']          = None
            cp['order_status']      = None
            cp['order_description'] = None

        return(cp)


    def _check_active_trade(self, side, market_type, cp, order_seen):
        trade_done = False
        token_quantity = None

        if side == 'BUY':
            if self.configuration['run_type'] == 'REAL':
                if order_seen['S'] == 'BUY' or (market_type == 'SHORT' and order_seen['S'] == 'SELL'):
                    cp['price'] = float(order_seen['L'])

                    if market_type == 'LONG':
                        target_wallet = self.base_asset
                        target_quantity = float(order_seen['q'])
                    elif market_type == 'SHORT':
                        target_wallet = self.quote_asset
                        target_quantity = float(order_seen['q'])*float(order_seen['L'])

                    if order_seen['X'] == 'FILLED' and target_wallet in self.wallet_pair:
                        wallet_pair = self.wallet_pair
                        if wallet_pair[target_wallet][0] >= target_quantity:
                            trade_done = True
                            token_quantity = float(order_seen['q'])
                    elif order_seen['X'] == 'PARTIALLY_FILLED' and cp['order_status'] != 'LOCKED':
                        cp['order_status'] = 'LOCKED'
            else:
                if market_type == 'LONG':
                    trade_done = True if ((self.market_prices['lastPrice'] <= cp['price']) or (cp['order_type'] == 'MARKET')) else False
                elif market_type == 'SHORT':
                    trade_done = True if ((self.market_prices['lastPrice'] >= cp['price']) or (cp['order_type'] == 'MARKET')) else False
                token_quantity = cp['tokens_holding']

        elif side == 'SELL':
            if self.configuration['run_type'] == 'REAL':
                if order_seen['S'] == 'SELL' or (market_type == 'SHORT' and order_seen['S'] == 'BUY'):
                    if order_seen['X'] == 'FILLED':
                        cp['price'] = float(order_seen['L'])
                        token_quantity = float(order_seen['q'])
                        trade_done = True
                    elif order_seen['X'] == 'PARTIALLY_FILLED' and cp['order_status'] != 'LOCKED':
                        cp['order_status'] = 'LOCKED'
            else:
                if market_type == 'LONG':
                    if cp['order_type'] != 'STOP_LOSS_LIMIT':
                        trade_done = True if ((self.market_prices['lastPrice'] >= cp['price']) or (self.market_prices['lastPrice'] >= cp['stopLimitPrice']) or (cp['order_type'] == 'MARKET')) else False
                    else:
                        trade_done = True if (self.market_prices['lastPrice'] <= cp['price']) else False

                elif market_type == 'SHORT':
                    if cp['order_type'] != 'STOP_LOSS_LIMIT':
                        trade_done = True if ((self.market_prices['lastPrice'] <= cp['price']) or (cp['order_type'] == 'MARKET')) else False
                    else:
                        trade_done = True if (self.market_prices['lastPrice'] >= cp['price']) else False
                token_quantity = cp['tokens_holding']
        return(cp, trade_done, token_quantity)


    def _trade_manager(self, market_type, cp, indicators, candles):
        ''' 
        Burada hem satış hem de satın alma koşulları tüccar tarafından yönetilir.
        -
        '''


        # Giriş/çıkış koşullarını kontrol edin.

        ## Sipariş durumu kilitliyse geri dönün.
        if cp['order_status'] == 'LOCKED':
            return

        ## Dinamik olarak doğru koşullar işlevini seçin.
        if cp['order_side'] == 'SELL':
            current_conditions = TC.long_exit_conditions if market_type == 'LONG' else TC.short_exit_conditions

        elif cp['order_side'] == 'BUY':
            ### Bot donmaya zorlanırsa, satın alma iadesini önleyin.
            if self.state_data['runtime_state'] == 'FORCE_PREVENT_BUY':
                return

            current_conditions = TC.long_entry_conditions if market_type == 'LONG' else TC.short_entry_conditions


        # Durum kontrol sonuçlarını kontrol edin.
        logging.debug('[BaseTrader] Checking for {0} {1} condition. [{2}]'.format(cp['order_side'], market_type, self.print_pair))
        new_order = current_conditions(self.custom_conditional_data, cp, indicators,  self.market_prices, candles, self.print_pair)
                
        ## Yeni bir sipariş iade edilmezse, sadece iade edin.
        if not(new_order):
            return

        ## Sipariş noktasını güncelleyin.
        if 'order_point' in new_order:
            cp['order_point'] = new_order['order_point']

        order = None

        ## Yeni bir olası sipariş türü güncellemesini kontrol edin.
        if 'order_type' in new_order:

            ### Emir türü güncellemesi BEKLE değilse mevcut siparişi güncelleyin VEYA siparişi iptal edin.
            if new_order['order_type'] != 'WAIT':
                print(new_order)
                cp['order_description'] = new_order['description']

                #### Kullanılacak fiyatları biçimlendirin.
                if 'price' in new_order:
                    if 'price' in new_order:
                        new_order['price'] = '{0:.{1}f}'.format(float(new_order['price']), self.rules['TICK_SIZE'])
                    if 'stopPrice' in new_order:
                        new_order['stopPrice'] = '{0:.{1}f}'.format(float(new_order['stopPrice']), self.rules['TICK_SIZE'])

                    if float(new_order['price']) != cp['price']:
                        order = new_order
                else:
                    #### Emir türü değiştiyse VEYA yerleştirme fiyatı değiştiyse, siparişi yeni fiyat/tür ile güncelleyin.
                    if cp['order_type'] != new_order['order_type']:
                        order = new_order

            else:
                #### Siparişi iptal et.
                cp['order_status'] = None
                cp['order_type'] = 'WAIT'

                #### Yalnızca satın alma işlemi veya marj olarak 2 piyasa türüne izin veriliyorsa piyasa türünü sıfırlayın.
                if cp['order_side'] == 'BUY':
                    cp['order_market_type'] = None

                #### Yerleştirildiyse aktif siparişi iptal edin.
                if cp['order_id'] != None and new_order['order_type'] == 'WAIT':
                    cancel_order_results = self._cancel_order(cp['order_id'], cp['order_type'])
                    cp['order_id'] = None

                return(cp)

        # Yeni bir piyasa emri verin.
        if order:
            order_results = self._place_order(market_type, cp, order)
            logging.info('order: {0}\norder result:\n{1}'.format(order, order_results))

            # Sipariş yerleşiminden binance ile ilgili hatalar için hata tutamacı:
            if 'code' in order_results['data']:
                if order_results['data']['code'] == -2010:
                    self.state_data['runtime_state'] = 'PAUSE_INSUFBALANCE'
                elif order_results['data']['code'] == -2011:
                    self.state_data['runtime_state'] = 'CHECK_ORDERS'
                return

            logging.info('[BaseTrader] {0} Order placed for {1}.'.format(self.print_pair, new_order['order_type']))
            logging.info('[BaseTrader] {0} Order placement results:\n{1}'.format(self.print_pair, str(order_results['data'])))

            if 'type' in order_results['data']:
                if order_results['data']['type'] == 'MARKET':
                    price1 = order_results['data']['fills'][0]['price']
                else:
                    price1 = order_results['data']['price']
            else: price1 = None

            # Siparişin verildiği fiyatı belirleyin.
            price2 = None
            if 'price' in order:
                price2 = float(order['price'])
                if price1 == 0.0 or price1 == None: 
                    order_price = price2
                else: order_price = price1
            else: order_price = price1

            if 'stopPrice' in order:
                cp['stopPrice'] == ['stopPrice']

            # Test siparişi miktarını ayarlayın ve marj ticareti kredisini ayarlayın.
            if order['side'] == 'BUY':
                cp['order_market_type'] = market_type

                if self.configuration['run_type'] == 'REAL':
                    if self.configuration['trading_type'] == 'MARGIN' and 'loan_id' in order_results['data']:
                        cp['loan_id'] = order_results['data']['loan_id'] 
                        cp['loan_cost'] = order_results['data']['loan_cost']
                else:
                    cp['tokens_holding'] = order_results['data']['tester_quantity']

            # Gerçek işlemler için canlı sipariş kimliğini güncelleyin.
            if self.configuration['run_type'] == 'REAL':
                cp['order_id'] = order_results['data']['orderId']

            cp['price']         = float(order_price)
            cp['order_type']    = new_order['order_type']
            cp['order_status']  = 'PLACED'

            logging.info('type: {0}, status: {1}'.format(new_order['order_type'], cp['order_status']))
            return(cp)


    def _place_order(self, market_type, cp, order):
        ''' place order '''

        ## Uzun/kısa reel/test işlemleri için AL/SAT tarafı için miktar miktarını hesaplayın.
        quantity = None
        if order['side'] == 'BUY':
            quantity = float(self.state_data['base_currency'])/float(self.market_prices['bidPrice'])

        elif order['side'] == 'SELL':
            if 'order_prec' in order:
                quantity = ((float(order['order_prec']/100))*float(self.trade_recorder[-1][2]))
            else:
                quantity = float(self.trade_recorder[-1][2])

        if self.configuration['run_type'] == 'REAL' and cp['order_id']:
            cancel_order_results = self._cancel_order(cp['order_id'], cp['order_type'])
            if 'code' in cancel_order_results:
                return({'action':'ORDER_ISSUE', 'data':cancel_order_results})

        ## Miktarı doğru kesinlik olacak şekilde ayarlayın.
        if quantity:
            split_quantity = str(quantity).split('.')
            f_quantity = float(split_quantity[0]+'.'+split_quantity[1][:self.rules['LOT_SIZE']])

        logging.info('Order: {0}'.format(order))

        ## Her iki TEST/GERÇEK çalıştırma türü için her iki SATIŞ/ALINMA tarafı için sipariş verin.
        if self.configuration['run_type'] == 'REAL':
            rData = {}
            ## Sipariş kısa ise AL'ı SAT'a dönüştürün (kısa siparişler için)
            if market_type == 'LONG':
                side = order['side']
            elif market_type == 'SHORT':
                if order['side'] == 'BUY':
                    ## Kısa bir kredi için gereken miktarı hesaplayın.
                    loan_get_result = self.rest_api.margin_accountBorrow(asset=self.base_asset, amount=f_quantity)
                    rData.update({'loan_id':loan_get_result['tranId'], 'loan_cost':f_quantity})
                    side = 'SELL'
                else:
                    side = 'BUY'

            if order['order_type'] == 'OCO_LIMIT':
                logging.info('[BaseTrader] symbol:{0}, side:{1}, type:{2}, quantity:{3} price:{4}, stopPrice:{5}, stopLimitPrice:{6}'.format(self.print_pair, order['side'], order['order_type'], f_quantity,order['price'], order['stopPrice'], order['stopLimitPrice']))
                rData.update(self.rest_api.place_order(self.configuration['trading_type'], symbol=self.configuration['symbol'], side=side, type=order['order_type'], timeInForce='GTC', quantity=f_quantity, price=order['price'], stopPrice=order['stopPrice'], stopLimitPrice=order['stopLimitPrice']))
                return({'action':'PLACED_MARKET_ORDER', 'data':rData})

            elif order['order_type'] == 'MARKET':
                logging.info('[BaseTrader] symbol:{0}, side:{1}, type:{2}, quantity:{3}'.format(self.print_pair, order['side'], order['order_type'], f_quantity))
                rData.update(self.rest_api.place_order(self.configuration['trading_type'], symbol=self.configuration['symbol'], side=side, type=order['order_type'], quantity=f_quantity))
                return({'action':'PLACED_MARKET_ORDER', 'data':rData})

            elif order['order_type'] == 'LIMIT':
                logging.info('[BaseTrader] symbol:{0}, side:{1}, type:{2}, quantity:{3} price:{4}'.format(self.print_pair, order['side'], order['order_type'], f_quantity, order['price']))
                rData.update(self.rest_api.place_order(self.configuration['trading_type'], symbol=self.configuration['symbol'], side=side, type=order['order_type'], timeInForce='GTC', quantity=f_quantity, price=order['price']))
                return({'action':'PLACED_LIMIT_ORDER', 'data':rData})

            elif order['order_type'] == 'STOP_LOSS_LIMIT':
                logging.info('[BaseTrader] symbol:{0}, side:{1}, type:{2}, quantity:{3} price:{4}, stopPrice:{5}'.format(self.print_pair, order['side'], order['order_type'], f_quantity, order['price'], order['stopPrice']))
                rData.update(self.rest_api.place_order(self.configuration['trading_type'], symbol=self.configuration['symbol'], side=side, type=order['order_type'], timeInForce='GTC', quantity=f_quantity, price=order['price'], stopPrice=order['stopPrice']))
                return({'action':'PLACED_STOPLOSS_ORDER', 'data':rData})

        else:
            placed_order = {'type':'test', 'price':0, 'tester_quantity':float(f_quantity)}
            
            if order['order_type'] == 'OCO_LIMIT':
                placed_order.update({'stopPrice':order['stopPrice'], 'stopLimitPrice':order['stopLimitPrice']})

            if order['order_type'] == 'MARKET':
                placed_order.update({'price':self.market_prices['lastPrice']})
            else:
                placed_order.update({'price':order['price']})

            return({'action':'PLACED_TEST_ORDER', 'data':placed_order})


    def _cancel_order(self, order_id, order_type):
        ''' cancel orders '''
        if self.configuration['run_type'] == 'REAL':
            if order_type == 'OCO_LIMIT':
                cancel_order_result = self.rest_api.cancel_oco_order(symbol=self.configuration['symbol'])
            else:
                cancel_order_result = self.rest_api.cancel_order(self.configuration['trading_type'], symbol=self.configuration['symbol'], orderId=order_id)
            logging.debug('[BaseTrader] {0} cancel order results:\n{1}'.format(self.print_pair, cancel_order_result))
            return(cancel_order_result)
        logging.debug('[BaseTrader] {0} cancel order.'.format(self.print_pair))
        return(True)


    def get_trader_data(self):
        ''' Access that is availble for the traders details. '''
        trader_data = {
            'market':self.print_pair,
            'configuration':self.configuration,
            'market_prices':self.market_prices,
            'wallet_pair':self.wallet_pair,
            'custom_conditions':self.custom_conditional_data,
            'market_activity':self.market_activity,
            'trade_recorder':self.trade_recorder,
            'state_data':self.state_data,
            'rules':self.rules
        }

        return(trader_data)


    def strip_timestamps(self, indicators):

        base_indicators = {}

        for ind in indicators:
            if ind in MULTI_DEPTH_INDICATORS:
                base_indicators.update({ind:{}})
                for sub_ind in indicators[ind]:
                    base_indicators[ind].update({sub_ind:[ val[1] for val in indicators[ind][sub_ind] ]})
            else:
                base_indicators.update({ind:[ val[1] for val in indicators[ind] ]})

        return(base_indicators)


    def update_wallets(self, socket_buffer_global):
        ''' M-cüzdan verilerini soket aracılığıyla toplanan verilerle güncelleyin '''
        last_wallet_update_time = socket_buffer_global['outboundAccountPosition']['E']
        foundBase = False
        foundQuote = False
        wallet_pair = {}

        for wallet in socket_buffer_global['outboundAccountPosition']['B']:
            if wallet['a'] == self.base_asset:
                wallet_pair.update({self.base_asset:[float(wallet['f']), float(wallet['l'])]})
                foundBase = True
            elif wallet['a'] == self.quote_asset:
                wallet_pair.update({self.quote_asset:[float(wallet['f']), float(wallet['l'])]})
                foundQuote = True

            if foundQuote and foundBase:
                break

        if not(foundBase):
            wallet_pair.update({self.base_asset:[0.0, 0.0]})
        if not(foundQuote):
            wallet_pair.update({self.quote_asset:[0.0, 0.0]})

        logging.info('[BaseTrader] Yeni hesap verileri çekildi, cüzdanlar güncellendi. [{0}]'.format(self.print_pair))
        return(wallet_pair, last_wallet_update_time)