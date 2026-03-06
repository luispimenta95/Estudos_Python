import yfinance as yf
from datetime import datetime
import os
import time
import sys
import calendar
from pessoal import financeiro, rendimentos
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

    # No meu caso , a ideia é executar dia 15 e ultimo dia do mês
    dia_execucao = 15
    data_15 = datetime(hoje.year, hoje.month, dia_execucao)

    if data_15.weekday() == 5: ## Pagamento caiu num sábado
        dia_execucao = 14
    elif data_15.weekday() == 6: ## Pagamento caiu num domingo
        dia_execucao = 13

    # --- ultimo dia do mês ---
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    data_final = datetime(hoje.year, hoje.month, ultimo_dia)

    dia_execucao_final = ultimo_dia

    if data_final.weekday() == 5:
        dia_execucao_final = ultimo_dia - 1
    elif data_final.weekday() == 6:
        dia_execucao_final = ultimo_dia - 2

    if dia == dia_execucao or dia == dia_execucao_final:
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

# =============================
# BINANCE
# =============================

api_key = os.getenv('BINANCE_KEY')
api_secret = os.getenv('BINANCE_SECRET')

client_binance = Client(api_key, api_secret)

server_time = client_binance.get_server_time()
client_binance.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)

# =============================
# BUSCA COTAÇÕES
# =============================

tickers = list(financeiro.carteira.keys())

dados_download = yf.download(
    tickers,
    period="1d",
    auto_adjust=True,
    progress=False
)["Close"]

# =============================
# DÓLAR
# =============================

dolar_raw = yf.download(
    "USDBRL=X",
    period="1d",
    auto_adjust=True,
    progress=False
)["Close"]

try:
    cotacao_dolar = float(
        dolar_raw.iloc[-1].item()
        if hasattr(dolar_raw.iloc[-1], 'item')
        else dolar_raw.iloc[-1]
    )
except:
    cotacao_dolar = 5.0

# =============================
# BINANCE ASSETS
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
# CÁLCULO BOLSA
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
# PATRIMÔNIO
# =============================

valor_cdb = financeiro.cdb

total_carteira = total_atual_bolsa + valor_cdb + valor_dolares_reais

# =============================
# SUGESTÃO DE APORTES
# =============================

aporte2 = total_carteira * 0.02
aporte4 = total_carteira * 0.04
aporte8 = total_carteira * 0.08
aporte10 = total_carteira * 0.10

# =============================
# PERCENTUAIS
# =============================

percentual_bolsa = (total_atual_bolsa / total_carteira * 100) if total_carteira > 0 else 0
percentual_cdb = (valor_cdb / total_carteira * 100) if total_carteira > 0 else 0
percentual_crypto = (valor_dolares_reais / total_carteira * 100) if total_carteira > 0 else 0

# =============================
# TEXTO BINANCE
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
# RENDIMENTOS
# =============================

total_rendimentos = sum(
    valor
    for info in rendimentos.rendimentos.values()
    for _, _, valor in info["itens"]
)

total_aportes = sum(valor for _, valor in financeiro.aportes)

lucro_real_bolsa = total_atual_bolsa - total_aportes

# =============================
# MENSAGEM
# =============================

mensagem = (
    f"Olá {nome_cliente}, segue seu patrimônio atualizado:\n\n"
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

    f"📊 PATRIMÔNIO TOTAL: R$ {total_carteira:,.2f}\n\n"

    f"💡 Sugestão de aportes:\n"
    f"• 2% da carteira: R$ {aporte2:,.2f}\n"
    f"• 4% da carteira: R$ {aporte4:,.2f}\n"
    f"• 8% da carteira: R$ {aporte8:,.2f}\n"
    f"• 10% da carteira: R$ {aporte10:,.2f}\n\n"
)

# =============================
# ENVIO
# =============================

functions.sendMessageTelegram(mensagem)