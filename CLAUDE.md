# PREDMED — contexto do projeto

Plataforma SaaS de IA para **previsão, priorização e redistribuição de filas cirúrgicas do SUS** (Ceará).
Financiamento: **Edital FUNCAP/FINEP nº 08/2025 — Programa Centelha 3 CE**. Executora: JOSE MARCAL DOMINGOS JUNIOR LTDA.
Vigência do plano: **set/2026 → set/2027 (12 meses)**. Clientes-alvo: SESA-CE, secretarias municipais e hospitais públicos/privados.
É software para **governo e saúde**: dados de pacientes, LGPD, acessibilidade e auditoria são requisitos, não "nice to have".

## Três funcionalidades do plano
1. **Previsão de demanda** — cirurgias por especialidade, horizonte 30–90 dias (meta MAPE < 15%).
2. **Priorização clínica** — SWALIS + tempo de espera + judicialização + risco (oncologia/cardiologia).
3. **Redistribuição geográfica** — hospitais com capacidade ociosa na mesma CIR (meta: −40% no tempo de espera, ainda não comprovada).

## Stack atual (MVP 0.1)
- `backend/` — FastAPI + SQLAlchemy + SQLite (`predmed.db`), JWT multi-tenant (roles: SESA, hospital público, hospital particular). `main.py` concentra ~30 endpoints; `routers/` está vazio. Serviços em `backend/services/`. Scripts de ETL em `backend/_SCRIPTS/`.
- `frontend/` — Next.js 14 (App Router) + Tailwind + Chart.js/Recharts. Telas em `frontend/src/app/dashboard/*`.
- Dados: IntegraSUS (fila), DATASUS/SIH (`.dbc`), CNES. `predmed-original.db` (1,9 GB, SIH 2019–2024) não é versionado.
- Início local: `./start.sh`.

## Documentos de referência
- `docs/CHECKLIST_CONCLUSAO.md` — diagnóstico verificado e checklist de entregas.
- **Plano de trabalho atualizado (planilha xlsx)** — vale para **cronograma (19 atividades, meses 1–12, set/2026–set/2027) e orçamento**. Resumo no agente `gerente-projetos`.
- **Proposta original Centelha (PDF, 21 p.)** — vale para descrição do produto, metas (MAPE < 15%, SUS > 70, NPS > 70, 5 entrevistas, 15 demos, piloto 90 dias), riscos/LGPD, mercado e indicadores. **Onde o PDF conflita com a planilha (datas, etapas, rubricas, valores), a planilha prevalece.**

## Decisões do responsável (28/09/2026)
- Repositório GitHub é **privado**.
- **UX/UI será feito internamente** (sem consultoria contratada) — remanejamento da rubrica de R$ 6.288 em standby.
- **Nuvem: AWS, região São Paulo (sa-east-1)** — nota fiscal brasileira e aderência ao texto aprovado. Manter a aplicação **portável** (Docker, PostgreSQL padrão, armazenamento compatível com S3, config por env). Cloudflare descartado como principal. Registro completo em `docs/gestao/decisoes.md`.

## Regras para qualquer agente
- **Nunca** exibir, copiar ou commitar dados identificáveis de pacientes (nome/iniciais + nº de solicitação contam como dado pessoal).
- **Não apresentar números fixos/sintéticos como resultados medidos** (MAPE, % de redução). Sinalizar "simulado" / "não validado".
- Recomendações do sistema são **apoio à decisão**; não executam regulação, transferência nem emissão de AIH.
- Mudanças grandes: proponha o plano antes de editar. Mantenha o MVP rodando (`./start.sh`) após cada mudança.
- Idioma: português do Brasil em código de domínio, UI e documentação.
