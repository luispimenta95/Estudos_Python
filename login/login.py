"""
Baixa o Relatório do Coach no Tutory para os alunos ATIVOS da consulta.

Fluxo por aluno (igual ao que você já fazia para um):
1. Login
2. Alunos → Pesquisa (/alunos/consulta)
3. Filtro status = ativos + Buscar (reduz a lista antes de gerar relatórios)
4. Opções do aluno → Relatório do Coach
5. Filtros (questões + mês + datas) → Gerar
6. Acessar Relatório → Baixar
7. Fecha a aba do relatório e passa para o próximo aluno
8. Ao fim, reprocessa falhas (até 3 tentativas por aluno)

Credenciais e pastas vêm do .env (veja .env.example).
"""

from __future__ import annotations

import glob
import argparse
import os
import shutil
import time
from datetime import datetime
from calendar import monthrange
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--periodo",
    choices=["1", "2"],
    required=True,
    help=(
        "Escolha o período desejado:\n"
        "1 = Dia inicial: 01\n"
        "    \nDia Final: 15\n"
        "\n2 = Dia inicial: 16\n"
        "    Dia Final: Último dia do mês (30 ou 31, e 28/29 em fevereiro)"
    ),
)
parser.add_argument(
    "--teste",
    action="store_true",
    help=(
        "Modo teste: baixa o relatório só da aluna Marianny Carvalho "
        "(útil para validar PDF com gráficos)."
    ),
)
args = parser.parse_args()


URL_LOGIN = os.getenv("LOGIN_URL", "https://admin.tutory.com.br/login").strip()
EMAIL = os.getenv("LOGIN_USER", "").strip()
SENHA = os.getenv("LOGIN_PASSWORD", "").strip()

# Aluna usada no modo --teste (match parcial no nome da lista)
ALUNA_TESTE = "Marianny Carvalho"

PASTA_DOWNLOAD = os.getenv(
    "PASTA_DOWNLOAD",
    str(Path.home() / "Relatorios_Tutory"),
).strip()
# Perfil Firefox opcional (mesmo browser do teste manual)
FIREFOX_PROFILE = os.getenv("FIREFOX_PROFILE", "").strip()
FIREFOX_BINARY = os.getenv("FIREFOX_BINARY", "").strip()
HEADLESS = os.getenv("HEADLESS", "0").strip() in {"1", "true", "True", "yes"}
TIMEOUT = int(os.getenv("TIMEOUT", "25"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "90"))
# Tempo para Chart.js pintar o gráfico interativo antes de congelar
CHART_WAIT = int(os.getenv("CHART_WAIT", "30"))

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


def _parece_binario_firefox(caminho: Path) -> bool:
    """Geckodriver rejeita wrappers (snap/script). Precisa do executável real."""
    try:
        if not caminho.is_file() or not os.access(caminho, os.X_OK):
            return False
        # scripts shell / snap launchers começam com shebang
        with caminho.open("rb") as f:
            inicio = f.read(128)
        if inicio.startswith(b"#!"):
            return False
        nome = caminho.name.lower()
        return "firefox" in nome or nome in {"firefox", "firefox-bin", "firefox-esr"}
    except OSError:
        return False


def resolver_binario_firefox() -> str | None:
    """
    Resolve um Firefox que o geckodriver aceite.
    /usr/bin/firefox no Ubuntu costuma ser wrapper snap → InvalidArgumentException.
    """
    candidatos: list[Path] = []

    if FIREFOX_BINARY:
        candidatos.append(Path(FIREFOX_BINARY).expanduser())

    # binários reais comuns (antes dos wrappers do PATH)
    candidatos.extend(
        Path(p)
        for p in (
            "/usr/lib/firefox/firefox",
            "/usr/lib/firefox-esr/firefox-esr",
            "/snap/firefox/current/usr/lib/firefox/firefox",
            "/opt/firefox/firefox",
            str(Path.home() / "firefox" / "firefox"),
            "/Applications/Firefox.app/Contents/MacOS/firefox",
        )
    )

    which = shutil.which("firefox") or shutil.which("firefox-esr")
    if which:
        candidatos.append(Path(which).resolve())

    vistos: set[str] = set()
    for cand in candidatos:
        try:
            chave = str(cand.resolve()) if cand.exists() else str(cand)
        except OSError:
            chave = str(cand)
        if chave in vistos:
            continue
        vistos.add(chave)
        if _parece_binario_firefox(cand):
            return str(cand.resolve())

    if FIREFOX_BINARY:
        print(
            f"AVISO: FIREFOX_BINARY='{FIREFOX_BINARY}' não é um executável "
            "Firefox válido (wrappers como /usr/bin/firefox do snap não servem). "
            "Tentando deixar o geckodriver achar o padrão..."
        )
    return None


def criar_driver() -> webdriver.Firefox:
    """
    Usa Firefox — mesmo browser do teste manual no Tutory.
    (No Chrome os gráficos interativos Chart.js não iam no PDF.)
    """
    pasta = str(Path(PASTA_DOWNLOAD).resolve())
    options = Options()

    binario = resolver_binario_firefox()
    if binario:
        options.binary_location = binario
        print(f"Firefox binary: {binario}")
    else:
        print(
            "Firefox binary: (padrão do geckodriver). "
            "Se falhar, defina FIREFOX_BINARY no .env para o executável real, "
            "ex.: /usr/lib/firefox/firefox ou "
            "/snap/firefox/current/usr/lib/firefox/firefox"
        )

    if FIREFOX_PROFILE:
        perfil = str(Path(FIREFOX_PROFILE).expanduser())
        options.add_argument("-profile")
        options.add_argument(perfil)
        print(f"Firefox profile: {perfil}")
    if HEADLESS:
        options.add_argument("-headless")

    # Download automático de PDF (Firefox; aba do relatório costuma ser about:blank)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", pasta)
    options.set_preference("browser.download.useDownloadDir", True)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.alwaysOpenPanel", False)
    options.set_preference("browser.download.always_ask_before_handling_new_types", False)
    options.set_preference("browser.download.improvements_to_download_panel", False)
    options.set_preference("browser.download.viewableInternally.enabledTypes", "")
    options.set_preference("pdfjs.disabled", True)
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        "application/pdf,application/x-pdf,application/octet-stream,binary/octet-stream",
    )
    options.set_preference("browser.helperApps.alwaysAsk.force", False)
    options.set_preference("browser.download.forbid_open_with", True)

    try:
        driver = webdriver.Firefox(service=Service(), options=options)
    except Exception as exc:
        msg = str(exc)
        if "not a Firefox executable" in msg or "binary is not" in msg.lower():
            raise SystemExit(
                "Não achei um Firefox executável válido para o geckodriver.\n"
                "No .env, aponte FIREFOX_BINARY para o binário real (não o wrapper):\n"
                "  FIREFOX_BINARY=/usr/lib/firefox/firefox\n"
                "  # ou snap:\n"
                "  FIREFOX_BINARY=/snap/firefox/current/usr/lib/firefox/firefox\n"
                "E comente/remova um FIREFOX_BINARY inválido (ex.: /usr/bin/firefox).\n"
                f"Erro original: {exc}"
            ) from exc
        raise

    driver.set_page_load_timeout(60)
    try:
        driver.maximize_window()
    except Exception:
        driver.set_window_size(1920, 1080)
    print(f"Firefox iniciado (download em: {pasta})")
    return driver


def js_click(driver: WebDriver, elemento) -> None:
    driver.execute_script("arguments[0].click();", elemento)


def fechar_abas_extras(driver: WebDriver, aba_principal: str) -> None:
    for handle in list(driver.window_handles):
        if handle != aba_principal:
            driver.switch_to.window(handle)
            driver.close()
    driver.switch_to.window(aba_principal)


def limpar_overlays(driver: WebDriver) -> None:
    """Fecha dropdowns/modais/sweetalert que sobraram do aluno anterior."""
    driver.execute_script(
        """
        document.querySelectorAll('.dropdown-menu.show').forEach(el => el.classList.remove('show'));
        document.querySelectorAll('.dropdown.show, .btn-group.show').forEach(el => el.classList.remove('show'));
        document.querySelectorAll('.modal.show').forEach(el => {
            el.classList.remove('show');
            el.style.display = 'none';
        });
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('padding-right');
        document.querySelectorAll('.swal-overlay, .swal-modal').forEach(el => el.remove());
        """
    )
    try:
        from selenium.webdriver.common.keys import Keys

        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass
    time.sleep(0.2)


def elemento_visivel(el) -> bool:
    try:
        return el.is_displayed() and el.size.get("height", 0) > 0 and el.size.get("width", 0) > 0
    except StaleElementReferenceException:
        return False


def esperar_link_relatorio_visivel(driver: WebDriver, card, timeout: int = TIMEOUT):
    """
    Não use XPath global: após o 1º aluno existem vários
    'Relatório do Coach' no DOM (ocultos). Pegamos só o visível
    do menu aberto / do card atual.
    """
    fim = time.time() + timeout
    ultimo_erro = "link não apareceu"

    while time.time() < fim:
        candidatos = []

        # 1) menu Bootstrap aberto em qualquer lugar
        candidatos.extend(
            driver.find_elements(
                By.CSS_SELECTOR,
                ".dropdown-menu.show a.btn-generate-report, "
                ".dropdown-menu.show a[class*='btn-generate-report']",
            )
        )
        # 2) dentro do card do aluno
        candidatos.extend(
            card.find_elements(
                By.CSS_SELECTOR,
                ".dropdown-menu a.btn-generate-report, a.btn-generate-report, "
                ".pesquisa-aluno-acoes a",
            )
        )
        # 3) fallback por texto, mas só visíveis
        candidatos.extend(
            driver.find_elements(
                By.XPATH,
                "//a[contains(normalize-space(.),'Relatório do Coach') or "
                "contains(normalize-space(.),'Relatorio do Coach')]",
            )
        )

        vistos = set()
        for el in candidatos:
            try:
                id_el = el.id
                if id_el in vistos:
                    continue
                vistos.add(id_el)
                texto = (el.text or el.get_attribute("textContent") or "").strip().lower()
                if "relat" not in texto and "coach" not in texto:
                    # ainda pode ser o botão certo só com classe
                    classes = el.get_attribute("class") or ""
                    if "btn-generate-report" not in classes:
                        continue
                if not elemento_visivel(el):
                    continue
                return el
            except StaleElementReferenceException:
                ultimo_erro = "elemento stale"
                continue

        time.sleep(0.25)

    raise TimeoutException(
        f"Relatório do Coach visível não encontrado em {timeout}s ({ultimo_erro})"
    )


def login(driver: WebDriver, wait: WebDriverWait) -> None:
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


def filtrar_alunos_ativos(driver: WebDriver, wait: WebDriverWait) -> None:
    """Seleciona status=ativos e clica em Buscar antes de listar/abrir ações."""
    print("Filtrando alunos com status 'ativos'...")
    select_el = wait.until(EC.presence_of_element_located((By.NAME, "status")))
    Select(select_el).select_by_value("ativos")
    # Garante que o change dispare mesmo se o Select nativo for interceptado por UI
    driver.execute_script(
        """
        arguments[0].value = 'ativos';
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
        """,
        select_el,
    )

    buscar = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[type='submit'][value='Buscar'], button[type='submit'][value='Buscar']")
        )
    )
    try:
        buscar.click()
    except Exception:
        js_click(driver, buscar)
    print("Clicou em Buscar")

    time.sleep(0.8)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pesquisa-aluno-container")))
    print("Filtro de alunos ativos aplicado")


def abrir_pesquisa_alunos(driver: WebDriver, wait: WebDriverWait) -> None:
    print("Abrindo pesquisa de alunos...")
    driver.get(URL_CONSULTA)
    wait.until(lambda d: "/alunos/consulta" in d.current_url)
    wait.until(EC.presence_of_element_located((By.NAME, "status")))
    filtrar_alunos_ativos(driver, wait)
    print("Pesquisa de alunos aberta")


def listar_alunos_visiveis(driver: WebDriver) -> list[dict]:
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


def ir_para_proxima_pagina(driver: WebDriver, wait: WebDriverWait) -> bool:
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


def coletar_todos_alunos(driver: WebDriver, wait: WebDriverWait) -> list[str]:
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


def encontrar_aluno_por_trecho(
    driver: WebDriver, wait: WebDriverWait, trecho: str
) -> str | None:
    """Varre a lista filtrada e devolve o nome completo que contém o trecho."""
    alvo = trecho.casefold().strip()
    abrir_pesquisa_alunos(driver, wait)
    pagina = 1

    while True:
        pagina_atual = listar_alunos_visiveis(driver)
        print(f"Buscando '{trecho}' na página {pagina}: {len(pagina_atual)} aluno(s)")
        for aluno in pagina_atual:
            if alvo in aluno["nome"].casefold():
                return aluno["nome"]
        if not ir_para_proxima_pagina(driver, wait):
            break
        pagina += 1
    return None


def localizar_card_por_nome(driver: WebDriver, wait: WebDriverWait, nome: str):
    """Abre a consulta e navega páginas até achar o card do aluno."""
    limpar_overlays(driver)
    abrir_pesquisa_alunos(driver, wait)
    limpar_overlays(driver)

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
    driver: WebDriver, wait: WebDriverWait, card, nome: str
) -> None:
    print(f"[{nome}] Abrindo opções...")
    limpar_overlays(driver)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
    time.sleep(0.4)

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
        achados = card.find_elements(
            By.CSS_SELECTOR, ".pesquisa-aluno-acoes button, .dropdown button"
        )
        if achados:
            botao_opcoes = achados[0]
    if botao_opcoes is None:
        raise RuntimeError(f"[{nome}] Botão de opções não encontrado no card.")

    # Clique "humano" no toggle; js_click às vezes não abre o menu Bootstrap
    try:
        wait.until(EC.element_to_be_clickable(botao_opcoes))
        botao_opcoes.click()
    except Exception:
        js_click(driver, botao_opcoes)

    # Garante que algum menu ficou .show; se não, tenta de novo
    time.sleep(0.35)
    menus_abertos = driver.find_elements(By.CSS_SELECTOR, ".dropdown-menu.show")
    if not menus_abertos:
        print(f"[{nome}] Menu não abriu no 1º clique; tentando de novo...")
        limpar_overlays(driver)
        time.sleep(0.2)
        try:
            botao_opcoes.click()
        except Exception:
            js_click(driver, botao_opcoes)
        time.sleep(0.35)

    relatorio = esperar_link_relatorio_visivel(driver, card)
    try:
        relatorio.click()
    except Exception:
        js_click(driver, relatorio)
    print(f"[{nome}] Relatório do Coach aberto")

    # Aguarda UI do relatório (filtros) aparecer
    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button.btn-selector[data-value='questoes'], #relDataIni")
        )
    )


def configurar_filtros_relatorio(driver: WebDriver, wait: WebDriverWait, nome: str) -> None:
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
    if args.periodo == "1":
        data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        data_fim = hoje.replace(day=15).strftime("%Y-%m-%d")
    else:
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        data_inicio = hoje.replace(day=16).strftime("%Y-%m-%d")
        data_fim = hoje.replace(day=ultimo_dia).strftime("%Y-%m-%d")
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


def _listar_arquivos_download(pastas: list[Path]) -> set[str]:
    arquivos: set[str] = set()
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        arquivos.update(str(p) for p in pasta.glob("*") if p.is_file())
    return arquivos


def aguardar_novo_download(
    antes: set[str],
    timeout: int = DOWNLOAD_TIMEOUT,
    pastas: list[str] | None = None,
) -> str | None:
    """Espera PDF novo. Firefox usa .part; também olha ~/Downloads como fallback."""
    dirs = [Path(p).expanduser() for p in (pastas or [PASTA_DOWNLOAD])]
    downloads_padrao = Path.home() / "Downloads"
    if downloads_padrao.resolve() not in {d.resolve() for d in dirs}:
        dirs.append(downloads_padrao)

    fim = time.time() + timeout
    while time.time() < fim:
        atuais = _listar_arquivos_download(dirs)
        baixando = [
            p
            for p in atuais
            if p.endswith(".part")
            or p.endswith(".crdownload")
            or p.endswith(".tmp")
            or p.endswith(".download")
        ]
        novos = [
            p
            for p in (atuais - antes)
            if p not in baixando
            and not Path(p).name.startswith(".")
            and (
                p.lower().endswith(".pdf")
                or Path(p).suffix == ""
                or "relat" in Path(p).name.lower()
            )
        ]
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


def preparar_graficos_para_pdf(driver: WebDriver, nome: str) -> int:
    """
    O gerador de PDF do Tutory ignora o canvas Chart.js em movimento.
    Mantém o canvas e o Chart intactos (o botão Baixar depende deles), mas põe
    uma imagem PNG sobreposta exatamente no mesmo local: o PDF captura a imagem.
    """
    print(f"[{nome}] Criando sobreposição estática dos gráficos para o PDF...")

    WebDriverWait(driver, CHART_WAIT).until(
        lambda d: d.execute_script(
            "return !!(document.body && document.body.innerText"
            " && document.body.innerText.length > 50)"
        )
    )
    time.sleep(5)  # espera o traço de entrada dos gráficos animados

    convertidos = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          let n = 0;
          const existing = document.querySelectorAll('.tutory-chart-pdf-overlay');
          existing.forEach(el => el.remove());

          async function imageReady(url) {
            const img = new Image();
            img.src = url;
            await new Promise((resolve, reject) => {
              img.onload = resolve;
              img.onerror = reject;
            });
            return img;
          }

          const canvases = Array.from(document.querySelectorAll('canvas'));
          for (const canvas of canvases) {
            try {
              const rect = canvas.getBoundingClientRect();
              if (rect.width < 80 || rect.height < 60) continue;
              const url = canvas.toDataURL('image/png', 1.0);
              const check = await imageReady(url);
              if (!check.naturalWidth) continue;

              const overlay = document.createElement('img');
              overlay.className = 'tutory-chart-pdf-overlay';
              overlay.src = url;
              overlay.alt = '';
              overlay.setAttribute('aria-hidden', 'true');
              overlay.style.cssText = [
                'position:fixed',
                'left:' + rect.left + 'px',
                'top:' + rect.top + 'px',
                'width:' + rect.width + 'px',
                'height:' + rect.height + 'px',
                'z-index:2147483647',
                'pointer-events:none',
                'display:block'
              ].join(';');
              document.body.appendChild(overlay);
              n++;
            } catch (e) {}
          }
          done(n);
        })().catch(() => done(0));
        """
    )

    time.sleep(0.8)
    print(f"[{nome}] Sobreposições PNG dos gráficos: {convertidos}")
    return int(convertidos or 0)


def acessar_baixar_relatorio(
    driver: WebDriver, wait: WebDriverWait, aba_principal: str, nome: str
) -> str | None:
    print(f"[{nome}] Aguardando popup do relatório...")
    pastas_monitor = [PASTA_DOWNLOAD, str(Path.home() / "Downloads")]
    antes = _listar_arquivos_download([Path(p) for p in pastas_monitor])

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
    preparar_graficos_para_pdf(driver, nome)

    # clique nativo — js_click às vezes não dispara o download no Firefox
    try:
        baixar.click()
    except Exception:
        js_click(driver, baixar)
    print(f"[{nome}] Download iniciado")

    arquivo = aguardar_novo_download(antes, pastas=pastas_monitor)
    if arquivo:
        # se caiu em ~/Downloads, move para PASTA_DOWNLOAD antes de renomear
        destino_dir = Path(PASTA_DOWNLOAD).resolve()
        origem = Path(arquivo)
        if origem.parent.resolve() != destino_dir:
            destino_dir.mkdir(parents=True, exist_ok=True)
            movido = destino_dir / origem.name
            contador = 1
            while movido.exists():
                movido = destino_dir / f"{origem.stem}_{contador}{origem.suffix}"
                contador += 1
            origem.rename(movido)
            arquivo = str(movido)
            print(f"[{nome}] Movido de Downloads → {arquivo}")
        final = renomear_download(arquivo, nome)
        print(f"[{nome}] Arquivo salvo: {final}")
    else:
        print(f"[{nome}] AVISO: não detectei arquivo novo em {PASTA_DOWNLOAD}")
        try:
            amostra = sorted(Path(PASTA_DOWNLOAD).glob("*"))[-5:]
            print(f"[{nome}] Últimos arquivos na pasta: {[p.name for p in amostra]}")
        except Exception:
            pass
        final = None

    fechar_abas_extras(driver, aba_principal)
    return final


def processar_aluno(
    driver: WebDriver,
    wait: WebDriverWait,
    aba_principal: str,
    nome: str,
) -> str | None:
    """Retorna o caminho do PDF baixado, ou None em falha."""
    try:
        fechar_abas_extras(driver, aba_principal)
        limpar_overlays(driver)
        card = localizar_card_por_nome(driver, wait, nome)
        abrir_relatorio_coach_do_card(driver, wait, card, nome)
        configurar_filtros_relatorio(driver, wait, nome)
        arquivo = acessar_baixar_relatorio(driver, wait, aba_principal, nome)
        limpar_overlays(driver)
        return arquivo
    except (
        TimeoutException,
        ElementClickInterceptedException,
        RuntimeError,
        StaleElementReferenceException,
    ) as exc:
        print(f"[{nome}] ERRO: {exc}")
        try:
            shot = Path(PASTA_DOWNLOAD) / f"erro_{nome.replace(' ', '_')[:40]}.png"
            driver.save_screenshot(str(shot))
            print(f"[{nome}] Screenshot: {shot}")
        except Exception:
            pass
        try:
            limpar_overlays(driver)
            fechar_abas_extras(driver, aba_principal)
        except Exception:
            pass
        return None


def formatar_duracao(segundos: float) -> str:
    total = int(round(segundos))
    horas, resto = divmod(total, 3600)
    minutos, segs = divmod(resto, 60)
    if horas:
        return f"{horas}h {minutos}min {segs}s"
    if minutos:
        return f"{minutos}min {segs}s"
    return f"{segs}s"


def gravar_log_resumo(
    inicio: datetime,
    fim: datetime,
    total_alunos: int,
    pdfs: list[str],
    falhas: list[str],
    resultados: list[dict] | None = None,
) -> Path:
    caminho = Path(PASTA_DOWNLOAD) / f"log_download_{inicio.strftime('%Y%m%d_%H%M%S')}.txt"
    linhas = [
        "Relatórios Tutory - resumo da execução",
        f"Início: {inicio.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Fim:    {fim.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Duração: {formatar_duracao((fim - inicio).total_seconds())}",
        f"Alunos processados: {total_alunos}",
        f"PDFs baixados: {len(pdfs)}",
        f"Falhas finais: {len(falhas)}",
        f"Pasta: {PASTA_DOWNLOAD}",
        "",
        "Arquivos:",
    ]
    if pdfs:
        linhas.extend(f"- {Path(p).name}" for p in pdfs)
    else:
        linhas.append("- (nenhum)")

    linhas.extend(["", "Status por aluno:"])
    if resultados:
        for r in resultados:
            status = "OK" if r["sucesso"] else "FALHA"
            linhas.append(
                f"- [{status}] {r['nome']} (tentativas: {r['tentativas']})"
            )
    else:
        linhas.append("- (nenhum)")

    if falhas:
        linhas.extend(["", "Alunos com falha após todas as tentativas:"])
        linhas.extend(f"- {nome}" for nome in falhas)

    texto = "\n".join(linhas) + "\n"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def baixar_todos(driver: WebDriver, wait: WebDriverWait) -> None:
    inicio = datetime.now()
    max_tentativas = 3
    print(f"Processo iniciado em: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")

    aba_principal = driver.current_window_handle

    if args.teste:
        nome_teste = encontrar_aluno_por_trecho(driver, wait, ALUNA_TESTE)
        nomes = [nome_teste] if nome_teste else []
        if nomes:
            print(
                f"Modo --teste: processando apenas {nomes[0]} "
                f"para validar o PDF com gráficos"
            )
        else:
            print(f"Modo --teste: aluna '{ALUNA_TESTE}' não encontrada na lista.")
    else:
        nomes = coletar_todos_alunos(driver, wait)

    if not nomes:
        fim = datetime.now()
        print("Nenhum aluno encontrado em /alunos/consulta.")
        log = gravar_log_resumo(inicio, fim, 0, [], [], [])
        print(f"Log salvo em: {log}")
        return

    # Flag de sucesso/falha por aluno
    resultados: dict[str, dict] = {
        nome: {"nome": nome, "sucesso": False, "arquivo": None, "tentativas": 0}
        for nome in nomes
    }

    def processar_lote(lista: list[str], rodada: int) -> None:
        total = len(lista)
        for i, nome in enumerate(lista, start=1):
            resultados[nome]["tentativas"] += 1
            tentativa = resultados[nome]["tentativas"]
            print("=" * 50)
            print(
                f"[rodada {rodada}] Aluno {i}/{total}: {nome} "
                f"(tentativa {tentativa}/{max_tentativas})"
            )
            arquivo = processar_aluno(driver, wait, aba_principal, nome)
            if arquivo:
                resultados[nome]["sucesso"] = True
                resultados[nome]["arquivo"] = arquivo
                print(f"[{nome}] SUCESSO")
            else:
                resultados[nome]["sucesso"] = False
                resultados[nome]["arquivo"] = None
                print(f"[{nome}] FALHA")

    # 1ª passagem: todos os alunos
    processar_lote(nomes, rodada=1)

    # Reprocessa só os com erro, até completar 3 tentativas
    for rodada in range(2, max_tentativas + 1):
        pendentes = [n for n in nomes if not resultados[n]["sucesso"]]
        if not pendentes:
            print("=" * 50)
            print("Nenhuma falha restante — sem reprocessamento.")
            break
        print("=" * 50)
        print(
            f"Reprocessando {len(pendentes)} aluno(s) com erro "
            f"(rodada {rodada}/{max_tentativas})..."
        )
        processar_lote(pendentes, rodada=rodada)

    pdfs = [r["arquivo"] for r in resultados.values() if r["sucesso"] and r["arquivo"]]
    falhas = [r["nome"] for r in resultados.values() if not r["sucesso"]]
    lista_resultados = [resultados[n] for n in nomes]

    fim = datetime.now()
    log = gravar_log_resumo(inicio, fim, len(nomes), pdfs, falhas, lista_resultados)

    print("=" * 50)
    print(f"Início: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Fim:    {fim.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Duração: {formatar_duracao((fim - inicio).total_seconds())}")
    print(f"PDFs baixados: {len(pdfs)}")
    print(f"Falhas finais: {len(falhas)}")
    if falhas:
        print("Alunos com falha:")
        for nome in falhas:
            print(f"- {nome} (tentativas: {resultados[nome]['tentativas']})")
    print(f"Arquivos em: {PASTA_DOWNLOAD}")
    print(f"Log salvo em: {log}")


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
