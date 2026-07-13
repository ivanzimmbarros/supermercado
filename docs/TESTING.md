# Política obrigatória de testes

Estado: **obrigatória a partir de 2026-07-13** — aplica-se a **toda e qualquer etapa/épico** daqui em diante.

## Confirmação da instrução

Instrução do product owner **validada e confirmada**:

1. Para **todas** as etapas e épicos construídos, deve existir estrutura de:
   - testes **funcionais**
   - testes **e2e**
   - testes **simulados** (como utilizadores a navegar no sistema)
2. Estes testes devem ser **regularmente revistos, atualizados e alterados** quando o comportamento ou a UI mudarem.
3. Ao **término de qualquer etapa**, a suite completa deve ser **executada na íntegra**.
4. Em caso de **qualquer falha**, o código deve ser **reconstruído/corrigido** até que **todos** os testes passem com sucesso.
5. Nenhuma etapa se considera concluída sem este gate verde.

Esta política é parte do Definition of Done do projecto.

---

## Definition of Done (por etapa)

Uma etapa só está **DONE** quando:

- [ ] Código da funcionalidade implementado
- [ ] Testes unitários relevantes passam
- [ ] Testes funcionais da etapa passam
- [ ] Testes e2e afectados passam
- [ ] Testes de navegação simulada (utilizador) passam
- [ ] Suite completa do repositório está verde (`pytest`)
- [ ] Documentação/testes desactualizados foram revistos
- [ ] Commit + push da correção (se houve falha intermediária)

**Regra anti-atalho:** não avançar para a etapa seguinte com testes a falhar, a skippar permanentemente ou a comentário `# TODO fix later` bloqueante.

---

## Estrutura obrigatória

```text
tests/
├── unit/                  # regras puras / parsers / serviços isolados
├── functional/            # fluxos de negócio via serviços/API interna
├── e2e/                   # percursos ponta-a-ponta (incl. AppTest Streamlit)
├── simulated_users/       # roteiros de “Ivan” / “Esposa” a navegar e configurar
├── fixtures/              # HTML/JSON de providers e dados de apoio
└── conftest.py            # fixtures partilhadas
```

### O que cada camada cobre

| Camada | Objectivo | Exemplos |
|---|---|---|
| **Unit** | Funções puras e parsers | €/unidade, matching, validação de agenda |
| **Functional** | Casos de uso de domínio | mudar CP congela histórico; search grava snapshot; job respeita agenda |
| **E2E** | App completa / páginas | login gate → consulta → ver ranking; config alterar agenda |
| **Simulated users** | Navegação “humana” repetível | Utilizador altera CP, consulta leite, vê histórico do CP antigo intacto |

---

## Gate de execução (obrigatório no fim de cada etapa)

```bash
export PYTHONPATH=src
export SUPERMERCADO_DEV_BYPASS=1
python3 -m pytest -q
```

Ou o atalho:

```bash
python3 -m tests.run_all
```

Se houver falha: **corrigir código ou testes desactualizados** → voltar a correr → só então fechar a etapa.

---

## Revisão contínua

Sempre que uma etapa alterar comportamento:

1. Actualizar ou acrescentar testes nas 3 camadas impactadas
2. Remover asserções obsoletas (não “deixar passar” com asserts frouxos sem justificativa)
3. Manter fixtures de providers alinhadas com HTML real quando o parser mudar
4. Nos PRs, referir o resultado da suite completa

---

## Agente / desenvolvimento assistido

Para o agente Cursor / qualquer executor automático:

- Tratar esta política como **user rule permanente** deste repositório
- No final de cada etapa: correr a suite completa
- Se falhar: iterar em ciclo *fix → fail → fix* até verde
- Não declarar a etapa completa sem evidência de suite verde
