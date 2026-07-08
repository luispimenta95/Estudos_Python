# Login em plataforma web

Script Python que abre a página de login, envia usuário/senha e mantém a sessão (cookies) para continuar autenticado.

## Setup

```bash
cd login
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` com a URL e as credenciais da plataforma.

## Como descobrir os campos do formulário

1. Abra a página de login no navegador
2. Pressione F12 → aba Elements / Inspetor
3. Localize os inputs, por exemplo:

```html
<input type="email" name="email">
<input type="password" name="password">
```

4. Coloque esses `name` em `FIELD_USER` e `FIELD_PASSWORD`

## Executar

```bash
python login.py
```

## Observações

- Funciona bem em logins por formulário HTML (POST + cookies/CSRF).
- Se o site for 100% JavaScript (SPA) ou tiver CAPTCHA, este script com `requests` não basta — aí é preciso Selenium ou Playwright.
- Nunca versionar o arquivo `.env` com senha real.
