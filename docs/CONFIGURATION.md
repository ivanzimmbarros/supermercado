# Configuração dinâmica e histórico por código postal

## Validação do pedido

Pedido aceite com refinamentos abaixo. Princípio obrigatório:

> **Nada de referência operacional fica hardcoded no código de negócio.**  
> Defaults existem apenas como *seed* inicial; em runtime tudo passa por `ConfigService` / UI de configuração.

---

## Crítica e refinamentos

### 1. Job: terça e sexta 07:00

**Aceite** como seed inicial (`Europe/Lisbon`).

**Crítica:** se o horário/dias ficarem só no cron do GitHub Actions, voltam a ser hardcode fora da app.

**Desenho:**

| Peça | Responsabilidade |
|---|---|
| `ConfigService` | Guarda `weekdays`, `time`, `timezone`, `enabled`, `executions_per_week` |
| UI Configurações | Altera esses valores sem deploy |
| Runner (GH Actions ou equivalente) | Dispara com frequência curta (ex. a cada 15 min), **consulta a config** e só executa se o momento atual casar; usa lock/`last_run_at` para não duplicar |

Assim terça/sexta 07:00 não estão “graviados” no workflow — são dados.

### 2. “Quantidade de execuções” + dias + hora

**Risco de conflito:** 3 execuções/semana mas só 2 dias selecionados (ou o inverso).

**Regra adotada:**

- `weekdays` é a fonte de verdade (ex.: `["tue", "fri"]`)
- `executions_per_week` é **derivado** de `len(weekdays)` **ou** imposto na UI com validação:
  - utilizador define N
  - escolhe exactamente N dias
  - define hora padrão + timezone
- Invariante: `len(weekdays) == executions_per_week`
- Hora única por execução (MVP): todas as execuções usam o mesmo `schedule_time` (07:00 por seed)

Se no futuro precisar de horas diferentes por dia, isso será lista de slots `{weekday, time}` — fora do MVP, mas o modelo de settings aguenta JSON.

### 3. Zero hardcode

**Aceite.** Aplicável a:

- código postal ativo
- agenda do job
- mercados habilitados
- allowlist (secrets + config)
- timezone
- janelas de oportunidade (15/30/60) — também configuráveis
- cadence labels / parâmetros de matching thresholds (seed + config)

**Exceção legítima (não é regra de negócio):** constantes técnicas internas (nomes de colunas SQL, chaves de schema, timeouts de HTTP default com override por config).

Código de domínio **não** pode conter `POSTAL = "4815-413"` nem `DAYS = [1,4]`. Apenas:

```text
config = ConfigService.get()
geo = config.active_geo()
schedule = config.recurring_schedule()
```

### 4. Histórico por código postal (pedido crítico — bem desenhado)

**Aceite por completo.** Modelo:

```text
geo_contexts
  postal_code UNIQUE
  locality, district, ...
  status: active | frozen
  activated_at / deactivated_at
  never deleted

price_snapshots.geo_context_id  → obrigatório
opportunity queries             → sempre filtradas por geo_context_id
```

**Comportamento ao mudar o CP:**

1. CP atual → `frozen` (deixam de entrar novos snapshots neste contexto enquanto não for reativado)
2. Se o novo CP **já existiu** → reativa (`active`) e **retoma** o histórico antigo (append)
3. Se o novo CP é **novo** → cria `geo_contexts` novo + série histórica vazia
4. **Nunca** apaga nem funde snapshots entre CPs diferentes
5. UI de histórico permite **selecionar** um CP (ativo ou congelado) para consultar tendências sem misturar séries

**Crítica útil:** preços e stock dependem da zona. Misturar 4815-413 com outro CP na mesma série corromperia “melhor dos 30 dias”. Por isso a partição por CP é correta e obrigatória.

**Também particionar (mesmo `geo_context_id`):**

- preferências de loja por mercado
- corridas do job / coletas
- (opcional MVP+) caches de disponibilidade

Produtos canónicos da família e matches **podem** ser globais (o extrato de tomate é o mesmo produto); o que muda com o CP é a **observação de preço/stock**.

### 5. “Nova estrutura de comparação histórica”

Interpretado como:

- série temporal **independente por geo_context**
- ranking 15/30/60 e “melhor oportunidade” calculados **dentro** do CP selecionado
- ao voltar ao CP antigo, as métricas reaparecem com continuidade

Não é um segundo schema físico distinto (evita explosão de tabelas); é a **mesma estrutura**, chaveada por `geo_context_id`.

---

## Seed inicial (só na migração / first boot)

| Chave | Valor inicial |
|---|---|
| `active_postal_code` | `4815-413` |
| `schedule.weekdays` | `tue`, `fri` |
| `schedule.time` | `07:00` |
| `schedule.timezone` | `Europe/Lisbon` |
| `schedule.executions_per_week` | `2` |
| `schedule.enabled` | `true` |
| `opportunity_windows_days` | `[15, 30, 60]` |
| `markets.enabled` | `continente`, `pingo_doce` |

Depois disso, qualquer alteração é pela UI/API de configuração.

---

## Serviços obrigatórios de configuração

| Serviço | Responsabilidade |
|---|---|
| `ConfigService` | Ler/escrever settings versionados |
| `GeoContextService` | Ativar/criar/congelar CP; listar históricos |
| `ScheduleService` | Validar dias/hora/N; dizer se “deve correr agora” |
| `OpportunityService` | Sempre receber `geo_context_id` (nunca implícito mágico no SQL sem filtro) |

Auditoria leve: `settings_audit` (quem alterou, de→para, quando) — importante com 2 utilizadores.

---

## Veredito

Pedido **válido e superior** ao MVP anterior. A partição histórica por CP e a banimento de hardcode elevam a qualidade do sistema. Os únicos pontos a disciplinar são: (1) invariante N dias = N execuções, (2) runner que lê a agenda da base, (3) produtos canónicos globais vs observações de preço por geo.
