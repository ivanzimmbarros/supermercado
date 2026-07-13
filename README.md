# supermercado

Sistema familiar de listas de compras e comparação de preços em supermercados de Portugal (Python + Streamlit).

## Isolamento

Este repositório e o app Streamlit são **independentes** de quaisquer outros projetos Git/Streamlit. Não partilham secrets, base de dados, jobs nem configuração de deploy.

## Documentação

- [Escopo MVP](docs/MVP_SCOPE.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Configuração dinâmica e histórico por CP](docs/CONFIGURATION.md)
- [Política obrigatória de testes](docs/TESTING.md)
- [Deploy isolado](docs/DEPLOY.md)
- [Regras do agente](AGENTS.md)

## Princípio: zero hardcode operacional

Código postal, agenda do job (dias/hora/quantidade), janelas 15/30/60 e mercados ativos vivem em `app_settings` / `geo_contexts` e alteram-se na página **Configurações**. Defaults existem apenas como *seed* de first-boot.

Seed inicial da agenda: terça e sexta, 07:00, `Europe/Lisbon` (2 execuções).  
Seed do CP: `4815-413` (Vizela). Mudar o CP congela o histórico anterior; reativar um CP antigo retoma a série sem apagar dados.

## Arranque local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
export SUPERMERCADO_DEV_BYPASS=1   # só local, sem Google OIDC
python -m supermercado.bootstrap
streamlit run app/Home.py
```

Para produção familiar: configure `.streamlit/secrets.toml` a partir de `.streamlit/secrets.toml.example` (Google OAuth + allowlist) e **desligue** o bypass em Configurações.

Job (respeita agenda da BD):

```bash
export PYTHONPATH=src
python -m supermercado.jobs.recurring_collect
python -m supermercado.jobs.recurring_collect --force
```

Testes (gate obrigatório ao fim de cada etapa):

```bash
export PYTHONPATH=src SUPERMERCADO_DEV_BYPASS=1
python3 -m tests.run_all
```

Camadas: `tests/unit`, `tests/functional`, `tests/e2e`, `tests/simulated_users`.  
Qualquer falha ⇒ corrigir e voltar a correr até verde (ver [`docs/TESTING.md`](TESTING.md)).

## Estado da implementação

- [x] Configuração dinâmica (CP, agenda, janelas, mercados, allowlist)
- [x] Histórico particionado por código postal
- [x] Auth Google + allowlist (gate nas páginas)
- [x] Normalizer €/unidade + matching idêntico/similar
- [x] Providers Continente e Pingo Doce + consulta avulsa
- [x] Histórico / melhores janelas
- [x] Recorrentes + job que lê a agenda
- [x] Estrutura obrigatória de testes unit/functional/e2e/utilizadores simulados
- [x] Listas de compras com comparação €/unidade por item
- [x] Scanner EAN (manual / câmara / upload)
- [x] Documentação e checklist de deploy Streamlit isolado
- [ ] Publicação efectiva no Streamlit Cloud (requer secrets Google + Postgres do owner)
