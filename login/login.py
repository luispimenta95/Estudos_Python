"""
Login no painel Tutory (admin.tutory.com.br).

O formulário da página usa AJAX (data-ajax) e envia POST para /intent/login
com os campos account e password. Em sucesso, a API devolve JSON sem "error"
e o browser redireciona para /index.

Como usar:
1. cp .env.example .env  e preencha LOGIN_USER / LOGIN_PASSWORD
2. pip install -r requirements.txt
3. python login.py
"""

from __future__ import annotations

import os
import sys
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = os.getenv("LOGIN_URL", "https://admin.tutory.com.br/login").strip()
LOGIN_USER = os.getenv("LOGIN_USER", "").strip()
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "").strip()
FIELD_USER = os.getenv("FIELD_USER", "account").strip()
FIELD_PASSWORD = os.getenv("FIELD_PASSWORD", "password").strip()
LOGIN_ACTION = os.getenv("LOGIN_ACTION", "").strip()  # ex.: /intent/login
CHECK_URL = os.getenv("CHECK_URL", "").strip()

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


def extrair_campos_ocultos(form) -> dict[str, str]:
    campos: dict[str, str] = {}
    for inp in form.find_all("input"):
        nome = inp.get("name")
        tipo = (inp.get("type") or "text").lower()
        if not nome:
            continue
        if tipo == "hidden":
            campos[nome] = inp.get("value") or ""
    return campos


def descobrir_action(form, base_url: str) -> str:
    # Tutory: data-action="/intent/login" (AJAX). Fallback: action= ou própria URL.
    if LOGIN_ACTION:
        return urljoin(base_url, LOGIN_ACTION)
    if form.get("data-action"):
        return urljoin(base_url, form["data-action"])
    if form.get("action"):
        return urljoin(base_url, form["action"])
    return base_url


def eh_ajax(form) -> bool:
    return (form.get("data-ajax") or "").lower() == "true"


def origem(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def fazer_login(sessao: requests.Session) -> tuple[requests.Response, bool]:
    print(f"Acessando página de login: {LOGIN_URL}")
    pagina = sessao.get(LOGIN_URL, timeout=30)
    pagina.raise_for_status()

    soup = BeautifulSoup(pagina.text, "lxml")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Formulário de login não encontrado na página.")

    payload = extrair_campos_ocultos(form)
    payload[FIELD_USER] = LOGIN_USER
    payload[FIELD_PASSWORD] = LOGIN_PASSWORD

    action = descobrir_action(form, LOGIN_URL)
    ajax = eh_ajax(form)
    print(f"Enviando credenciais para: {action} ({'AJAX/JSON' if ajax else 'HTML form'})")

    headers = {
        "Referer": LOGIN_URL,
        "Origin": origem(LOGIN_URL),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    if ajax:
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        headers["X-Requested-With"] = "XMLHttpRequest"

    resposta = sessao.post(
        action,
        data=payload,
        timeout=30,
        allow_redirects=True,
        headers=headers,
    )
    return resposta, ajax


def parse_json(resposta: requests.Response) -> Optional[dict[str, Any]]:
    try:
        data = resposta.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def login_ok(resposta: requests.Response, ajax: bool, sessao: requests.Session) -> tuple[bool, str]:
    data = parse_json(resposta)

    if ajax or data is not None:
        if data is None:
            return False, f"Resposta não-JSON do endpoint AJAX: {resposta.text[:300]}"
        if data.get("error"):
            return False, str(data["error"])
        # Tutory: sucesso quando não há error (result pode ser ausente/true)
        if data.get("result") is False:
            return False, str(data.get("error") or data)
        return True, "Login OK (JSON sem erro)."

    # Fallback HTML clássico
    if "login" in resposta.url.lower() and resposta.url.rstrip("/") == LOGIN_URL.rstrip("/"):
        return False, "Permaneceu na página de login."

    return resposta.status_code in (200, 302), f"Status {resposta.status_code}, URL {resposta.url}"


def validar_area_logada(sessao: requests.Session) -> tuple[bool, str]:
    alvo = CHECK_URL or urljoin(LOGIN_URL, "/index")
    check = sessao.get(alvo, timeout=30, allow_redirects=True)
    if "login" in check.url.lower():
        return False, f"Acesso a {alvo} redirecionou para login ({check.url})."
    return check.status_code == 200, f"Área logada acessível: {check.url} (HTTP {check.status_code})"


def cookies_resumo(sessao: requests.Session) -> str:
    nomes = [c.name for c in sessao.cookies]
    return ", ".join(nomes) if nomes else "(nenhum)"


def main() -> Optional[requests.Session]:
    validar_config()
    sessao = criar_sessao()

    try:
        resposta, ajax = fazer_login(sessao)
    except requests.RequestException as exc:
        print(f"Erro de rede ao tentar login: {exc}")
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc))
        sys.exit(1)

    print(f"Status HTTP: {resposta.status_code}")
    print(f"URL final: {resposta.url}")
    print(f"Cookies: {cookies_resumo(sessao)}")

    ok, detalhe = login_ok(resposta, ajax, sessao)
    print(detalhe)

    if not ok:
        print("Login falhou.")
        print("Confira LOGIN_USER / LOGIN_PASSWORD no .env (campo da conta = account).")
        sys.exit(1)

    area_ok, area_msg = validar_area_logada(sessao)
    print(area_msg)
    if not area_ok:
        print("Login JSON ok, mas a sessão não acessou a área logada.")
        sys.exit(1)

    print("Login realizado com sucesso.")
    print("A sessão (cookies) está pronta para novas requisições autenticadas.")
    return sessao


if __name__ == "__main__":
    main()
