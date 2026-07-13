# Escopo MVP — Sistema Familiar de Comparação de Preços

Estado: **congelado + refinamentos de configuração** (2026-07-13).  
Idioma da UI: **português**.  
Repositório: `ivanzimmbarros/supermercado` (isolado dos outros projetos Git/Streamlit).  
Configuração: ver [`CONFIGURATION.md`](CONFIGURATION.md) — **zero hardcode** de regras operacionais.

## Objetivo

Aplicação familiar (2 utilizadores) em Python + Streamlit para:

1. Criar e gerir listas de compras
2. Comparar preços entre supermercados pré-definidos
3. Fazer consultas avulsas
4. Acompanhar produtos recorrentes
5. Guardar histórico de preços/promoções e indicar melhores oportunidades (15/30/60 dias)

## Utilizadores e autenticação

| Item | Decisão |
|---|---|
| Utilizadores | Apenas 2 (casal) |
| Login | Google OIDC nativo do Streamlit |
| MFA | 2FA da conta Google |
| Autorização | Allowlist de e-mails (só os 2 Gmail autorizados) |

## Âncora geográfica (configurável)

- Seed inicial: **4815-413** (Vizela, Braga) — apenas no first boot
- Alterável na UI de configuração (`GeoContextService`)
- Cada código postal tem série histórica **própria**; mudança de CP congela a série anterior e cria/reativa outra
- Voltar a um CP antigo **retoma** o histórico previo (append) — nunca apaga
- Consultas de oportunidade/histório são sempre filtradas pelo `geo_context` selecionado

## Mercados

| Fase | Mercados | Notas |
|---|---|---|
| **MVP** | Continente, Pingo Doce | Endpoints SFCC/Demandware testados e viáveis |
| **v2** | Lidl | JSON embutido / ofertas semanais |
| **v2** | Intermarché | Anti-bot forte; provavelmente browser automation |
| **v2** | Aldi | Folhetos/oportunidades da semana, não catálogo full |

## Regras de negócio (MVP)

### Melhor oportunidade / melhor preço

1. Considerar apenas ofertas **disponíveis** no ranking atual
2. Usar **preço final** (já com promoção, se existir)
3. Comparar sempre por **€ por unidade canónica** (€/L, €/kg, €/un)
4. Em empate: preferir match `IDÊNTICO` a `SIMILAR`
5. Indisponível: fora do ranking, mas **persiste no histórico**

### Promoções

- Badge visual `PROMO` / `NORMAL` (+ % ou preço anterior quando disponível)
- Snapshot de histórico inclui flag promo, preço antes, validade e label

### Matching de produtos

1. EAN (scanner ou manual) → idêntico
2. Marca + atributos + quantidade/unidade
3. Se falhar → candidatos **similares** da mesma natureza
4. Comparação justa via preço/unidade (ex.: 250 ml vs 500 ml)
5. Utilizador confirma/corrige match; sistema memoriza

### Scanner

- Entrada por fotografia/upload ou código manual
- Serve de referência para busca exacta e similares
- UX mobile-first pragmática no Streamlit

### Recorrentes e agenda (configurável)

- Seed: **terça e sexta, 07:00, Europe/Lisbon, 2 execuções/semana**
- UI permite definir: quantidade de execuções, dias da semana e hora padrão
- Invariante: `len(dias) == quantidade_execucoes`
- Runner consulta a config em runtime (sem dias/hora hardcoded no código de negócio)

### Histórico / oportunidades

Respostas do tipo:

- Melhor preço do produto X nos últimos **15 / 30 / 60** dias (janelas também configuráveis)
- Sempre com base no **preço final por unidade**
- Sempre no âmbito do **código postal** ativo ou selecionado para consulta

## Módulos funcionais MVP

1. Autenticação Google + allowlist
2. **Configurações** (CP, agenda do job, janelas, mercados) — sem hardcode
3. Cadastro rico de produtos (+ scanner EAN)
4. Consulta avulsa
5. Listas de compras + comparação
6. Providers Continente e Pingo Doce
7. Histórico particionado por CP + janelas configuráveis
8. Recorrentes + runner que lê a agenda da BD
9. Deploy Streamlit isolado

## Explicitamente fora do MVP

- Lidl, Intermarché, Aldi (stubs/arquitetura preparados)
- Alertas WhatsApp/e-mail
- Otimização multi-loja da lista completa
- Previsão ML de promoções
- Perfis avançados além dos 2 utilizadores

## Critérios de “MVP pronto”

- Login Google funciona só para os 2 e-mails
- Consulta avulsa compara Continente vs Pingo Doce com €/unidade
- Lista mostra melhor oportunidade disponível com badges promo/stock
- Histórico guarda promo e permite consulta 15/30/60 dias
- Recorrentes atualizam 2×/semana
- Zero impacto nos outros apps/repos Streamlit/Git existentes
