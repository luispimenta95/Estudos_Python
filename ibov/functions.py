import requests
import calendar
from dotenv import load_dotenv
from datetime import datetime
import os
import time
import yfinance as yf

from binance.client import Client
import financeiro, rendimentos

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BINANCE_KEY = os.getenv("BINANCE_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

# =============================
# TELEGRAM
# =============================

def sendMessageTelegram(mensagem):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }

    response = requests.post(url, data=payload)

    if response.status_code != 200:
        print("Erro ao enviar mensagem:", response.text)


# =============================
# CONTROLE DE EXECUÇÃO
# =============================

def deve_executar():

    hoje = datetime.today()
    dia = hoje.day

    dia_execucao = 15
    data_15 = datetime(hoje.year, hoje.month, dia_execucao)

    if data_15.weekday() == 5:
        dia_execucao = 14
    elif data_15.weekday() == 6:
        dia_execucao = 13

    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    data_final = datetime(hoje.year, hoje.month, ultimo_dia)

    dia_execucao_final = ultimo_dia

    if data_final.weekday() == 5:
        dia_execucao_final = ultimo_dia - 1
    elif data_final.weekday() == 6:
        dia_execucao_final = ultimo_dia - 2

    #return dia == dia_execucao or dia == dia_execucao_final
    return True

# =============================
# BINANCE
# =============================

def getClientBinance():

    client = Client(BINANCE_KEY, BINANCE_SECRET)

    server_time = client.get_server_time()
    client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)

    return client


def get_binance_assets():

    client = getClientBinance()

    conta = client.get_account(recvWindow=10000)
    saldos = conta['balances']

    ativos = []
    total_usd = 0

    for ativo in saldos:

        qtd = float(ativo['free']) + float(ativo['locked'])

        if qtd <= 0.0001:
            continue

        symbol = ativo['asset']

        if symbol in ['USDT', 'USDC', 'BUSD', 'DAI']:
            valor_usd = qtd
        else:

            try:
                price = float(client.get_avg_price(symbol=f"{symbol}USDT")['price'])
                valor_usd = qtd * price
            except:
                continue

        total_usd += valor_usd

        ativos.append({
            "moeda": symbol,
            "quantidade": qtd,
            "valor_usd": valor_usd
        })

    return ativos, total_usd


# =============================
# DÓLAR
# =============================

def get_dolar():

    dolar_raw = yf.download(
        "USDBRL=X",
        period="1d",
        auto_adjust=True,
        progress=False
    )["Close"]

    try:
        return float(
            dolar_raw.iloc[-1].item()
            if hasattr(dolar_raw.iloc[-1], 'item')
            else dolar_raw.iloc[-1]
        )
    except:
        return 5.0


# =============================
# BOLSA
# =============================

def get_valor_bolsa():

    tickers = list(financeiro.carteira.keys())

    dados = yf.download(
        tickers,
        period="1d",
        auto_adjust=True,
        progress=False
    )["Close"]

    total = 0

    for ticker, info in financeiro.carteira.items():

        qtd = info["quantidade"]

        try:

            if len(tickers) > 1:
                preco_raw = dados[ticker].iloc[-1]
            else:
                preco_raw = dados.iloc[-1]

            preco = float(preco_raw.item() if hasattr(preco_raw, 'item') else preco_raw)

        except:
            preco = 0

        total += preco * qtd

    return total


# =============================
# RELATÓRIO
# =============================

def gerar_relatorio():

    nome_cliente = "Luis Felipe"
    data_atual = datetime.now().strftime("%d/%m/%Y")

    total_bolsa = get_valor_bolsa()

    valor_cdb = financeiro.cdb

    ativos_binance, total_usd_binance = get_binance_assets()

    cotacao_dolar = get_dolar()

    valor_crypto_brl = total_usd_binance * cotacao_dolar

    total_carteira = total_bolsa + valor_cdb + valor_crypto_brl

    total_rendimentos = sum(
        valor
        for info in rendimentos.rendimentos.values()
        for _, _, valor in info["itens"]
    )

    total_aportes = sum(valor for _, valor in financeiro.aportes)

    lucro_real = total_bolsa - total_aportes

    return {
        "nome": nome_cliente,
        "data": data_atual,
        "bolsa": total_bolsa,
        "cdb": valor_cdb,
        "crypto": valor_crypto_brl,
        "ativos_binance": ativos_binance,
        "usd_total": total_usd_binance,
        "dolar": cotacao_dolar,
        "total": total_carteira,
        "rendimentos": total_rendimentos,
        "aportes": total_aportes,
        "lucro": lucro_real
    }


# =============================
# MENSAGEM
# =============================

def montar_mensagem(d):

    percentual_bolsa = d["bolsa"] / d["total"] * 100
    percentual_cdb = d["cdb"] / d["total"] * 100
    percentual_crypto = d["crypto"] / d["total"] * 100

    aporte2 = d["total"] * 0.02
    aporte4 = d["total"] * 0.04
    aporte8 = d["total"] * 0.08
    aporte10 = d["total"] * 0.10

    texto_binance = f"💵 Cotação do dólar: R$ {d['dolar']:,.2f}\n\n"

    for ativo in d["ativos_binance"]:

        valor_brl = ativo["valor_usd"] * d["dolar"]
        percentual = valor_brl / d["total"] * 100

        texto_binance += (
            f"• {ativo['moeda']}: {ativo['quantidade']:.4f} | "
            f"$ {ativo['valor_usd']:,.2f} | "
            f"R$ {valor_brl:,.2f} | "
            f"{percentual:.2f}%\n"
        )

    mensagem = (
        f"Olá {d['nome']}, segue seu patrimônio atualizado:\n\n"
        f"📅 {d['data']}\n\n"

        f"💰 Bolsa: R$ {d['bolsa']:,.2f} ({percentual_bolsa:.2f}%)\n"
        f"💰 CDB 02/2031: R$ {d['cdb']:,.2f} ({percentual_cdb:.2f}%)\n"
        f"🌎 Cripto / Dólar: R$ {d['crypto']:,.2f} ({percentual_crypto:.2f}%)\n\n"

        f"{texto_binance}\n"

        f"💵 Total de dólares: $ {d['usd_total']:,.2f}\n"
        f"💵 Em Reais: R$ {d['crypto']:,.2f}\n\n"

        f"📥 Aportes Bolsa: R$ {d['aportes']:,.2f}\n"
        f"📈 Dividendos: R$ {d['rendimentos']:,.2f}\n"
        f"💵 Lucro valorização ativos: R$ {d['lucro']:,.2f}\n\n"

        f"📊 PATRIMÔNIO TOTAL: R$ {d['total']:,.2f}\n\n"

        f"💡 Sugestão de aportes:\n"
        f"• 2% da carteira: R$ {aporte2:,.2f}\n"
        f"• 4% da carteira: R$ {aporte4:,.2f}\n"
        f"• 8% da carteira: R$ {aporte8:,.2f}\n"
        f"• 10% da carteira: R$ {aporte10:,.2f}"
    )

    return mensagem
