# supermercado

Sistema familiar de listas de compras e comparação de preços em supermercados de Portugal (Python + Streamlit).

## Estado atual

Fase de **definição teórica** concluída em documentação:

- [Escopo MVP](docs/MVP_SCOPE.md)
- [Arquitetura](docs/ARCHITECTURE.md)

A construção da aplicação começa após aprovação destes documentos.

## Isolamento

Este repositório e o futuro app Streamlit são **independentes** de quaisquer outros projetos Git/Streamlit do autor. Não partilham secrets, base de dados, jobs nem configuração de deploy.

## MVP (resumo)

- Utilizadores: 2 (login Google + MFA da conta Google)
- Mercados: Continente e Pingo Doce (Lidl, Intermarché e Aldi em v2)
- Código postal de referência: `4815-413` (Vizela)
- Ranking: preço final por unidade (€/L, €/kg, €/un), só itens disponíveis
- Histórico com promoções e melhores oportunidades em 15/30/60 dias
- Produtos recorrentes atualizados 2× por semana
- Scanner EAN como referência de matching
