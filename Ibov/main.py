import requests
import locale
import time
from datetime import datetime as dt

while True:
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')
    request = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL,BTC-BRL,ETH-BRL")
    req = request.json()
    V_dolar = float(req["USDBRL"]["bid"])
    V_euro = float(req["EURBRL"]["bid"])
    V_btc = float(req["BTCBRL"]["bid"]) *1000
    #V_eth = float(req["ETHBRL"]["bid"]) *10

    coins = dict()
    coins['Bitcoin'] = str(locale.currency(V_btc, grouping=True))
    coins['Dolar'] = str(locale.currency(V_dolar, grouping=True))
    coins['Euro'] = str(locale.currency(V_euro, grouping=True))
    dia= dt.now()
    dia = dia.strftime("%d/%m/%Y %H:%M")
    print('\nCotação atualizada em ' +dia +'\n')
    for item in coins:
        print("Valor do "+item + " : "+ coins[item])
time.sleep(60)