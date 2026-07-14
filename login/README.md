# Relatórios Tutory (alunos ativos)

Script Selenium que:

1. faz login no painel
2. abre **Alunos → Pesquisa**
3. filtra o select **status** para **ativos** e clica em **Buscar** (só gera relatório de estudantes ativos)
4. para **cada aluno** da lista filtrada:
   - abre **Relatório do Coach**
   - aplica filtros (questões + mês + dia 1–15)
   - baixa o PDF
   - marca sucesso ou falha
5. ao fim do loop, **reprocessa os com erro** (até 3 tentativas no total por aluno)
6. avança a paginação, se existir

## Pré-requisitos

- Python 3.10+
- Google Chrome instalado
- ChromeDriver compatível no `PATH` (ou Selenium Manager resolve automaticamente em versões recentes)

## Setup

```bash
cd login
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` e preencha pelo menos:

```env
LOGIN_USER=sua_conta
LOGIN_PASSWORD=sua_senha
PASTA_DOWNLOAD=/caminho/para/Relatorios_Tutory
```

## Como executar

Com o ambiente virtual ativo e o `.env` configurado:

```bash
cd login
source .venv/bin/activate   # se ainda não estiver ativo
python login.py
```

### Opções úteis no `.env`

| Variável | Descrição | Padrão |
|---|---|---|
| `LOGIN_URL` | URL de login | `https://admin.tutory.com.br/login` |
| `LOGIN_USER` | Usuário | (obrigatório) |
| `LOGIN_PASSWORD` | Senha | (obrigatório) |
| `PASTA_DOWNLOAD` | Pasta dos PDFs | `~/Relatorios_Tutory` |
| `CHROME_USER_DATA` | Perfil Chrome do Selenium | `~/.chrome-selenium` |
| `HEADLESS` | `1` = sem janela | `0` |
| `TIMEOUT` | Timeout de elementos (s) | `25` |
| `DOWNLOAD_TIMEOUT` | Timeout de download (s) | `90` |

### Executar sem abrir a janela do Chrome

No `.env`:

```env
HEADLESS=1
```

Depois:

```bash
python login.py
```

## Saída

- PDFs em `PASTA_DOWNLOAD`, renomeados como `Nome_do_Aluno_YYYY-MM.pdf`
- Log de resumo: `log_download_YYYYMMDD_HHMMSS.txt` (status, tentativas e falhas)
- Em erro por aluno: screenshot `erro_<nome>.png` e o script segue / reprocessa

## Observações

- Não versionar o `.env` com senha.
- Se a lista de alunos não aparecer, confira se a conta vê alunos em `/alunos/consulta`.
- Falhas são reprocessadas automaticamente ao fim do loop (até 3 tentativas por aluno).
