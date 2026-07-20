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

## Setup

```bash
cd login
pip install -r requirements.txt
cp .env.example .env
```

Preencha `LOGIN_USER` e `LOGIN_PASSWORD` no `.env`.

É preciso ter **Google Chrome** + **ChromeDriver** compatível no PATH.

## Executar

```bash
python login.py --periodo 1
# ou segunda quinzena:
python login.py --periodo 2

# teste: só Marianny Carvalho (validar PDF com gráficos)
python login.py --periodo 1 --teste
```

Os arquivos vão para `PASTA_DOWNLOAD`, renomeados como `Nome_do_Aluno_YYYY-MM.pdf`.

## Observações

- Não versionar o `.env` com senha.
- Se a lista de alunos não aparecer, confira se a conta vê alunos em `/alunos/consulta`.
- Em erro por aluno, o script tira screenshot e segue para o próximo.
- Há um `sleep(2)` antes de clicar em **Gerar**.
- Na aba do relatório, o script espera o **Chart.js** (`window.Chart`) e o gráfico **Acertos e Erros por Dia** pintado antes de **Baixar**. O aviso MIME `binary/octet-stream` do `chart.js` no DevTools é só warning — o Chrome carrega mesmo assim. Ajuste `REPORT_RENDER_TIMEOUT` se precisar.
