from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

import os
import time
import glob

PASTA_DOWNLOAD = "/home/luis-pimenta/Relatorios_Tutory"

os.makedirs(
    PASTA_DOWNLOAD,
    exist_ok=True
)

options = Options()

EMAIL = "missaonomeacao"
SENHA = "05473793150"
URL_LOGIN = "https://admin.tutory.com.br/login"


# Estabilidade
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
options.add_argument("--disable-software-rasterizer")

# Evita alguns problemas de automação
options.add_argument("--disable-blink-features=AutomationControlled")

# Mantém um perfil separado do seu Chrome principal
options.add_argument("--user-data-dir=/home/luis-pimenta/.chrome-selenium")

# Inicia maximizado
options.add_argument("--start-maximized")


driver = webdriver.Chrome(
    service=Service(),
    options=options
)

wait = WebDriverWait(driver, 20)


# ============================================
# LOGIN
# ============================================

def login():

    print("Abrindo página de login...")

    driver.get(URL_LOGIN)


    account = wait.until(
        EC.visibility_of_element_located(
            (By.NAME, "account")
        )
    )


    password = wait.until(
        EC.visibility_of_element_located(
            (By.NAME, "password")
        )
    )


    account.clear()
    account.send_keys(EMAIL)

    password.clear()
    password.send_keys(SENHA)


    botao = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input.login-submit")
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        botao
    )


    wait.until(
        lambda d: "/login" not in d.current_url
    )


    print("✅ Login realizado")



# ============================================
# PESQUISA ALUNOS
# ============================================

def abrir_pesquisa_alunos():

    print("Abrindo menu Alunos...")


    menu = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains(@class,'dropdown-toggle') and normalize-space()='Alunos']"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        menu
    )


    pesquisar = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[@href='/alunos/consulta']"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        pesquisar
    )


    wait.until(
        lambda d: "/alunos/consulta" in d.current_url
    )


    print("✅ Pesquisa de alunos aberta")



# ============================================
# RELATORIO COACH
# ============================================

def abrir_relatorio_coach():

    print("Abrindo opções...")


    botao_opcoes = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "button.dropdown-toggle-split"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        botao_opcoes
    )


    relatorio = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains(@class,'btn-generate-report') and contains(normalize-space(),'Relatório do Coach')]"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        relatorio
    )


    print("✅ Relatório do Coach aberto")



# ============================================
# FILTROS DO RELATÓRIO
# ============================================

def configurar_filtros_relatorio():

    print("Configurando filtros...")


    # Desempenho em Questões

    questoes = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "button.btn-selector[data-value='questoes']"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        questoes
    )


    print("✅ Desempenho em Questões selecionado")



    # Mês

    mes = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "button.btn-selector[data-value='mes']"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        mes
    )


    print("✅ Filtro Mês selecionado")



    # Datas automáticas

    hoje = datetime.now()

    data_inicio = hoje.strftime("%Y-%m-01")
    data_fim = hoje.strftime("%Y-%m-15")


    print("Data inicial:", data_inicio)
    print("Data final:", data_fim)



    campo_inicio = wait.until(
        EC.visibility_of_element_located(
            (
                By.ID,
                "relDataIni"
            )
        )
    )


    campo_fim = wait.until(
        EC.visibility_of_element_located(
            (
                By.ID,
                "relDataFim"
            )
        )
    )



    # Força atualização do input date

    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """,
        campo_inicio,
        data_inicio
    )


    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """,
        campo_fim,
        data_fim
    )


    print("✅ Datas preenchidas")



    # Gerar relatório

    gerar = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "a.btn-generate-my-report"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        gerar
    )


    print("✅ Relatório solicitado")


# ============================================
# ACESSAR E BAIXAR RELATÓRIO
# ============================================

def acessar_baixar_relatorio():

    print("Aguardando popup do relatório...")


    # Guarda a aba atual
    aba_principal = driver.current_window_handle


    # Clica em Acessar Relatório
    acessar = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "button.swal-button--confirm"
            )
        )
    )


    driver.execute_script(
        "arguments[0].click();",
        acessar
    )


    print("✅ Clicou em Acessar Relatório")


    # Aguarda abrir nova aba
    wait.until(
        lambda d: len(d.window_handles) > 1
    )


    abas = driver.window_handles


    for aba in abas:
        if aba != aba_principal:
            driver.switch_to.window(aba)
            break


    print("✅ Mudou para aba do relatório")

    print("URL relatório:")
    print(driver.current_url)



    # Aguarda botão Baixar
    baixar = wait.until(
        EC.element_to_be_clickable(
            (
                By.ID,
                "btn_save"
            )
        )
    )


    print("Botão Baixar encontrado")


    driver.execute_script(
        "arguments[0].click();",
        baixar
    )


    print("✅ Download iniciado")



# ============================================
# EXECUÇÃO
# ============================================

try:

    login()

    abrir_pesquisa_alunos()

    abrir_relatorio_coach()

    configurar_filtros_relatorio()

    acessar_baixar_relatorio()


    input("\nPressione ENTER para fechar...")


except Exception as e:

    print("ERRO:")
    print(e)

    driver.save_screenshot(
        "erro_tutory.png"
    )


finally:

    driver.quit()