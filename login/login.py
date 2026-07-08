from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

# Se quiser executar sem abrir a janela
# options.add_argument("--headless=new")


driver = webdriver.Chrome(
    service=Service(),
    options=options
)

wait = WebDriverWait(driver, 20)


# ============================================
# FUNÇÕES
# ============================================

def login():

    print("Abrindo página de login...")

    driver.get(URL_LOGIN)

    account = wait.until(
        EC.visibility_of_element_located((By.NAME, "account"))
    )

    password = wait.until(
        EC.visibility_of_element_located((By.NAME, "password"))
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


    print("Abrindo Pesquisa de Alunos...")

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

    print("✅ Tela de pesquisa aberta")


def abrir_relatorio_coach():

    print("Abrindo menu de opções...")

    botao_opcoes = wait.until(
        EC.element_to_be_clickable(
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


    print("Clicando em Relatório do Coach...")

    relatorio = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "a.btn-generate-report"
            )
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        relatorio
    )


    print("✅ Relatório do Coach selecionado")


# ============================================
# EXECUÇÃO
# ============================================

try:

    login()

    abrir_pesquisa_alunos()

    abrir_relatorio_coach()

    print(driver.current_url)

    input("\nPressione ENTER para fechar...")


finally:

    driver.quit()