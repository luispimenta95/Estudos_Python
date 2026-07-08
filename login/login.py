"""
Script de login em plataforma web via sessão HTTP.

Como usar:
1. Copie .env.example para .env e preencha URL, usuário e senha
2. Inspecione o formulário de login no navegador (F12) e ajuste
   FIELD_USER / FIELD_PASSWORD com o atributo name dos inputs
3. pip install -r requirements.txt
4. python login.py
"""

from __future__ import annotations

import os
import sys
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = os.getenv("LOGIN_URL", "").strip()
LOGIN_USER = os.getenv("LOGIN_USER", "").strip()
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "").strip()
FIELD_USER = os.getenv("FIELD_USER", "email").strip()
FIELD_PASSWORD = os.getenv("FIELD_PASSWORD", "password").strip()
CHECK_URL = os.getenv("CHECK_URL", "").strip()
SUCCESS_TEXT = os.getenv("SUCCESS_TEXT", "").strip()
FAILURE_TEXT = os.getenv("FAILURE_TEXT", "").strip()

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def validar_config() -> None:
    faltando = []
    if not LOGIN_URL:
        faltando.append("LOGIN_URL")
    if not LOGIN_USER:
        faltando.append("LOGIN_USER")
    if not LOGIN_PASSWORD:
        faltando.append("LOGIN_PASSWORD")
    if faltando:
        print("Configure no arquivo .env:", ", ".join(faltando))
        print("Use .env.example como modelo.")
        sys.exit(1)


def criar_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
    )
    return sessao


def extrair_campos_ocultos(html: str) -> dict[str, str]:
    """Pega inputs hidden (CSRF, tokens, etc.) do formulário de login."""
    soup = BeautifulSoup(html, "lxml")
    campos: dict[str, str] = {}

    form = soup.find("form")
    escopo = form if form else soup

    for inp in escopo.find_all("input"):
        nome = inp.get("name")
        tipo = (inp.get("type") or "text").lower()
        if not nome:
            continue
        if tipo == "hidden" or nome.lower() in {"csrf", "csrfmiddlewaretoken", "_token", "authenticity_token"}:
            campos[nome] = inp.get("value") or ""

    return campos


def descobrir_action(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    form = soup.find("form")
    if form and form.get("action"):
        return urljoin(base_url, form["action"])
    return base_url


def fazer_login(sessao: requests.Session) -> requests.Response:
    print(f"Acessando página de login: {LOGIN_URL}")
    pagina = sessao.get(LOGIN_URL, timeout=30)
    pagina.raise_for_status()

    payload = extrair_campos_ocultos(pagina.text)
    payload[FIELD_USER] = LOGIN_USER
    payload[FIELD_PASSWORD] = LOGIN_PASSWORD

    action = descobrir_action(pagina.text, LOGIN_URL)
    print(f"Enviando credenciais para: {action}")

    resposta = sessao.post(
        action,
        data=payload,
        timeout=30,
        allow_redirects=True,
        headers={"Referer": LOGIN_URL},
    )
    return resposta


def login_ok(resposta: requests.Response, sessao: requests.Session) -> bool:
    texto = resposta.text.lower()

    if FAILURE_TEXT and FAILURE_TEXT.lower() in texto:
        return False

    if SUCCESS_TEXT:
        alvo = CHECK_URL or resposta.url
        pagina = sessao.get(alvo, timeout=30) if CHECK_URL else resposta
        return SUCCESS_TEXT.lower() in pagina.text.lower()

    if CHECK_URL:
        check = sessao.get(CHECK_URL, timeout=30, allow_redirects=True)
        # Se redirecionou de volta para login, provavelmente falhou
        if "login" in check.url.lower() and "login" not in CHECK_URL.lower():
            return False
        return check.status_code == 200

    # Heurística simples: não ficou na página de login e status OK
    ficou_no_login = "login" in resposta.url.lower() and resposta.url.rstrip("/") == LOGIN_URL.rstrip("/")
    return resposta.status_code in (200, 302) and not ficou_no_login


def cookies_resumo(sessao: requests.Session) -> str:
    nomes = [c.name for c in sessao.cookies]
    return ", ".join(nomes) if nomes else "(nenhum)"


def main() -> Optional[requests.Session]:
    validar_config()
    sessao = criar_sessao()

    try:
        resposta = fazer_login(sessao)
    except requests.RequestException as exc:
        print(f"Erro de rede ao tentar login: {exc}")
        sys.exit(1)

    print(f"Status HTTP: {resposta.status_code}")
    print(f"URL final: {resposta.url}")
    print(f"Cookies: {cookies_resumo(sessao)}")

    if login_ok(resposta, sessao):
        print("Login realizado com sucesso.")
        print("A sessão (cookies) está pronta para novas requisições autenticadas.")
        return sessao

    print("Login falhou. Verifique:")
    print("- usuário/senha no .env")
    print("- FIELD_USER / FIELD_PASSWORD (name dos inputs no HTML)")
    print("- se o site exige JavaScript (aí use Selenium/Playwright)")
    print("- SUCCESS_TEXT / FAILURE_TEXT / CHECK_URL para validação")
    sys.exit(1)


if __name__ == "__main__":
    main()
