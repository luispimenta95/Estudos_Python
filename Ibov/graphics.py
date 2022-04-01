import pandas_datareader.data as web
import matplotlib.pyplot as plt
import time
import datetime
from matplotlib import dates as mpl_dates


import _datetime

now = _datetime.date.today()

year = now.year
month = now.month
day = now.day
start = datetime.datetime(2022, 3, 7)
end = datetime.datetime(year, month, day)
start = datetime.datetime(2022, 3, 7)
print(end)

tickers = ['WEGE3','MGLU3', 'ITSA4']

for item in tickers:
    time.sleep(1)
    date_format = mpl_dates.DateFormatter('%d/%m/%Y')
    plt.gca().xaxis.set_major_formatter(date_format)
    cotacao = web.DataReader(f'{item}.SA', 'yahoo', start, end)
    cotacao["Adj Close"].plot()
    plt.xlabel('Data')
    plt.ylabel('Fechamento')
    plt.title('Gráfico do ticker ' +item)
    plt.show(block=False)
    plt.pause(10)
    plt.close()