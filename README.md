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

## Usuários de Demo

| Role | Email | Senha |
|------|-------|-------|
| 🏛️ SESA (Gestor Estadual) | sesa@predmed.com | predmed123 |
| 🏥 Hospital Público (HGF) | hgf@predmed.com | predmed123 |
| 🏢 Hospital Particular | particular@predmed.com | predmed123 |

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

Após adicionar os CSVs, rode novamente:
```bash
cd backend && source venv/bin/activate && python seed.py
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
