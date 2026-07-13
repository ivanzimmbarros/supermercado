# Regras obrigatórias do projeto supermercado

## Pasta local do utilizador (Windows)

Referência oficial no PC do owner (não acessível directamente pela cloud):

```text
C:\Users\ivanz\OneDrive\Documentos\Projetos - AI\3. Supermercado
```

O agente trabalha no repositório Git (`/workspace` ↔ GitHub).  
Qualquer instrução de “local” deve apontar para essa pasta Windows e lembrar que a sincronização é via Git/ZIP da branch correcta — nunca assumir escrita directa no OneDrive.

## Gate de testes (Definition of Done)

Para **toda e qualquer etapa/épico** daqui em diante:

1. Construir/actualizar testes **funcionais**, **e2e** e **navegação simulada** (além de unitários).
2. No fim da etapa, correr a suite completa e só fechar se estiver **100% verde**.
3. Se algum teste falhar: **corrigir código ou testes** e repetir até passar.
4. Revistar e actualizar testes sempre que o comportamento mudar.

Referência: `docs/TESTING.md`

Comando:

```bash
export PYTHONPATH=src SUPERMERCADO_DEV_BYPASS=1
python3 -m tests.run_all
```
