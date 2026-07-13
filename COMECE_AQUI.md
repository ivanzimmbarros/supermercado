# Como usar a app em casa (sem ser técnico)

## Pasta oficial no seu Windows

Tudo o que for uso local neste PC deve estar / ser actualizado nesta pasta:

```text
C:\Users\ivanz\OneDrive\Documentos\Projetos - AI\3. Supermercado
```

Ficheiro para iniciar a app:

```text
C:\Users\ivanz\OneDrive\Documentos\Projetos - AI\3. Supermercado\iniciar_app.bat
```

Faça **duplo clique** em `iniciar_app.bat` e abra **http://localhost:8501**.

---

## Importante: alinhamento com o Git

O agente na cloud **não escreve directamente** na pasta do OneDrive.  
A fonte de verdade do código é o GitHub (`ivanzimmbarros/supermercado`).

Para a sua pasta Windows ficar alinhada com o Git:

1. Preferir a branch onde está o código completo: `cursor/architecture-design-b771`  
   (ou `main`, quando o Pull Request for aceite)
2. Actualizar a pasta local sempre a partir do GitHub (Download ZIP da branch correcta **ou** `git pull` se a pasta for um clone Git)
3. Não misturar pastas antigas / ZIPs diferentes — use **sempre** esta pasta oficial acima

### Se a pasta ainda tiver só o README
Então descarregou a branch `main` (incompleta). Volte a descarregar a branch  
`cursor/architecture-design-b771` e extraia **por cima** desta pasta oficial (ou limpe e volte a extrair).

---

## Opção A — Windows (a sua)
1. Abra a pasta oficial acima no Explorador de Ficheiros
2. Duplo clique em `iniciar_app.bat`
3. Espere abrir o browser em **http://localhost:8501**

## Opção B — Mac / Linux
1. Abra a pasta do projeto no Terminal
2. Execute: `./iniciar_app.sh`
3. Abra **http://localhost:8501**

## Dentro da app
- **Consulta avulsa** — pesquisar preços
- **Listas** — lista de compras e comparar
- **Histórico** — preços no tempo
- **Recorrentes** — produtos a seguir
- **Configurações** — código postal, agenda, etc.

## Parar a app
Feche a janela preta/terminal ou prima `Ctrl+C`.

## Nota
Este modo local não precisa de login Google.  
A publicação no Streamlit Cloud (com Google) é um passo separado, mais tarde.
