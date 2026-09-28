# 🧠 PREDMED MVP — eKLICK Healthcare AI

**Plataforma de IA para Previsão, Priorização e Redistribuição de Filas Cirúrgicas do SUS**

> Programa Centelha 3 — FUNCAP/CE

---

## Arquitetura

```
predmed-mvp/
├── backend/            # FastAPI + SQLAlchemy + SQLite
│   ├── main.py         # Todos os endpoints da API
│   ├── database.py     # Models: Tenant, Usuario, PacienteFila, etc.
│   ├── auth.py         # JWT multi-tenant
│   ├── seed.py         # Cria usuários e importa dados
│   ├── services/
│   │   ├── ia_engine.py    # Índice de pressão, redistribuição por CIR
│   │   └── data_import.py  # Importa IntegraSUS + DATASUS
│   └── data/           # ← coloque os CSVs aqui
├── frontend/           # Next.js 14 + Tailwind
│   └── src/app/
│       ├── login/          # Tela de login com usuários demo
│       └── dashboard/      # Todas as telas do PREDMED
│           ├── page.tsx        # Dashboard (KPIs, alertas)
│           ├── fila/           # Fila cirúrgica paginada
│           ├── priorizacao/    # Score IA + SWALIS
│           ├── redistribuicao/ # Mapa CIR + Aprovar (SESA)
│           ├── hospitais/      # Mapa de pressão hospitalar
│           ├── judicializados/ # Casos com ordem judicial
│           ├── zerarfilas/     # Simulador de mutirão
│           ├── relatorios/     # Relatório por role
│           └── configuracoes/  # Vagas SUS (particular) + imports (SESA)
└── start.sh            # Inicia tudo com um comando
```

---

## Requisitos

- Python 3.10+
- Node.js 18+
- npm ou yarn

---

## Inicialização rápida

```bash
chmod +x start.sh
./start.sh
```

Acesse:
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

---

## Usuários de Demo (somente desenvolvimento)

| Role | Email |
|------|-------|
| 🏛️ SESA (Gestor Estadual) | sesa@predmed.com |
| 🏙️ SMS Sobral | sms@predmed.com |
| 🏥 Hospital Público (HGF) | hgf@predmed.com |
| 🏢 Hospital Particular | particular@predmed.com |

Com `APP_ENV=dev` (padrão do `./start.sh`) e sem `SEED_SENHA_PADRAO`, os usuários **criados pelo seed**
recebem a senha de desenvolvimento `predmed123`. A tela de login mostra os atalhos de demo apenas em
`next dev` (ou com `NEXT_PUBLIC_MOSTRAR_DEMO=1`). Usuários que já existem no banco **mantêm a senha atual**:
o seed não altera nem recria usuários.

---

## Configuração e segurança (Sprint 1 — B04)

O backend lê variáveis do ambiente ou de `backend/.env` (modelo em `backend/.env.example`; o `.env` não é versionado).

| Variável | Em `APP_ENV=dev` | Fora de dev (qualquer outro valor ou ausente) |
|---|---|---|
| `APP_ENV` | `./start.sh` define `dev` se não houver valor | ausente = produção |
| `SECRET_KEY` | opcional; se faltar, gera um segredo local em `backend/.dev-secret-key` (ignorado pelo git) | **obrigatória** — a API não inicia sem ela |
| `CORS_ORIGINS` | padrão `http://localhost:3000,http://127.0.0.1:3000` | lista separada por vírgula; vazio = nenhuma origem |
| `SEED_SENHA_PADRAO` / `SEED_SENHA_<SESA\|SMS\|HGF\|PARTICULAR>` | padrão `predmed123` | obrigatória; sem ela o seed **não cria** o usuário |
| `DATABASE_URL` | padrão `sqlite:///./predmed.db` | idem |

O que mudou:
- O segredo JWT não tem mais valor fixo no código. Tokens emitidos com o segredo antigo deixam de valer.
- `seed.py` é **idempotente**: cria apenas tenants, usuários e vagas que faltam; não apaga nada e só importa CSVs se a fila/capacidade estiver vazia. Para carregar CSVs novos: `python seed.py --reimportar`.
- A importação IntegraSUS/DATASUS valida o arquivo antes e substitui os dados numa única transação; se o arquivo for inválido ou a carga falhar, os dados anteriores são mantidos (upload responde 400).
- `./start.sh` usa `backend/venv/bin/python` diretamente (o `activate` do venv apontava para um caminho antigo).
- **Rotação**: as contas já existentes em `predmed.db` continuam com a senha antiga. Para trocá-las sem apagar nada: `cd backend && SEED_SENHA_PADRAO='<nova>' APP_ENV=dev venv/bin/python seed.py --redefinir-senhas` (só aceita senha vinda de variável; nunca usa o padrão de dev).

Gerar um segredo: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

---

## Colocando seus dados reais

### IntegraSUS (fila de espera)
```bash
cp consulta-fila-espera_2026-02-22_13-14-37.csv backend/data/
```

### DATASUS (capacidade hospitalar)
```bash
cp tabnet_internacoes_ceara_datasus.csv backend/data/
```

Após adicionar os CSVs, rode (a fila só é substituída se o novo arquivo for válido):
```bash
cd backend && APP_ENV=dev venv/bin/python seed.py --reimportar
```

Ou faça upload via interface web em **Configurações → Importação de Dados** (usuário SESA).

---

## Multi-tenant — Quem vê o quê

| Tela | SESA | Hosp. Público | Hosp. Particular |
|------|:----:|:-------------:|:----------------:|
| Dashboard (geral) | ✅ Ceará todo | ✅ Ceará todo | ✅ Ceará todo |
| Fila Cirúrgica | ✅ tudo | ✅ só o seu hosp. | ✅ tudo |
| Priorização | ✅ | ✅ | ✅ |
| **Redistribuição** | ✅ + botão Aprovar | 👁️ leitura | 👁️ leitura |
| Hospitais | ✅ todos | ✅ sua CIR | ✅ públicos da CIR |
| Judicializados | ✅ | ✅ | ✅ |
| Prog. Zerar Filas | ✅ | ✅ | ✅ |
| **Configurações → Vagas SUS** | ❌ | ❌ | ✅ só ele |
| **Configurações → Importar CSV** | ✅ | ❌ | ❌ |
| Relatórios | ✅ Ceará | ✅ seu hosp. | ✅ seu hosp. |

---

## Endpoints principais da API

```
POST  /auth/login              → JWT com role e tenant
GET   /auth/me                 → Usuário logado
GET   /dashboard               → KPIs filtrados por role
GET   /fila?page=1&esp=...     → Fila paginada + filtros
GET   /hospitais               → Lista com índice de pressão
GET   /redistribuicao          → Sugestões por CIR
POST  /redistribuicao/aprovar  → [SESA only] Aprova transferência
GET   /redistribuicao/historico → Histórico de transferências
GET   /configuracoes/vagas     → [Particular] Status vagas/mês
PUT   /configuracoes/vagas     → [Particular] Atualiza vaga
POST  /admin/import/integrasus → [SESA] Upload CSV IntegraSUS
POST  /admin/import/datasus    → [SESA] Upload CSV DATASUS
GET   /priorizacao             → Top 20 por score IA + SWALIS
GET   /judicializados          → Casos com ordem judicial
GET   /relatorios/resumo       → Resumo por role
GET   /health                  → Status do sistema
```

---

## Roadmap pós-MVP

- [ ] Login com 2FA + refresh token
- [ ] Banco PostgreSQL (produção)
- [ ] Integração SISREG (automática)
- [ ] Integração FHIR R4 — Tasy/MV
- [ ] Cron job de atualização diária IntegraSUS
- [ ] Modelo Prophet real para previsão de demanda
- [ ] Deploy AWS/GCP com Docker
- [ ] Painel de billing SaaS (Stripe)

---

**eKLICK Healthcare AI** | contato@ekclick.com.br
# predmed
