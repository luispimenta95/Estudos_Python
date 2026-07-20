# Relatórios Tutory (alunos ativos)

Script Selenium (**Firefox**) que:

1. faz login no painel
2. abre **Alunos → Pesquisa**
3. filtra o select **status** para **ativos** e clica em **Buscar** (só gera relatório de estudantes ativos)
4. para **cada aluno** da lista filtrada:
   - abre **Relatório do Coach**
   - aplica filtros (questões + mês + datas)
   - baixa o PDF
   - marca sucesso ou falha
5. ao fim do loop, **reprocessa os com erro** (até 3 tentativas no total por aluno)
6. avança a paginação, se existir

Usa **Firefox** (como no teste manual). No Chrome os gráficos interativos do relatório não iam no PDF.

## Setup

```bash
cd login
pip install -r requirements.txt
cp .env.example .env
```

Preencha `LOGIN_USER` e `LOGIN_PASSWORD` no `.env`.

É preciso ter **Firefox** + **geckodriver** compatível no PATH.

Se aparecer `binary is not a Firefox executable`, o `.env` está apontando para um
wrapper (ex.: `/usr/bin/firefox` do snap). Ajuste para o binário real:

```bash
# descubra o binário:
#   ls /usr/lib/firefox/firefox
#   ls /snap/firefox/current/usr/lib/firefox/firefox
FIREFOX_BINARY=/usr/lib/firefox/firefox
```

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
- Antes de **Baixar**, o script espera a animação do Chart.js (pontos **e** linhas), força `showLine`/stroke estático, congela no mesmo canvas e baixa. No log: `Gráficos estáticos no canvas`.
