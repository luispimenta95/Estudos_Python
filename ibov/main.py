import yfinance as yf
from datetime import datetime
import os
from ibov.pessoal import financeiro, rendimentos
import functions
from dotenv import load_dotenv
load_dotenv()

# === Configurações iniciais ===
nome_cliente = 'Luis Felipe'
base_path = os.getenv('BASE_PATH')
data_atual = datetime.now().strftime("%d/%m/%Y")

# === Busca as cotações atuais ===
tickers = list(financeiro.carteira.keys())
dados = yf.download(tickers, period="1d", auto_adjust=False)["Close"].iloc[-1]

# === Calcula valores da carteira ===
total_investido = 0
total_atual = 0

for ticker, info in financeiro.carteira.items():
    preco_medio = info["preco"]
    qtd = info["quantidade"]
    tipo = info["tipo"]

    preco_atual = dados.get(ticker, None)
    investido = preco_medio * qtd
    valor_atual = preco_atual * qtd if preco_atual else 0
    lucro_prejuizo = valor_atual - investido if valor_atual else 0
    variacao_pct = (lucro_prejuizo / investido) * 100 if investido else 0

    total_investido += investido
    total_atual += valor_atual

total_carteira = total_atual + financeiro.renda_fixa + financeiro.gastos_emergenciais

# === Soma todos os rendimentos do histórico ===
total_rendimentos = 0.0

for ticker, info in rendimentos.rendimentos.items():
    for data_str, tipo, valor in info["itens"]:
        total_rendimentos += valor

# === Soma todos os aportes do histórico ===
total_aportes = sum(valor for _, valor in financeiro.aportes)

# === Lucro Real (Valor atual - Aportes totais) ===
lucro_real = total_atual - total_aportes

# === Monta mensagem para o Telegram ===
mensagem = (
    f"Olá {nome_cliente}, segue o detalhamento da sua carteira:\n\n"
    f"📅 {data_atual}\n"
    f"💰 Total aplicado na bolsa de valores: R$ {total_atual:,.2f}\n"
    f"💰 Total para gastos emergenciais: R$ {financeiro.gastos_emergenciais:,.2f}\n"
    f"💰 Total guardado para longo prazo: R$ {financeiro.renda_fixa:,.2f}\n"
    f"📊 Total carteira: R$ {total_carteira:,.2f}\n\n"
    f"📥 Total de aportes: R$ {total_aportes:,.2f}\n"
    f"📈 Rendimentos recebidos: R$ {total_rendimentos:,.2f}\n"
    f"💵 Lucro real: R$ {lucro_real:,.2f}"
)

# === Envia mensagem ===
functions.sendMessageTelegram(mensagem)
