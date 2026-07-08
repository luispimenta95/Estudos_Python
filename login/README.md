# Login Tutory (admin)

Script Python para autenticar no painel `https://admin.tutory.com.br/login`.

O site não faz POST clássico no `/login`: o formulário usa AJAX (`data-ajax`) e envia:

- URL: `POST /intent/login`
- Campos: `account`, `password`
- Resposta: JSON (`error` em falha; sem `error` em sucesso → redireciona para `/index`)

## Setup

```bash
cd login
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` com `LOGIN_USER` e `LOGIN_PASSWORD`.

## Executar

```bash
python login.py
```

Em sucesso, a sessão `requests` fica com o cookie `PHPSESSID` autenticado.

## Observação

Não versionar o arquivo `.env` com senha real.
