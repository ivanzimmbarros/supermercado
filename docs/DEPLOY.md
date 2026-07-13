# Deploy isolado (Streamlit Community Cloud)

Este app **não** partilha secrets, base de dados nem configuração com outros projetos.

## Checklist anti-impacto

- [ ] Criar app Streamlit **novo** (não reutilizar apps existentes)
- [ ] Ligar apenas o repositório `ivanzimmbarros/supermercado`
- [ ] Branch de deploy: `main` (após merge) ou este feature branch para teste
- [ ] Main file: `app/Home.py`
- [ ] Python packages: `requirements.txt`
- [ ] System packages: `packages.txt` (`libzbar0` para scanner)
- [ ] Secrets **só** deste app (ver `.streamlit/secrets.toml.example`)
- [ ] `DATABASE_URL` apontando a Postgres dedicado (Supabase/Neon **novo**)
- [ ] `allowed_emails` dos 2 Gmail
- [ ] Em Configurações: `allow_dev_bypass = false` e `require_google_login = true`
- [ ] Confirmar que os outros dois projetos Streamlit/Git permanece intactos

## Secrets mínimos

```toml
[auth]
redirect_uri = "https://<ESTE-APP>.streamlit.app/oauth2callback"
cookie_secret = "..."
client_id = "..."
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[app]
allowed_emails = ["email1@gmail.com", "email2@gmail.com"]

# Alternativa: variável de ambiente DATABASE_URL no painel Cloud
```

Também defina `DATABASE_URL` (Postgres) no ambiente do app.

## Google Cloud OAuth

1. Criar cliente OAuth Web no Google Cloud do projecto familiar
2. Authorized redirect URI = `https://<ESTE-APP>.streamlit.app/oauth2callback`
3. Audience em Testing com os 2 e-mails
4. MFA já nas contas Google

## Pós-deploy

1. Abrir app → login Google
2. Confirmar CP `4815-413` (ou alterar em Configurações)
3. Consulta avulsa + lista + scanner
4. Correr job localmente/`workflow_dispatch` com `DATABASE_URL` de produção se aplicável
