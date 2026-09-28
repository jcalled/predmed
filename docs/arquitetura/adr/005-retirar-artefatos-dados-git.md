# ADR-005 — Retirar artefatos e dados do git

- **Status:** Proposto. **NÃO EXECUTAR** sem aprovação explícita do responsável, passo a passo.
- **Data:** 28/09/2026

## Contexto

Levantamento feito em 28/09/2026 com `git ls-files`, `git count-objects` e `git rev-list --objects`:

- 35.917 arquivos rastreados, dos quais cerca de 35.000 são artefatos:

  | Artefato | Arquivos |
  |---|---|
  | `frontend/node_modules` | 13.420 |
  | `venv/` na raiz | ~11.000 |
  | `backend/venv` | 10.886 |
  | `__pycache__` | 8.648 (sobreposto aos venvs) |
  | `lightning_logs` | 363 |
  | `.next` | 72 |

- Dados rastreados:
  - `backend/predmed.db` (contém a fila importada);
  - 2 CSVs `consulta-fila-espera_*.csv` com colunas `INIC_NOME_PACIENTE` e `NUN_SOLICITACAO` (**dado pessoal de saúde**);
  - 72 `.dbc` do SIH (públicos, 218 MB);
  - `CNES-ceara.json`.
- O histórico de `main` contém `backend/predmed.db` com **1,8 GB** em um commit antigo, o binário `next-swc` de 110 MB e `backend/_SCRIPTS/SIH/dados_sih.csv` (11,6 MB). `.git` ocupa 941 MB.
- Não há ref remota local (`origin/main`). O GitHub recusa blobs acima de 100 MB, então **não se sabe o que existe hoje no remoto** `github.com/jcalled/predmed` (privado).
- Há também a ref `refs/codex/turn-diffs/...` (ferramenta externa), que retém blobs grandes.
- O `.gitignore` já cita venv, node_modules, .next e `*.db`, mas isso **não remove** arquivos já rastreados.

## Decisão

Executar em **duas fases independentes**, com aprovação separada.

### Fase A — Parar de versionar (sem reescrever histórico)

Reversível e sem risco para os arquivos locais.

1. **Backup verificado fora do repositório** (antes de tudo):
   - copiar `backend/predmed.db`, `backend/predmed-original.db` e `backend/data/` para um disco ou volume criptografado fora da pasta do projeto;
   - registrar `sha256sum` de cada arquivo em um manifesto, **sem** conteúdo;
   - fazer um espelho completo do repositório como está: `git clone --mirror` para um local criptografado.
2. **Verificar o remoto no GitHub:** branches e tags existentes, se os CSVs e o `.db` estão lá, quem tem acesso, forks e se há Actions ou caches. Registrar o resultado.
3. **Completar o `.gitignore`**:

   ```gitignore
   # Python
   **/venv/
   **/.venv/
   **/__pycache__/
   *.pyc

   # Node / Next
   **/node_modules/
   **/.next/
   **/out/

   # ML
   **/lightning_logs/
   **/.neuralprophet_ckpt/
   **/prophet_models/
   *.ckpt

   # Dados — nunca versionar
   *.db
   *.sqlite*
   *.dbc
   *.dbf
   *.parquet
   backend/data/
   data/
   **/*fila-espera*.csv

   # Segredos
   .env
   .env.*
   !.env.example

   # SO / logs
   .DS_Store
   *.log
   ```

   Exceção explícita para fixtures sintéticas, por exemplo `!tests/fixtures/**`.
4. **Remover somente do índice** (os arquivos locais permanecem):

   ```bash
   git rm -r --cached venv backend/venv frontend/node_modules frontend/.next \
     backend/lightning_logs backend/prophet_models backend/data backend/predmed.db
   git rm -r --cached $(git ls-files | grep -E '__pycache__|\.DS_Store$')
   ```

   Criar `data/README.md` descrevendo as fontes (IntegraSUS, DATASUS FTP, CNES), como obter e onde ficam as cópias de acesso restrito.
5. Conferir `git status` e `ls` para confirmar que os arquivos locais continuam presentes. Rodar `./start.sh`. Commit único, sem push até a revisão.

Efeito: novos commits ficam limpos. **O histórico continua contendo os dados pessoais e o blob de 1,8 GB.** A Fase A não resolve a exposição passada.

### Fase B — Reescrever o histórico

Destrutiva para o histórico; exige aprovação explícita.

Pré-condições: Fase A concluída; backup espelho verificado; todos os colaboradores avisados; nenhum PR aberto.

1. Em um **clone espelho novo** (nunca na cópia de trabalho), usar `git filter-repo` para remover:
   - caminhos: `venv/`, `backend/venv/`, `frontend/node_modules/`, `frontend/.next/`, `backend/lightning_logs/`, `backend/__pycache__/`, `backend/data/`, `backend/_SCRIPTS/SIH/dados_sih.csv`, `backend/prophet_models/`;
   - globs: `*.db`, `*.dbc`, `*.csv` de dados;
   - opcionalmente, `--strip-blobs-bigger-than 10M`.
2. Remover refs de ferramentas (`refs/codex/*`) no clone reescrito e rodar `git gc --prune=now --aggressive`.
3. Validar:
   - `git rev-list --objects --all` não contém os caminhos removidos;
   - tamanho final esperado de poucos MB;
   - o projeto compila;
   - `./start.sh` roda com os dados restaurados do backup para `data/`.
4. Publicar: `git push --force --mirror` para o remoto privado, **ou, preferível, criar um repositório novo** e arquivar o antigo como privado com acesso restrito. Repositório novo evita que forks e caches retenham os objetos.
5. No GitHub: pedir ao suporte a remoção de objetos em cache e de referências de PRs (os objetos podem persistir em `refs/pull/*`); revisar forks e colaboradores; invalidar caches de Actions.
6. Todos os colaboradores fazem **clone novo**. Não fazer `pull` sobre o histórico antigo, que reintroduziria os objetos.
7. Registrar o evento como incidente de segurança de dados (baixo alcance: repositório privado). Avaliar com o jurídico se há dever de comunicação à controladora.

### Onde ficam os dados depois

| Dado | Destino |
|---|---|
| SIH `.dbc` (público) | Baixado pelo job a partir do FTP do DATASUS; cópia em bucket de artefatos (R2/S3) |
| CNES | Baixado pelo job; versão em bucket |
| Fila IntegraSUS | Bucket **com dado pessoal na região Brasil**, criptografado, retenção curta; banco com pseudonimização (ADR-004) |
| `predmed-original.db` | Não migrar como arquivo; recarregar o SIH no Postgres a partir dos `.dbc` (ADR-002). Manter cópia local cifrada até a reconciliação (T05) |
| Modelos treinados | Bucket `modelos/<versão>/`, com métricas no banco |
| Fixtures de teste | `tests/fixtures/` **sintéticas**, geradas por script |

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Só Fase A | Rápida e segura, mas mantém dado pessoal e 1,8 GB no histórico. Aceitável como primeiro passo, não como estado final |
| BFG Repo-Cleaner | Equivalente; `git filter-repo` é a recomendação atual do próprio git |
| Git LFS para os dados | Não resolve LGPD: dado pessoal continuaria no repositório |
| Apagar o repositório e recomeçar sem histórico | Mais simples que a Fase B, mas perde o histórico de código. Viável se o histórico não tiver valor; decisão do responsável |

## Consequências

- Clone passa de ~940 MB para poucos MB. O CI fica viável e a exposição de dados no repositório termina.
- A Fase B muda todos os hashes de commit; links antigos para commits deixam de funcionar.
- `start.sh` precisa encontrar os dados em `data/` local (ajuste pequeno, passo M1 de [estrutura-pastas.md](../estrutura-pastas.md)).
