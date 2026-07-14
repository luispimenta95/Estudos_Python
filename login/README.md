# Relatórios Tutory (alunos ativos)

Script Selenium que:

1. faz login no painel
2. abre **Alunos → Pesquisa**
3. filtra o select **status** para **ativos** (só gera relatório de estudantes ativos)
4. para **cada aluno** da lista filtrada:
   - abre **Relatório do Coach**
   - aplica filtros (questões + mês + dia 1–15)
   - baixa o PDF
5. avança a paginação, se existir

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
python login.py
```

Os arquivos vão para `PASTA_DOWNLOAD`, renomeados como `Nome_do_Aluno_YYYY-MM.pdf`.

## Observações

- Não versionar o `.env` com senha.
- Se a lista de alunos não aparecer, confira se a conta vê alunos em `/alunos/consulta`.
- Em erro por aluno, o script tira screenshot e segue para o próximo.
