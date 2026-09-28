# Diagnóstico de arquitetura — PREDMED MVP 0.1

- **Data:** 28/09/2026
- **Autor:** arquiteto de sistemas (agente), a pedido do responsável técnico
- **Escopo:** leitura do repositório local `predmed-mvp` (branch `main`, commit `ef31833a`). Nenhum código foi alterado.
- **Não verificado:** ambientes externos, repositório remoto no GitHub, contas de nuvem, contratos.
- **Regra aplicada:** nenhum dado de paciente foi copiado para este documento. Só nomes de colunas e contagens agregadas.

## Escala de severidade

| Nível | Significado |
|---|---|
| **S1 — Crítico** | Exposição de dado pessoal, falha de isolamento entre instituições ou perda de dados. Bloqueia piloto e homologação. |
| **S2 — Alto** | Impede ambiente reproduzível, deploy em nuvem ou cumprimento de compromisso da proposta (E1.2). |
| **S3 — Médio** | Dívida estrutural que encarece a evolução e os testes. |
| **S4 — Baixo** | Higiene e legibilidade. |

## Resumo executivo

| # | Achado | Sev. |
|---|---|---|
| D01 | Dados pessoais da fila IntegraSUS (iniciais + nº de solicitação) versionados no git e presentes no histórico | S1 |
| D02 | Isolamento multi-tenant incompleto: `/fila` (SMS/particular), `/priorizacao`, `/judicializados` e `/dashboard` não filtram por instituição | S1 |
| D03 | Segredo JWT com valor padrão no código e senha demo única recriada a cada `start.sh` | S1 |
| D04 | Importação IntegraSUS apaga a fila anterior sem snapshot; `seed.py` apaga usuários e tenants a cada inicialização | S1 |
| D05 | `torch.load` globalmente alterado para `weights_only=False` (desserialização insegura) | S2 |
| D06 | Upload grava em `/tmp/{file.filename}` sem sanitizar o nome (path traversal) e sem limite de tamanho | S2 |
| D07 | Sem trilha de auditoria das decisões; "aprovação" de redistribuição grava `status="aprovado"` sem revisão nem motivo | S2 |
| D08 | Repositório com ~35,9 mil arquivos versionados (venv x2, node_modules, .next, lightning_logs); `.git` com 941 MB e blob de 1,8 GB | S2 |
| D09 | `requirements.txt` não reflete o que o código importa (statsmodels, torch, neuralprophet, pysus ausentes; `prophet` sem versão) | S2 |
| D10 | SQLite sem migrações (`create_all`), sem Alembic, sem backup | S2 |
| D11 | Treino de ML na mesma thread/processo da API, cache em memória do processo | S2 |
| D12 | `main.py` monolítico: 31 endpoints, schemas, regras de negócio e SQL no mesmo arquivo; `routers/` vazio | S3 |
| D13 | Sem testes, sem Docker, sem CI/CD, sem separação dev/homolog/prod | S2 |
| D14 | Indicadores fixos apresentados como medidos (MAPE 11,2%, redução 40%, R$ 1.500/AIH) | S2 (reputacional/contratual) |
| D15 | ETL disperso (`_SCRIPTS/`), com import quebrado e sem agendamento | S3 |
| D16 | Frontend guarda JWT em `localStorage`; URL da API cai em `localhost` por padrão; 5 erros de TypeScript (checklist T01) | S3 |
| D17 | Arquivos mortos e experimentais (`database_original.py`, `teste.py`, código comentado, symlink para `~/Downloads`) | S4 |

---

## 1. Estrutura atual

```
predmed-mvp/
├── start.sh                 # sobe backend (venv + seed + uvicorn --reload) e frontend (next dev)
├── venv/                    # venv na raiz, versionado (10.999+ arquivos)
├── backend/
│   ├── main.py              # 837 linhas, 31 rotas @app.*
│   ├── auth.py              # JWT + RBAC por função
│   ├── database.py          # engine + 12 modelos + get_db/init_db
│   ├── database_original.py # morto
│   ├── seed.py              # recria tenants/usuários demo + auto_import + série histórica
│   ├── teste.py             # script de teste manual do Prophet
│   ├── routers/__init__.py  # vazio
│   ├── services/            # 3.625 linhas em 6 módulos
│   ├── _SCRIPTS/            # ETL CNES/DATASUS/IntegraSUS/SIH, mapeamento CIR
│   ├── data/                # CSVs IntegraSUS, CNES JSON, 72 .dbc SIH (218 MB)
│   ├── lightning_logs/      # ~290 versões de treino NeuralProphet
│   ├── prophet_models/      # symlink quebrado → ~/Downloads/...
│   ├── predmed.db           # 17 MB (versionado)
│   ├── predmed-original.db  # 1,9 GB (não versionado)
│   └── venv/                # segundo venv, versionado (10.886 arquivos)
└── frontend/                # Next.js 14 App Router, 20 arquivos "use client"
    ├── src/app/dashboard/*  # 14 telas, ~3.900 linhas
    ├── src/lib/api.ts, auth.tsx
    ├── node_modules/        # versionado (13.420 arquivos)
    └── .next/               # versionado (72 arquivos, caches de 10–16 MB)
```

Python 3.10.14 (pyenv) em ambos os venvs.

## 2. Backend — acoplamentos e `main.py`

- **Monólito de rotas** — `backend/main.py` tem 31 decoradores `@app.*`. Mistura schemas Pydantic (`main.py:122-138`), consultas SQLAlchemy inline (`main.py:207-270`, `main.py:469-500`), regra de negócio (`main.py:650-715`, plano "Zerar Filas") e orquestração de ML (`main.py:62-83`). O diretório `backend/routers/` só tem `__init__.py` vazio. **S3**
- **Imports duplicados e locais** — `get_previsoes_todas_especialidades_prophet` é importado duas vezes (`main.py:16` e `main.py:47`). `analytics_sih` é importado no topo (`main.py:49-54`) e de novo dentro de cada rota (`main.py:728`, `742`, `757`...). **S4**
- **Ciclo de vida misto** — `lifespan` definido e desativado (`main.py:85-97`), e ao mesmo tempo `@app.on_event("startup")` (`main.py:108-118`) chama `seed.py` via `subprocess` quando não há usuários. **S3**
- **Sessão de banco entre threads** — o upload IntegraSUS dispara `threading.Thread(target=_treinar_em_background, args=(db,))` (`main.py:440-445`) com a sessão da requisição, que o `get_db` fecha ao fim da resposta (`database.py:339-344`). Isso gera condição de corrida e erros intermitentes. **S2**
- **Regras de tenant espalhadas** — cada rota decide o filtro por papel com `if user.role == ...` e casa hospital pelo **primeiro token do nome do tenant** (`main.py:213-214`, `main.py:363`, `main.py:540-541`). Um nome como "Hospital X" casa com qualquer "HOSPITAL...". **S1**, ver seção 6.
- **Valores de negócio fixos** — `aih_estimada = qtd * 1500` (`main.py:347`, `376`, `688`), protocolo com `random.randint` (`main.py:329`), que pode colidir porque a coluna é `unique` (`database.py:118`). **S3**
- **Rota de leitura com efeito colateral** — `/zerarfilas` é `GET` e recalcula previsões (`main.py:650-660`). `/previsoes/recalcular` apaga `serie_historica` inteira antes de reconstruir (`main.py:584-586`). **S3**

### Serviços

| Módulo | Linhas | Observação |
|---|---|---|
| `services/data_import.py` | 849 | Importadores CNES/DATASUS/IntegraSUS e casamento de hospitais por similaridade (`difflib`). Usa `print` para log (`:393`, `:481`, `:604-610`, `:727`). Apaga tabelas antes de importar (`:400`, `:489`, `:643`, `:755`). |
| `services/analytics_sih.py` | 837 | SQL analítico sobre `aih_registro`, com ramificação por dialeto (`:89`). Holt-Winters para MAPE (`:574`, `:673`). |
| `services/ia_engine.py` | 782 | KPIs, pressão hospitalar e redistribuição. KPIs fixos `reducao_estimada_pct: 40` e `acuracia_mape: 11.2` (`:355`, `:357`). Import no fim do arquivo (`:783`). |
| `services/previsoes_ml.py` | 694 | O nome diz "Prophet", mas executa Holt-Winters (`:36-38`, `treinar_prophet` em `:410`). Fallback **sintético** quando falta histórico (`:149-152`, `:166`). Cache em dicionário do processo (`:88-113`). Patch global de `torch.load` (`:17-30`). |
| `services/previsoes.py` | 354 | Regressão linear e série histórica. Apaga `SerieHistorica` (`:104`, `:164`). Cenário "−40%" embutido (`:226`). |
| `services/cir_config.py` | 109 | Configuração estática de CIR e macrorregiões. Boa candidata a `domain/`. |

Os serviços recebem `Session` e fazem ORM direto. Não há camada de repositório nem interfaces, então não dá para testar a regra de negócio sem banco.

## 3. ETL e ML

- **Scripts soltos** — `backend/_SCRIPTS/etl_completo.py` importa `services.download_sih` (`:34`), que não existe. O arquivo está em `_SCRIPTS/SIH/download_sih.py`, então o ETL "completo" não roda como está. **S3**
- **Fonte SIH** — `download_sih.py:119` baixa via FTP público do DATASUS. Os 72 `.dbc` (2019–2024) foram copiados para `backend/data/sih/` e estão versionados.
- **IntegraSUS** — só por upload manual (`/admin/import/integrasus`) ou arquivo em `data/`. Não há coleta agendada, validação de esquema, snapshot histórico nem idempotência. `import_integrasus` apaga toda a fila antes de inserir (`data_import.py:643`). Se a importação falhar no meio, a base válida anterior se perde. **S1** (perda de dados)
- **Colunas recebidas** — `POSICAO_FILA; MUNICIPIO; UNIDADE; PROCEDIMENTO; ESPECIALIDADE; INIC_NOME_PACIENTE; JUDICIALIZADO; CLASSIF_SWALIS; NUN_SOLICITACAO`. O importador persiste `iniciais` (`data_import.py:616`) e o expõe na API (`main.py:259`, `485`, `518`). `NUN_SOLICITACAO` não é persistido, mas está no CSV versionado.
- **ML acoplado à API** — o treino roda em thread dentro do processo uvicorn (`main.py:62-83`, `440-445`). `lightning_logs/` e `.neuralprophet_ckpt/` são gravados dentro do código-fonte. O cache (`previsoes_ml.py:88`) some a cada reinício e não é compartilhado entre réplicas, o que inviabiliza escalar horizontalmente. **S2**
- **Honestidade de métricas** — ver checklist (T02, T03). O fallback sintético e os KPIs fixos alimentam as telas sem sinalização. **S2**

## 4. Banco de dados

- `DATABASE_URL` já é lida do ambiente com padrão SQLite (`database.py:14-19`). Isso ajuda a migração.
- `init_db()` = `Base.metadata.create_all` (`database.py:347-348`). Não há Alembic nem versionamento de esquema. Colunas adicionadas depois (`cnes`, `hospital_id`) só aparecem em bancos novos. **S2**
- `declarative_base` legado (`database.py:9`) e `datetime.utcnow` (deprecado no 3.12).
- Datas da fila gravadas como `String` (`database.py:70-71`), o que impede calcular espera em SQL de forma confiável (checklist E2.2).
- `AIHRegistro` guarda `nasc`, `cep`, `munic_res`, `n_aih`, `raca_cor` e CIDs (`database.py:176-214`). O comentário "Paciente (não identificável)" (`:197`) **não procede**: data de nascimento + CEP + município formam quase-identificadores. Hoje a tabela está vazia em `predmed.db`, mas `predmed-original.db` tem 3,18 milhões de registros. **S2**
- `tenant_id` só existe em `usuarios` e `config_vagas`. As tabelas de dados (`pacientes_fila`, `transferencias`, `hospitais`) não têm chave de tenant nem de escopo (CIR/município). **S1** (base do problema D02)
- Não há backup, restauração testada nem criptografia em repouso. `predmed-original.db` (1,9 GB) é cópia única local. **S1** (perda de dados)
- `analytics_sih.py:89` já trata dialeto `postgresql`. Esse é um ponto a validar na migração, junto com `ilike`, `extract` e `case`.

## 5. Autenticação e segurança

| Item | Evidência | Sev. |
|---|---|---|
| Segredo JWT padrão | `auth.py:14` `os.getenv("SECRET_KEY", "predmed-secret-...")`. Se a variável faltar em produção, qualquer pessoa que leia o repositório forja tokens. | S1 |
| Token de 24 h, sem revogação nem refresh | `auth.py:16`, `auth.py:30-34` | S2 |
| `python-jose` 3.3.0 | `requirements.txt:4`. Biblioteca com manutenção fraca e CVEs históricos. Avaliar `pyjwt`. | S3 |
| Senha demo única, contas recriadas em todo `start.sh` | `seed.py:19-21` (apaga), `seed.py:57-72` (senha fixa), `start.sh:33` e `:64-67` | S1 fora do ambiente local |
| Login sem rate limit nem bloqueio; mensagem genérica (ok) | `main.py:142-149` | S2 |
| JWT carrega nome, tenant e CIR | `main.py:152-159`. É dado pessoal do usuário em claro (base64) em `localStorage`. | S3 |
| Token em `localStorage` (exposto a XSS) | `frontend/src/lib/auth.tsx:45-46`, `lib/api.ts:13` | S3 |
| CORS fixo em localhost | `main.py:99-105`. Bloqueia deploy; precisa vir de configuração. | S2 |
| Upload inseguro | `main.py:432`, `main.py:456`: `f"/tmp/{file.filename}"` sem sanitização, sem limite de tamanho nem tipo, arquivo não é apagado | S2 |
| Desserialização insegura | `previsoes_ml.py:25-30` força `weights_only=False` em todo `torch.load` do processo | S2 |
| `/health` sem autenticação expõe contagem de pacientes e usuários | `main.py:825-833` | S3 |
| Swagger `/docs` aberto | padrão FastAPI | S3 em produção |
| Logs com `print`, sem estrutura nem correlação | `data_import.py` (vários), `seed.py:120-123` imprime credenciais | S3 |
| HTTPS / criptografia em repouso | inexistentes no local; dependem da infraestrutura | S2 |

## 6. Multi-tenant e RBAC

Papéis em uso: `sesa`, `sms`, `hospital_publico`, `hospital_particular` (`database.py:50`, `auth.py:61-78`).

| Rota | sesa | sms | hospital_publico | hospital_particular | Problema |
|---|---|---|---|---|---|
| `GET /fila` (`main.py:196-270`) | tudo | **tudo** | nome do hospital por `ilike` do 1º token | **tudo** | Particular e SMS veem iniciais de pacientes de todo o estado. As `stats` (`:237-249`) ignoram o filtro. |
| `GET /priorizacao` (`main.py:464-500`) | tudo | tudo | **tudo** | **tudo** | Nenhum filtro. |
| `GET /judicializados` (`main.py:504-525`) | tudo | tudo | **tudo** | **tudo** | Nenhum filtro. Casos judiciais são especialmente sensíveis. |
| `GET /dashboard` (`ia_engine.py:326`) | tudo | tudo | tudo | tudo | Recebe `role`/`tenant_id`, mas não os usa. |
| `GET /hospitais` (`main.py:274-293`) | tudo | tudo | CIR | CIR + Fortaleza | Filtro em Python após carregar tudo. |
| `POST /redistribuicao/aprovar` | sim | não | não | não | Correto no RBAC, mas sem auditoria (seção 7). |
| `/analytics/*` (`main.py:722-822`) | tudo | tudo | tudo | tudo | Dados SIH agregados. Decidir se o ranking de mortalidade por hospital (`:746`) deve ser visível a hospitais privados. |

O papel `sms` não tem escopo municipal em nenhuma rota, embora exista `Tenant.municipio_gestor` (`database.py:33`). **S1**

## 7. Auditoria e modo "somente leitura"

- A proposta promete "modo somente leitura / apoio à decisão". A API tem operações de escrita legítimas: config de vagas, "aprovar" redistribuição e importações. Não há tabela de auditoria (quem, quando, o quê, antes/depois, motivo, IP).
- `Transferencia.status = "aprovado"` e a mensagem "✅ N pacientes alocados para ..." (`main.py:338`, `:348`) sugerem uma **execução** de transferência, o que contraria a regra "não executa regulação" (CLAUDE.md, checklist R05). **S2**
- Não há registro de acesso a dados de pacientes (quem consultou a fila), o que seria útil para LGPD art. 37 e para resposta a incidente.

## 8. Higiene do repositório

| Item versionado | Arquivos | Observação |
|---|---|---|
| `frontend/node_modules/` | 13.420 | Inclui binário nativo de 110 MB (`next-swc.darwin-arm64.node`) |
| `venv/` (raiz) | ~11.000 | venv duplicado |
| `backend/venv/` | 10.886 | |
| `__pycache__` | 8.648 | |
| `backend/lightning_logs/` | 363 | |
| `frontend/.next/` | 72 | caches webpack de 10–16 MB |
| `backend/data/` | 77 | 2 CSVs IntegraSUS com **iniciais + nº de solicitação** (dado pessoal), 72 `.dbc` SIH, CNES JSON |
| `backend/predmed.db` | 1 | contém a fila importada (dado pessoal) |
| `backend/prophet_models/prophet_model.bin` | 1 | symlink para `~/Downloads` |

- `.git` = 941 MB (`size-pack` 867 MB). O histórico de `main` contém **dois blobs acima de 100 MB**: uma versão de `backend/predmed.db` com **1,8 GB** e o binário SWC de 110 MB. Também há `backend/_SCRIPTS/SIH/dados_sih.csv` (11,6 MB) no histórico. Existe ainda uma ref `refs/codex/turn-diffs/...` com blob > 100 MB.
- Não há ref remota local (`origin/main` ausente). O GitHub rejeita arquivos acima de 100 MB, então **é provável que o push de `main` completo nunca tenha sido aceito**, ou que o remoto contenha um histórico diferente. Esse ponto precisa ser **verificado no GitHub antes de qualquer limpeza** (ADR-005).
- O `.gitignore` já lista `venv`, `node_modules`, `.next`, `*.db`, mas os arquivos continuam rastreados porque foram adicionados antes. Ignorar não "desversiona". Faltam `*.csv` de dados, `lightning_logs/`, `.neuralprophet_ckpt/`, `.DS_Store`, `.env*`.
- `.DS_Store` versionados (raiz, `frontend/`, `frontend/src/...`).

## 9. Testes, build e deploy

- Nenhum teste automatizado (backend ou frontend). Não há `pytest`, `vitest` nem `playwright`.
- Nenhum `Dockerfile`, `docker-compose`, workflow `.github/` ou IaC.
- `start.sh` sobe `uvicorn --reload` com `--host 0.0.0.0` (exposto na rede local) e roda `seed.py` destrutivo (`start.sh:33`). O script é adequado apenas para desenvolvimento.
- `requirements.txt` não fixa `prophet` e omite pacotes importados: `statsmodels` (`previsoes_ml.py:38`, `analytics_sih.py:574`), `torch` (`previsoes_ml.py:17`), `python-dateutil` (transitivo), `pysus` (`_SCRIPTS/SIH`). O ambiente só funciona porque o venv foi versionado. **S2**
- Frontend: 5 erros de `tsc` (checklist T01). `NEXT_PUBLIC_API_URL` tem padrão `localhost:8000` em três lugares (`next.config.js`, `lib/api.ts:3`, `analytics/page.tsx:129`, `simulador/page.tsx:6`). Não há ESLint configurado.
- As 14 telas são `"use client"`. Não há SSR de dados. Isso facilita a hospedagem estática/edge (OpenNext) e reduz a carga no servidor Next.

## 10. Implicações para a infraestrutura

1. A API depende de **pandas, numpy, statsmodels e torch/neuralprophet** (este último pode sair). Esse stack **não roda em Python Workers** (Pyodide/WebAssembly, 128 MB por isolate). Precisa de **contêiner** (detalhes no ADR-003).
2. O treino de ML e o ETL SIH (GBs, FTP) precisam de **jobs em lote** com disco e memória próprios, fora da API.
3. Estado no processo (cache em memória, arquivos em `/tmp`, `lightning_logs`) impede rodar a API sem estado, requisito tanto para Cloudflare Containers (disco efêmero, hibernação) quanto para ECS/App Runner.
4. Não há camada de tenant no dado. Antes de ir para a nuvem é preciso resolver D02, D03 e D04.

## 11. Pontos positivos a preservar

- `DATABASE_URL` e `NEXT_PUBLIC_API_URL` já vêm do ambiente.
- Senhas com bcrypt (`auth.py:18`).
- RBAC por dependência FastAPI (`require_sesa`, `require_gestor`) é o mecanismo certo; falta estendê-lo a escopo de dados.
- A API exibe apenas iniciais, não o nome completo, e `NUN_SOLICITACAO` não é persistido. Continua sendo dado pessoal (CLAUDE.md), mas a exposição já é reduzida.
- Frontend 100% cliente, fácil de servir em CDN com conexão lenta.
- `cir_config.py` e a modelagem `Hospital`/`HospitalAlias` são uma boa base de domínio.
