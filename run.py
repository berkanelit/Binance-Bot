#! /usr/bin/env python3
import os
import logging
from core import botCore

## Kurulum 
cwd = os.getcwd()
CACHE_DIR = 'cache/'.format(cwd)
LOGS_DIR = 'logs/'.format(cwd)

## Kurulum Girişi.
log_format = '%(asctime)s:%(name)s:%(message)s'
logging.basicConfig(
    format=log_format,
    level=logging.INFO)
logger = logging.getLogger()

SETTINGS_FILE_NAME = 'settings.conf'
DEFAULT_SETTINGS_DATA = '''# Public and Private key pais used for the for the trader
PUBLIC_KEY=
PRIVATE_KEY=

# İşlemcinin test modunda çalıştırılmasına izin verin (True/False).
IS_TEST=True

# Yatırımcının spot veya marj türünde çalışmasına izin verin.
MARKET_TYPE=SPOT

# Düşük olduğunda BNB bakiyesini otomatik olarak güncelleyin (ticaret ücretleri için, yalnızca gerçek ticaret için geçerlidir)
UPDATE_BNB_BALANCE=True

# Tüccar için kullanılan aralık (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d).
TRADER_INTERVAL=4h

# Yatırımcının kullanacağı maksimum para birimi (BTC olarak) ayrıca bunun piyasa sayısıyla arttığına dikkat edin, yani her piyasanın ticaret döviz çifti olarak 2 çifti 0,0015 olacaktır.TRADING_CURRENCY=0.002
TRADING_CURRENCY=100

# İşlem yapılacak piyasalar (şu anda sadece BTC piyasaları), çoklu piyasa işlemleri için piyasaları bir ile ayırır.
TRADING_MARKETS=BTC-ETH,BTC-LTC

# Web uygulaması için yapılandırma (boş bırakılırsa varsayılan IP=127.0.0.1, Bağlantı Noktası=5000)
HOST_IP=
HOST_PORT=

# Mum aralığı ve derinlik aralığı için konfigürasyon (eğer sol banka mum ise varsayılan=500, Derinlik=50)
MAX_CANDLES=
MAX_DEPTH=
'''


def settings_reader():
    # Ayarlar dosyası üzerinde ayrıştırmak ve kv çiftlerini toplamak için okuyucu işlevini ayarlama.

    ## Başlangıç ​​varsayılan değişkenleriyle kurulum ayarları dosya nesnesi.
    settings_file_data = {'public_key':'', 'private_key':'', 'host_ip':'127.0.0.1', 'host_port':5000, 'max_candles':500,'max_depth':50}

    ## Ayarlar dosyasını okuyun ve alanları çıkarın.
    with open(SETTINGS_FILE_NAME, 'r') as f:
        for line in f.readlines():

            ### kv hattını kontrol edin.
            if not('=' in line) or line[0] == '#':
                continue

            key, data = line.split('=')

            ### Verinin bir değeri olup olmadığını kontrol edin.
            if data == None or data == '\n':
                continue

            data = data.replace('\n', '')

            if key == 'IS_TEST':
                data = 'TEST' if data.upper() == 'TRUE' else 'REAL'
                key = 'run_type'

            elif key == 'MARKET_TYPE':
                data = data.upper()

            elif key == 'TRADING_MARKETS':
                data = data.replace(' ', '')
                data = data.split(',') if ',' in data else [data]

            elif key == 'HOST_IP':
                default_ip = '127.0.0.1'

            elif key == 'HOST_PORT':
                data = int(data)

            elif key == 'MAX_CANDLES':
                data = int(data)

            elif key == 'MAX_DEPTH':
                data = int(data)

            settings_file_data.update({key.lower():data})

    return(settings_file_data)


if __name__ == '__main__':

    ## Kontrol edin ve önbellek/günlükler dizini yapın.
    if not(os.path.exists(LOGS_DIR)):
        os.makedirs(LOGS_DIR, exist_ok=True)
    if not(os.path.exists(CACHE_DIR)):
        os.makedirs(CACHE_DIR, exist_ok=True)

    ## Ayarları yükle/ayar dosyası oluştur.
    if os.path.exists(SETTINGS_FILE_NAME):
        settings = settings_reader()
        botCore.start(settings, LOGS_DIR, CACHE_DIR)
    else:
        with open(SETTINGS_FILE_NAME, 'w') as f:
            f.write(DEFAULT_SETTINGS_DATA)
        print('Created settings.conf file.')

