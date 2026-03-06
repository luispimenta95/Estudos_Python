import yfinance as yf
from datetime import datetime
import os
import time
import sys
import calendar
from ibov.pessoal import financeiro, rendimentos
import functions
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

# =============================
# CONTROLE DE EXECUÇÃO POR DATA
# =============================

def deve_executar():

    hoje = datetime.today()
    dia = hoje.day

    # --- regra dia 15 ---
    dia_execucao_15 = 15
    data_15 = datetime(hoje.year, hoje.month, 15)

    if data_15.weekday() == 5:
        dia_execucao_15 = 14
    elif data_15.weekday() == 6:
        dia_execucao_15 = 13

    # --- ultimo dia do mês ---
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    data_final = datetime(hoje.year, hoje.month, ultimo_dia)

    dia_execucao_final = ultimo_dia

    if data_final.weekday() == 5:
        dia_execucao_final = ultimo_dia - 1
    elif data_final.weekday() == 6:
        dia_execucao_final = ultimo_dia - 2

    if dia == dia_execucao_15 or dia == dia_execucao_final:
        return True

    return False


if not deve_executar():
    print("Hoje não é dia de execução do relatório.")
    sys.exit()

# =============================
# Configurações iniciais
# =============================

nome_cliente = 'Luis Felipe'
data_atual = datetime.now().strftime("%d/%m/%Y")

# === Binance ===
api_key = os.getenv('BINANCE_KEY')
api_secret = os.getenv('BINANCE_SECRET')

client_binance = Client(api_key, api_secret)

# Sincroniza horário para evitar erro -1021
server_time = client_binance.get_server_time()
client_binance.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)

# === Busca Cotações Bolsa ===
tickers = list(financeiro.carteira.keys())
dados_download = yf.download(tickers, period="1d", auto_adjust=True, progress=False)["Close"]

# === Busca Cotação Dólar ===
dolar_raw = yf.download("USDBRL=X", period="1d", auto_adjust=True, progress=False)["Close"]

try:
    cotacao_dolar = float(dolar_raw.iloc[-1].item() if hasattr(dolar_raw.iloc[-1], 'item') else dolar_raw.iloc[-1])
except:
    cotacao_dolar = 5.0


# =============================
# BINANCE
# =============================

def get_binance_assets():

    conta = client_binance.get_account(recvWindow=10000)
    saldos = conta['balances']

    ativos = []
    total_usd = 0.0

    for ativo in saldos:

        qtd = float(ativo['free']) + float(ativo['locked'])

        if qtd <= 0.0001:
            continue

        symbol = ativo['asset']

        if symbol in ['USDT', 'USDC', 'BUSD', 'DAI']:
            valor_usd = qtd
        else:
            try:
                price = float(client_binance.get_avg_price(symbol=f"{symbol}USDT")['price'])
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


ativos_binance, total_usd_binance = get_binance_assets()
valor_dolares_reais = total_usd_binance * cotacao_dolar


# =============================
# Cálculo Bolsa
# =============================

total_atual_bolsa = 0.0

for ticker, info in financeiro.carteira.items():

    qtd = info["quantidade"]

    try:

        if len(tickers) > 1:
            preco_raw = dados_download[ticker].iloc[-1]
        else:
            preco_raw = dados_download.iloc[-1]

        preco = float(preco_raw.item() if hasattr(preco_raw, 'item') else preco_raw)

    except:
        preco = 0

    total_atual_bolsa += preco * qtd


# =============================
# Patrimônio
# =============================

valor_cdb = financeiro.cdb

total_carteira = total_atual_bolsa + valor_cdb + valor_dolares_reais


# =============================
# Percentuais
# =============================

percentual_bolsa = (total_atual_bolsa / total_carteira * 100) if total_carteira > 0 else 0
percentual_cdb = (valor_cdb / total_carteira * 100) if total_carteira > 0 else 0
percentual_crypto = (valor_dolares_reais / total_carteira * 100) if total_carteira > 0 else 0


# =============================
# Texto Binance
# =============================

texto_binance = f"💵 Cotação do dólar: R$ {cotacao_dolar:,.2f}\n\n"

for ativo in ativos_binance:

    valor_brl = ativo["valor_usd"] * cotacao_dolar

    percentual_ativo = (valor_brl / total_carteira * 100) if total_carteira > 0 else 0

    texto_binance += (
        f"• {ativo['moeda']}: {ativo['quantidade']:.4f} | "
        f"$ {ativo['valor_usd']:,.2f} | "
        f"R$ {valor_brl:,.2f} | "
        f"{percentual_ativo:.2f}%\n"
    )


# =============================
# Rendimentos
# =============================

total_rendimentos = sum(
    valor
    for info in rendimentos.rendimentos.values()
    for _, _, valor in info["itens"]
)

total_aportes = sum(valor for _, valor in financeiro.aportes)

lucro_real_bolsa = total_atual_bolsa - total_aportes


# =============================
# Mensagem
# =============================

mensagem = (
    f"Olá {nome_cliente}, seu patrimônio atualizado:\n\n"
    f"📅 {data_atual}\n\n"

    f"💰 Bolsa: R$ {total_atual_bolsa:,.2f} ({percentual_bolsa:.2f}%)\n"
    f"💰 CDB 02/2031: R$ {valor_cdb:,.2f} ({percentual_cdb:.2f}%)\n"
    f"🌎 Cripto / Dólar: R$ {valor_dolares_reais:,.2f} ({percentual_crypto:.2f}%)\n\n"

    f"{texto_binance}\n"

    f"💵 Total de dólares: $ {total_usd_binance:,.2f}\n"
    f"💵 Em Reais: R$ {valor_dolares_reais:,.2f}\n\n"

    f"📥 Aportes Bolsa: R$ {total_aportes:,.2f}\n"
    f"📈 Dividendos: R$ {total_rendimentos:,.2f}\n"
    f"💵 Lucro valorização ativos: R$ {lucro_real_bolsa:,.2f}\n\n"

    f"📊 PATRIMÔNIO TOTAL: R$ {total_carteira:,.2f}"
)

# =============================
# Envio
# =============================

functions.sendMessageTelegram(mensagem)