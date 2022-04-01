import pandas as pd # Para evitar escrever pandas e trocar pela escrita apenas de pd para facilitar
from pandas_datareader import data as web # Evita a escrita do data e troca pelo web
import matplotlib.pyplot as plt
import _datetime
import datetime
import locale

now = _datetime.date.today()

year = now.year
month = now.month
day = now.day

start = datetime.datetime(2022, 3, 7)
end = datetime.datetime(year, month, day)
empresas_df = pd.read_excel("Empresas.xlsx")

for empresa in empresas_df['Empresa']:
    df = web.DataReader(f'{empresa}.SA', data_source='yahoo', start=start, end=end)
    pd = web.DataReader(f'{empresa}.SA', data_source='yahoo', start=end, end=end)
    df["Adj Close"].plot(figsize=(15, 10))
    preco_dia = pd["Adj Close"]
    """plt.xlabel('Data')
    plt.ylabel('Fechamento')
    plt.title('Gráfico do ticker ' +empresa)
    plt.show()
    plt.pause(3)
    plt.close()"""
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')
    print(str(locale.currency(pd["Adj Close"], grouping=True)))
