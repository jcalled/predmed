# Estrutura de pastas alvo e plano de migração

- **Status:** proposta, aguardando aprovação do responsável
- **Data:** 28/09/2026
- **Decisão relacionada:** [ADR-001](adr/001-estrutura-monorepo.md)

## 1. Princípios

1. **Monorepo único** (um repositório privado) com aplicações e pacotes separados. O time é pequeno e o versionamento conjunto API/web/ML simplifica o CI.
2. **Backend em camadas**: rota → serviço → repositório → modelo. A regra de negócio não conhece FastAPI nem SQL.
3. **ETL e ML fora da API**: rodam como jobs (mesma imagem ou imagem própria) e escrevem no banco/armazenamento. A API apenas lê resultados versionados.
4. **Nada específico de provedor no código de domínio**: diferenças Cloudflare/AWS ficam em `infra/` e em adaptadores (`core/storage.py`, `core/config.py`).
5. **Dados nunca no git**: `data/` local ignorado, com um README descrevendo as fontes; amostras só **sintéticas** em `tests/fixtures/`.

## 2. Estrutura alvo

```
predmed/
├── apps/
│   ├── api/                          # FastAPI (contêiner)
│   │   ├── pyproject.toml            # deps da API (sem torch)
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── migrations/               # Alembic
│   │   ├── src/predmed_api/
│   │   │   ├── main.py               # cria app, middlewares, inclui routers
│   │   │   ├── core/
│   │   │   │   ├── config.py         # pydantic-settings: DATABASE_URL, SECRET_KEY, CORS, STORAGE_*
│   │   │   │   ├── security.py       # JWT, hash, dependências de RBAC
│   │   │   │   ├── tenancy.py        # Escopo(tenant, cir, municipio, cnes) + filtros
│   │   │   │   ├── audit.py          # registro de auditoria
│   │   │   │   ├── logging.py        # logs JSON, mascaramento
│   │   │   │   └── storage.py        # interface ObjectStorage (S3 API: R2 ou S3)
│   │   │   ├── db/
│   │   │   │   ├── session.py        # engine, get_db
│   │   │   │   └── models/           # tenant.py, usuario.py, fila.py, hospital.py, sih.py, auditoria.py
│   │   │   ├── repositories/         # consultas SQL por agregado, sempre recebem Escopo
│   │   │   ├── schemas/              # Pydantic de entrada/saída
│   │   │   ├── services/             # dashboard, fila, priorizacao, redistribuicao, previsoes, analytics
│   │   │   └── api/routers/          # auth, dashboard, fila, hospitais, redistribuicao,
│   │   │                             # priorizacao, previsoes, analytics, admin_import, health
│   │   └── tests/
│   │       ├── unit/  integration/  fixtures/ (sintéticos)
│   └── web/                          # Next.js (atual frontend/)
│       ├── src/…
│       ├── open-next.config.ts       # somente quando adotar Cloudflare
│       └── tests/
├── packages/
│   ├── domain/                       # regras puras: SWALIS, CIR, pressão, score (sem I/O)
│   └── ml/                           # previsão: preparo de série, modelos, avaliação (MAPE holdout), registry
│       └── pyproject.toml            # statsmodels, (prophet/torch opcionais em extra)
├── pipelines/
│   ├── etl/                          # jobs: cnes, datasus, integrasus, sih (download_sih, sigtap)
│   │   ├── jobs/                     # um módulo por fonte, idempotente, com snapshot
│   │   └── Dockerfile                # imagem de jobs (ETL + treino)
│   └── treino/                       # job de treino/avaliação que publica modelo + métricas
├── infra/
│   ├── docker/compose.yml            # dev local: postgres, minio (S3), api, web
│   ├── cloudflare/                   # wrangler.jsonc (web, containers, cron), sem segredos
│   ├── aws/                          # terraform/ ou cdk/ (ECS/App Runner, RDS, S3)
│   └── scripts/                      # backup/restore, rotação de segredos
├── .github/workflows/                # ci.yml, deploy-homolog.yml, deploy-prod.yml
├── docs/
│   ├── arquitetura/ (este diretório, ADRs)
│   ├── dados/ (dicionário, fontes, RIPD)
│   └── operacao/ (runbooks, backup, incidentes)
├── data/                             # IGNORADO no git — dados locais (CSV, .dbc, .db)
├── start.sh                          # continua subindo o ambiente local
└── README.md
```

### Mapeamento do código atual

| Atual | Destino |
|---|---|
| `backend/main.py` (rotas) | `apps/api/src/predmed_api/api/routers/*.py` |
| `backend/main.py` (schemas `:122-138`) | `.../schemas/` |
| `backend/main.py:650-715` (Zerar Filas) | `.../services/zerar_filas.py` |
| `backend/auth.py` | `.../core/security.py` |
| `backend/database.py` | `.../db/session.py` + `.../db/models/*` |
| `backend/services/ia_engine.py` | `services/dashboard.py`, `services/redistribuicao.py`, parte em `packages/domain` |
| `backend/services/cir_config.py` | `packages/domain/cir.py` |
| `backend/services/previsoes*.py` | `packages/ml/` (treino) + `services/previsoes.py` (leitura de resultados) |
| `backend/services/analytics_sih.py` | `repositories/sih.py` + `services/analytics.py`; MAPE em `packages/ml/avaliacao.py` |
| `backend/services/data_import.py` | `pipelines/etl/jobs/{cnes,datasus,integrasus}.py` |
| `backend/_SCRIPTS/**` | `pipelines/etl/jobs/sih/`, `pipelines/etl/ferramentas/` |
| `backend/seed.py` | `apps/api/scripts/seed_dev.py` (não destrutivo, só dev) |
| `backend/database_original.py`, `teste.py` | removidos (após confirmação) |
| `frontend/` | `apps/web/` |
| `backend/data/`, `*.db` | `data/` local, fora do git; bases de nuvem no Postgres/objeto |

## 3. Plano de migração incremental

Regras: um PR por passo; **`./start.sh` funcionando ao fim de cada passo**; cada passo tem um critério de reversão. Nenhum passo apaga `.db`, CSV ou `.dbc`. Os passos M0–M3 dão segurança e podem ser feitos antes de mover pastas.

| Passo | O que fazer | Mantém `start.sh`? | Reversão |
|---|---|---|---|
| **M0 — Proteção de dados** | Backup local fora do repositório de `predmed.db`, `predmed-original.db`, `backend/data/` (cópia + `sha256sum`). Verificar no GitHub o que foi efetivamente enviado. | Sim, não toca código | n/a |
| **M1 — Parar de versionar novos artefatos** | Completar `.gitignore` e rodar `git rm -r --cached` em venv/node_modules/.next/pycache/lightning_logs/data/*.db (**remove apenas do índice**; arquivos locais ficam). Ver ADR-005, fase A. | Sim | `git revert` do commit |
| **M2 — Dependências reais** | `requirements.txt` com o que é importado e versões fixas (statsmodels, dateutil; torch/neuralprophet em `requirements-ml.txt` opcional); `pip freeze` de referência; tornar o import de torch preguiçoso. | Sim (`pip install -r`) | reverter arquivo |
| **M3 — Config e segredos** | Criar `core/config.py` (pydantic-settings). `SECRET_KEY` obrigatória fora de `ENV=dev`; CORS por variável; `.env.example`; `start.sh` gera `.env` dev se ausente. Seed **não destrutivo** (só cria se não existir). | Sim | reverter |
| **M4 — Testes de caracterização** | `pytest` + `TestClient` em SQLite temporário com fixtures **sintéticas**: login, RBAC e isolamento por papel (testes que hoje **falham** documentam D02, marcados `xfail`), smoke das 31 rotas. | Sim | n/a |
| **M5 — Routers** | Mover rotas de `main.py` para `backend/routers/*.py` com `APIRouter`, **sem mudar URLs**. `main.py` passa a só incluir routers. Um router por PR, com testes do M4 verdes. | Sim | reverter PR |
| **M6 — Schemas e escopo de tenant** | `schemas/`; `core/tenancy.py` com `Escopo` derivado do usuário; aplicar em `/fila`, `/priorizacao`, `/judicializados`, `/dashboard`; remover `xfail`. | Sim | reverter |
| **M7 — Repositórios** | Extrair consultas de `main.py` e dos serviços para `repositories/`. Serviços recebem repositórios. | Sim | reverter |
| **M8 — Alembic + Postgres local** | `alembic init`, migração baseline a partir dos modelos atuais; `infra/docker/compose.yml` com Postgres 16. `start.sh` continua em SQLite por padrão; `DATABASE_URL=postgresql://…` opcional. Ver ADR-002. | Sim | `DATABASE_URL` volta a SQLite |
| **M9 — Auditoria** | Tabela `auditoria` + middleware/dependência; registrar login, importações, configuração de vagas, "recomendação revisada". Ver ADR-004. | Sim | migração `downgrade` |
| **M10 — Separar ETL/ML** | Mover `data_import` e `_SCRIPTS` para `pipelines/etl` como CLI (`python -m pipelines.etl integrasus --arquivo ...`); import com **staging + troca atômica** (não apagar antes de validar); treino publica resultado em tabela `previsao_resultado` versionada; API só lê. Upload da API grava o arquivo no armazenamento de objetos e enfileira job. | Sim (`start.sh` chama CLI de ETL no lugar do seed) | reverter |
| **M11 — Reorganizar em monorepo** | `git mv backend apps/api` e `git mv frontend apps/web` (preserva histórico por arquivo); ajustar `start.sh` (caminhos) e imports. PR só de movimentação, sem mudar lógica. | Sim, com caminhos ajustados | `git revert` |
| **M12 — Contêineres e CI** | `Dockerfile` da API e dos jobs; `ci.yml` (lint, testes, `tsc`, build, varredura de segredos, `pip-audit`/`npm audit`); deploy homolog. | Sim | desativar workflow |
| **M13 — Nuvem** | Provisionar conforme ADR-003 (homolog primeiro, com dados pseudonimizados). | n/a | IaC `destroy` em homolog |
| **M14 — Limpeza de histórico** | Somente com aprovação explícita e depois de M0/M1: `git filter-repo` em clone espelho. Ver ADR-005, fase B. | Sim | clone espelho de backup |

### Estimativa de esforço (ordem de grandeza)

M0–M4: 3–5 dias. M5–M9: 1,5–2 semanas. M10–M12: 1–1,5 semana. M13: 3–5 dias por ambiente. É compatível com a janela da Etapa 2 se começar agora, mas concorre com E2.1–E2.5. Recomendação: M0–M4 e M6 **antes** de qualquer demonstração com dados reais fora da máquina local.

## 4. Convenções

- Python 3.11 ou 3.12 no contêiner (3.10 local ainda funciona durante a transição), `ruff` + `mypy` leve, `pytest`.
- Nomes de domínio em português (`fila`, `priorizacao`, `redistribuicao`); termos técnicos podem ficar em inglês (`repository`, `router`).
- Um arquivo de rota não passa de ~300 linhas; um serviço não passa de ~400. Acima disso, dividir por caso de uso.
- Proibido `print` em código de aplicação; usar `logging` com o formatador de `core/logging.py`.
