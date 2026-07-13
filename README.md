# supermercado

Sistema familiar de listas de compras e comparação de preços em supermercados de Portugal (Python + Streamlit).

## Isolamento

Este repositório e o app Streamlit são **independentes** de quaisquer outros projetos Git/Streamlit. Não partilham secrets, base de dados, jobs nem configuração de deploy.

## Documentação

- [Escopo MVP](docs/MVP_SCOPE.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Configuração dinâmica e histórico por CP](docs/CONFIGURATION.md)

## Princípio: zero hardcode operacional

Código postal, agenda do job (dias/hora/quantidade), janelas 15/30/60 e mercados ativos vivem em `app_settings` / `geo_contexts` e alteram-se na página **Configurações**. Defaults existem apenas como *seed* de first-boot.

Seed inicial da agenda: terça e sexta, 07:00, `Europe/Lisbon` (2 execuções).  
Seed do CP: `4815-413` (Vizela). Mudar o CP congela o histórico anterior; reativar um CP antigo retoma a série sem apagar dados.

## Arranque local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python -m supermercado.bootstrap
streamlit run app/Home.py
```

Job (respeita agenda da BD):

```bash
export PYTHONPATH=src
python -m supermercado.jobs.recurring_collect
# ou
python -m supermercado.jobs.recurring_collect --force
```

Testes:

```bash
export PYTHONPATH=src
pytest -q
```

## MVP (resumo)

- 2 utilizadores, login Google + MFA da conta Google (próxima etapa)
- Mercados MVP: Continente e Pingo Doce
- Ranking: preço final €/unidade, só disponíveis
- Histórico particionado por código postal
- Scanner EAN (etapa seguinte)
