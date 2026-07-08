"""
Baixa o Relatório do Coach no Tutory para TODOS os alunos da consulta.

Fluxo por aluno (igual ao que você já fazia para um):
1. Login
2. Alunos → Pesquisa (/alunos/consulta)
3. Opções do aluno → Relatório do Coach
4. Filtros (questões + mês + datas) → Gerar
5. Acessar Relatório → Baixar
6. Fecha a aba do relatório e passa para o próximo aluno

Credenciais e pastas vêm do .env (veja .env.example).
"""

from __future__ import annotations

import glob
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

URL_LOGIN = os.getenv("LOGIN_URL", "https://admin.tutory.com.br/login").strip()
EMAIL = os.getenv("LOGIN_USER", "").strip()
SENHA = os.getenv("LOGIN_PASSWORD", "").strip()

PASTA_DOWNLOAD = os.getenv(
    "PASTA_DOWNLOAD",
    str(Path.home() / "Relatorios_Tutory"),
).strip()
CHROME_USER_DATA = os.getenv(
    "CHROME_USER_DATA",
    str(Path.home() / ".chrome-selenium"),
).strip()
HEADLESS = os.getenv("HEADLESS", "0").strip() in {"1", "true", "True", "yes"}
TIMEOUT = int(os.getenv("TIMEOUT", "25"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "90"))

URL_CONSULTA = "https://admin.tutory.com.br/alunos/consulta"

os.makedirs(PASTA_DOWNLOAD, exist_ok=True)


def validar_config() -> None:
    faltando = [
        nome
        for nome, valor in [("LOGIN_USER", EMAIL), ("LOGIN_PASSWORD", SENHA)]
        if not valor
    ]
    if faltando:
        raise SystemExit(
            f"Configure no .env: {', '.join(faltando)}. Use login/.env.example como modelo."
        )


def criar_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={CHROME_USER_DATA}")
    options.add_argument("--start-maximized")
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    prefs = {
        "download.default_directory": str(Path(PASTA_DOWNLOAD).resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(), options=options)
    driver.set_page_load_timeout(60)
    return driver


def js_click(driver: webdriver.Chrome, elemento) -> None:
    driver.execute_script("arguments[0].click();", elemento)


def fechar_abas_extras(driver: webdriver.Chrome, aba_principal: str) -> None:
    for handle in list(driver.window_handles):
        if handle != aba_principal:
            driver.switch_to.window(handle)
            driver.close()
    driver.switch_to.window(aba_principal)


def login(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    print("Abrindo página de login...")
    driver.get(URL_LOGIN)

    account = wait.until(EC.visibility_of_element_located((By.NAME, "account")))
    password = wait.until(EC.visibility_of_element_located((By.NAME, "password")))

    account.clear()
    account.send_keys(EMAIL)
    password.clear()
    password.send_keys(SENHA)

    botao = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.login-submit")))
    js_click(driver, botao)
    wait.until(lambda d: "/login" not in d.current_url)
    print("Login realizado")


def abrir_pesquisa_alunos(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    print("Abrindo pesquisa de alunos...")
    driver.get(URL_CONSULTA)
    wait.until(lambda d: "/alunos/consulta" in d.current_url)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pesquisa-aluno-container")))
    print("Pesquisa de alunos aberta")


def listar_alunos_visiveis(driver: webdriver.Chrome) -> list[dict]:
    """Retorna [{index, nome}] dos cards visíveis na página atual."""
    cards = driver.find_elements(By.CSS_SELECTOR, ".pesquisa-aluno-container")
    alunos: list[dict] = []
    for i, card in enumerate(cards):
        try:
            nome_el = card.find_elements(By.CSS_SELECTOR, ".pesquisa-aluno-nome")
            nome = nome_el[0].text.strip() if nome_el else f"aluno_{i + 1}"
        except StaleElementReferenceException:
            nome = f"aluno_{i + 1}"
        alunos.append({"index": i, "nome": nome or f"aluno_{i + 1}"})
    return alunos


def ir_para_proxima_pagina(driver: webdriver.Chrome, wait: WebDriverWait) -> bool:
    """Tenta avançar paginação. Retorna True se mudou de página."""
    primeiro = driver.find_elements(By.CSS_SELECTOR, ".pesquisa-aluno-container .pesquisa-aluno-nome")
    texto_antes = primeiro[0].text if primeiro else ""

    xpaths = [
        "//li[contains(@class,'page-item') and not(contains(@class,'disabled'))]/a[@rel='next']",
        "//li[contains(@class,'page-item') and not(contains(@class,'disabled'))]"
        "/a[contains(@aria-label,'Next') or contains(@aria-label,'Próximo') or contains(@aria-label,'Proximo')]",
        "//a[contains(@class,'page-link') and (normalize-space()='›' or normalize-space()='»' or normalize-space()='>')]",
        "//a[contains(translate(normalize-space(.),'PRÓXIMOPROXIMO','proximoproximo'),'proximo')]",
    ]

    for xpath in xpaths:
        links = driver.find_elements(By.XPATH, xpath)
        for link in links:
            try:
                parent = link.find_element(By.XPATH, "..")
                if "disabled" in (parent.get_attribute("class") or ""):
                    continue
                js_click(driver, link)
                time.sleep(1.2)
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".pesquisa-aluno-container"))
                )
                depois = driver.find_elements(
                    By.CSS_SELECTOR, ".pesquisa-aluno-container .pesquisa-aluno-nome"
                )
                texto_depois = depois[0].text if depois else ""
                if texto_depois and texto_depois != texto_antes:
                    print("Próxima página de alunos carregada")
                    return True
            except Exception:
                continue
    return False


def coletar_todos_alunos(driver: webdriver.Chrome, wait: WebDriverWait) -> list[str]:
    """Percorre a lista (e paginação) e devolve os nomes na ordem."""
    abrir_pesquisa_alunos(driver, wait)
    nomes: list[str] = []
    pagina = 1

    while True:
        pagina_atual = listar_alunos_visiveis(driver)
        print(f"Coletando página {pagina}: {len(pagina_atual)} aluno(s)")
        for aluno in pagina_atual:
            if aluno["nome"] not in nomes:
                nomes.append(aluno["nome"])
        if not ir_para_proxima_pagina(driver, wait):
            break
        pagina += 1

    print(f"Total de alunos encontrados: {len(nomes)}")
    return nomes


def localizar_card_por_nome(driver: webdriver.Chrome, wait: WebDriverWait, nome: str):
    """Abre a consulta e navega páginas até achar o card do aluno."""
    abrir_pesquisa_alunos(driver, wait)

    while True:
        cards = driver.find_elements(By.CSS_SELECTOR, ".pesquisa-aluno-container")
        for card in cards:
            try:
                nome_el = card.find_elements(By.CSS_SELECTOR, ".pesquisa-aluno-nome")
                atual = nome_el[0].text.strip() if nome_el else ""
            except StaleElementReferenceException:
                continue
            if atual == nome:
                return card
        if not ir_para_proxima_pagina(driver, wait):
            break

    raise RuntimeError(f"Aluno não encontrado na lista: {nome}")


def abrir_relatorio_coach_do_card(
    driver: webdriver.Chrome, wait: WebDriverWait, card, nome: str
) -> None:
    print(f"[{nome}] Abrindo opções...")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
    time.sleep(0.3)

    botao_opcoes = None
    for seletor in (
        ".pesquisa-aluno-acoes button.dropdown-toggle-split",
        ".pesquisa-aluno-acoes .dropdown-toggle-split",
        "button.dropdown-toggle-split",
        ".dropdown-toggle-split",
    ):
        achados = card.find_elements(By.CSS_SELECTOR, seletor)
        if achados:
            botao_opcoes = achados[0]
            break
    if botao_opcoes is None:
        # fallback: qualquer botão de dropdown no card
        achados = card.find_elements(By.CSS_SELECTOR, ".pesquisa-aluno-acoes button, .dropdown button")
        if achados:
            botao_opcoes = achados[0]
    if botao_opcoes is None:
        raise RuntimeError(f"[{nome}] Botão de opções não encontrado no card.")

    js_click(driver, botao_opcoes)

    xpath_relatorio = (
        "//a[contains(@class,'btn-generate-report') and "
        "contains(normalize-space(),'Relatório do Coach')]"
    )
    relatorio = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_relatorio)))
    js_click(driver, relatorio)
    print(f"[{nome}] Relatório do Coach aberto")


def configurar_filtros_relatorio(driver: webdriver.Chrome, wait: WebDriverWait, nome: str) -> None:
    print(f"[{nome}] Configurando filtros...")

    questoes = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-selector[data-value='questoes']"))
    )
    js_click(driver, questoes)

    mes = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-selector[data-value='mes']"))
    )
    js_click(driver, mes)

    hoje = datetime.now()
    data_inicio = hoje.strftime("%Y-%m-01")
    data_fim = hoje.strftime("%Y-%m-15")
    print(f"[{nome}] Datas: {data_inicio} → {data_fim}")

    campo_inicio = wait.until(EC.visibility_of_element_located((By.ID, "relDataIni")))
    campo_fim = wait.until(EC.visibility_of_element_located((By.ID, "relDataFim")))

    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """,
        campo_inicio,
        data_inicio,
    )
    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """,
        campo_fim,
        data_fim,
    )

    gerar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-generate-my-report")))
    js_click(driver, gerar)
    print(f"[{nome}] Relatório solicitado")


def aguardar_novo_download(antes: set[str], timeout: int = DOWNLOAD_TIMEOUT) -> str | None:
    fim = time.time() + timeout
    while time.time() < fim:
        atuais = set(glob.glob(str(Path(PASTA_DOWNLOAD) / "*")))
        novos = [
            p
            for p in (atuais - antes)
            if not p.endswith(".crdownload") and not p.endswith(".tmp")
        ]
        baixando = [p for p in atuais if p.endswith(".crdownload") or p.endswith(".tmp")]
        if novos and not baixando:
            novos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return novos[0]
        time.sleep(0.5)
    return None


def renomear_download(caminho: str, nome_aluno: str) -> str:
    origem = Path(caminho)
    seguro = "".join(c if c.isalnum() or c in " ._-" else "_" for c in nome_aluno).strip()
    seguro = seguro.replace(" ", "_") or "aluno"
    mes = datetime.now().strftime("%Y-%m")
    destino = origem.with_name(f"{seguro}_{mes}{origem.suffix or '.pdf'}")
    contador = 1
    while destino.exists():
        destino = origem.with_name(f"{seguro}_{mes}_{contador}{origem.suffix or '.pdf'}")
        contador += 1
    origem.rename(destino)
    return str(destino)


def acessar_baixar_relatorio(
    driver: webdriver.Chrome, wait: WebDriverWait, aba_principal: str, nome: str
) -> str | None:
    print(f"[{nome}] Aguardando popup do relatório...")
    antes = set(glob.glob(str(Path(PASTA_DOWNLOAD) / "*")))

    acessar = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal-button--confirm"))
    )
    js_click(driver, acessar)
    print(f"[{nome}] Clicou em Acessar Relatório")

    wait.until(lambda d: len(d.window_handles) > 1)
    for aba in driver.window_handles:
        if aba != aba_principal:
            driver.switch_to.window(aba)
            break

    print(f"[{nome}] Aba do relatório: {driver.current_url}")
    baixar = wait.until(EC.element_to_be_clickable((By.ID, "btn_save")))
    js_click(driver, baixar)
    print(f"[{nome}] Download iniciado")

    arquivo = aguardar_novo_download(antes)
    if arquivo:
        final = renomear_download(arquivo, nome)
        print(f"[{nome}] Arquivo salvo: {final}")
    else:
        print(f"[{nome}] AVISO: não detectei arquivo novo em {PASTA_DOWNLOAD}")
        final = None

    fechar_abas_extras(driver, aba_principal)
    return final


def processar_aluno(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    aba_principal: str,
    nome: str,
) -> bool:
    try:
        fechar_abas_extras(driver, aba_principal)
        card = localizar_card_por_nome(driver, wait, nome)
        abrir_relatorio_coach_do_card(driver, wait, card, nome)
        configurar_filtros_relatorio(driver, wait, nome)
        acessar_baixar_relatorio(driver, wait, aba_principal, nome)
        return True
    except (TimeoutException, ElementClickInterceptedException, RuntimeError, StaleElementReferenceException) as exc:
        print(f"[{nome}] ERRO: {exc}")
        try:
            shot = Path(PASTA_DOWNLOAD) / f"erro_{nome.replace(' ', '_')[:40]}.png"
            driver.save_screenshot(str(shot))
            print(f"[{nome}] Screenshot: {shot}")
        except Exception:
            pass
        fechar_abas_extras(driver, aba_principal)
        return False


def baixar_todos(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    aba_principal = driver.current_window_handle
    nomes = coletar_todos_alunos(driver, wait)
    if not nomes:
        print("Nenhum aluno encontrado em /alunos/consulta.")
        return

    total_ok = 0
    total_erro = 0

    for i, nome in enumerate(nomes, start=1):
        print("=" * 50)
        print(f"Aluno {i}/{len(nomes)}: {nome}")
        if processar_aluno(driver, wait, aba_principal, nome):
            total_ok += 1
        else:
            total_erro += 1

    print("=" * 50)
    print(f"Concluído. Sucesso: {total_ok} | Erros: {total_erro}")
    print(f"Arquivos em: {PASTA_DOWNLOAD}")


def main() -> None:
    validar_config()
    driver = criar_driver()
    wait = WebDriverWait(driver, TIMEOUT)

    try:
        login(driver, wait)
        baixar_todos(driver, wait)
    except Exception as exc:
        print("ERRO FATAL:")
        print(exc)
        try:
            driver.save_screenshot(str(Path(PASTA_DOWNLOAD) / "erro_tutory.png"))
        except Exception:
            driver.save_screenshot("erro_tutory.png")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
