# Testar no Streamlit Cloud (sem Windows / sem Defender)

Use isto em vez do `iniciar_app.bat` enquanto o Defender bloquear o PC.

## 1) Criar um app NOVO (não mexa nos outros dois)

1. Abra: https://share.streamlit.io/  (ou https://streamlit.io/cloud)
2. Faça login com a mesma conta GitHub (`ivanzimmbarros`)
3. Clique **New app** / **Create app**
4. Preencha exactamente:

| Campo | Valor |
|---|---|
| Repository | `ivanzimmbarros/supermercado` |
| Branch | `cursor/architecture-design-b771` |
| Main file path | `app/Home.py` |
| App URL / nome | algo novo, ex. `supermercado-familiar` |

5. Confirme que **não** está a editar os seus outros apps existentes.

## 2) Secrets (modo teste, sem Google)

1. No app novo: **Settings** → **Secrets**
2. Cole isto:

```toml
[app]
dev_bypass = true
allowed_emails = ["ivanzimmbarros@gmail.com"]
```

3. Guarde / Save

## 3) Deploy

1. Clique **Deploy**
2. Espere a build terminar (pode demorar alguns minutos na 1ª vez)
3. Abra o link `https://….streamlit.app`

## 4) O que testar

- Página inicial com CP `4815-413`
- **Consulta avulsa** (ex.: `leite uht`)
- **Listas** (criar lista e adicionar item)
- **Configurações**
- **Histórico** / **Recorrentes**

## Notas importantes

- Este modo `dev_bypass = true` é **só para teste**. Depois ligamos login Google.
- Sem Postgres externo, os dados podem apagar-se quando o app hiberna — normal no teste.
- Se a branch no ecrã for `main`, mude para `cursor/architecture-design-b771` (a `main` ainda está quase vazia).

## Se der erro

Copie a mensagem da build/logs do Streamlit e envie — eu corrijo no Git e você só volta a fazer **Reboot app** / Redeploy.
