# Checklist de segurança e LGPD — PREDMED

- **Data da verificação:** 28/09/2026, por inspeção do repositório local (commit `ef31833a`)
- **Decisões:** [ADR-004](adr/004-seguranca-lgpd-auditoria.md), [ADR-005](adr/005-retirar-artefatos-dados-git.md)
- **Aviso:** checklist técnico, não é parecer jurídico nem certificação. Itens jurídicos exigem validação do consultor previsto no plano.

## Legenda

| Símbolo | Significado |
|---|---|
| ✅ | Existe e atende |
| 🟡 | Parcial |
| ❌ | Não existe |
| ⏳ | Depende de infraestrutura ou contrato ainda não provisionado |

Prioridade: **P0** antes de qualquer dado real sair da máquina local ou de uma demonstração a terceiros; **P1** antes do piloto; **P2** durante o piloto.

## 1. Segredos e configuração

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 1.1 | `SECRET_KEY` sem valor padrão; app não sobe sem ela fora de dev | ❌ | `backend/auth.py:14` tem valor padrão no código | P0 |
| 1.2 | Segredos só em variáveis de ambiente ou gerenciador (Workers Secrets, AWS Secrets Manager) | 🟡 | `DATABASE_URL` e `SECRET_KEY` já lidos do ambiente; não há gerenciador | P1 |
| 1.3 | `.env.example` versionado, `.env` ignorado | 🟡 | `frontend/.env` ignorado; não há `.env.example`; backend não usa `.env` | P0 |
| 1.4 | Varredura de segredos no CI e em pre-commit (gitleaks) | ❌ | Sem CI | P1 |
| 1.5 | Rotação documentada de chaves (JWT, HMAC de pseudonimização, banco) | ❌ | — | P1 |
| 1.6 | CORS por configuração, lista explícita por ambiente | ❌ | `backend/main.py:99-105` fixo em localhost | P0 |
| 1.7 | Credenciais demo apenas em dev; seed não destrutivo | ❌ | `backend/seed.py:19-21` apaga usuários; `:57-72` senha única; `start.sh:64-67` imprime credenciais | P0 |

## 2. Autenticação, RBAC e isolamento de tenant

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 2.1 | Senhas com hash forte | ✅ | bcrypt, `auth.py:18` | — |
| 2.2 | RBAC por dependência | 🟡 | `require_sesa`, `require_gestor`, `require_particular` (`auth.py:61-78`); `require_gestor`/`require_particular` não são usados | P0 |
| 2.3 | Escopo de dados por tenant em **todas** as rotas com dado de paciente | ❌ | `/fila` não filtra `sms` nem `hospital_particular` (`main.py:196-270`); `/priorizacao` (`:464`) e `/judicializados` (`:504`) sem filtro; `/dashboard` ignora tenant (`ia_engine.py:326`) | P0 |
| 2.4 | Vínculo tenant ↔ estabelecimento por CNES (não por substring de nome) | ❌ | `main.py:213-214`, `:363`, `:540-541` | P0 |
| 2.5 | Papel `sms` limitado ao município gestor | ❌ | `Tenant.municipio_gestor` existe (`database.py:33`), mas não é usado | P0 |
| 2.6 | Testes automatizados de acesso permitido/negado por papel (T07) | ❌ | Sem testes | P0 |
| 2.7 | Token curto + refresh rotativo; revogação | ❌ | 24 h, sem revogação (`auth.py:16`) | P1 |
| 2.8 | Token em cookie `HttpOnly; Secure; SameSite` | ❌ | `localStorage` (`frontend/src/lib/auth.tsx:45-46`) | P1 |
| 2.9 | JWT sem dados pessoais além do `sub` | ❌ | nome, tenant e CIR no payload (`main.py:152-159`) | P1 |
| 2.10 | Rate limit e bloqueio no login | ❌ | — (planejado para a borda Cloudflare e para a API) | P1 |
| 2.11 | MFA para SESA e administradores | ❌ | — | P1 |
| 2.12 | Gestão de usuários (criar, desativar, trocar senha) com auditoria | ❌ | Só via seed | P1 |

## 3. Minimização, pseudonimização e anonimização

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 3.1 | Dado de paciente fora do git (inclusive histórico) | ❌ | 2 CSVs da fila e `predmed.db` rastreados; `.db` de 1,8 GB no histórico (ADR-005) | **P0** |
| 3.2 | Nome completo não armazenado | ✅ | Apenas iniciais (`data_import.py:616`) | — |
| 3.3 | Nº de solicitação: não armazenado em claro; hash HMAC para deduplicação | 🟡 | Não persistido no banco, mas presente nos CSVs versionados | P0 |
| 3.4 | Iniciais exibidas só para papéis e escopos autorizados | ❌ | Expostas a todos os papéis (`main.py:259`, `:485`, `:518`) | P0 |
| 3.5 | SIH analítico sem `nasc`/`cep`/`n_aih` em claro (faixa etária, município) | ❌ | Colunas no modelo `AIHRegistro` (`database.py:176-201`); comentário "não identificável" incorreto | P1 |
| 3.6 | Treino de ML só com agregados (anonimização nos modelos, prometida na proposta) | 🟡 | Séries mensais agregadas; treino ainda roda dentro da API com acesso ao banco inteiro | P1 |
| 3.7 | Supressão de células pequenas (n < 5) em recortes finos | ❌ | — | P2 |
| 3.8 | Dados sintéticos para dev, homolog e testes | ❌ | Fallback sintético existe só para previsão (`previsoes_ml.py:149-166`) | P1 |

## 4. Auditoria e modo apoio à decisão

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 4.1 | Tabela de auditoria somente inserção | ❌ | — | P1 |
| 4.2 | Registro de login (sucesso e falha) | ❌ | — | P1 |
| 4.3 | Registro de consultas a listas com dado de paciente (filtros e contagem) | ❌ | — | P1 |
| 4.4 | Registro de importações (quem, arquivo por hash, contagens, resultado) | ❌ | — | P1 |
| 4.5 | "Aprovar redistribuição" → "revisão de recomendação" com justificativa; texto explícito de que não executa transferência nem AIH | ❌ | `main.py:338`, `:348` gravam "aprovado" / "pacientes alocados" | P0 (texto) / P1 (fluxo) |
| 4.6 | Versão de modelo e regra registrada em cada previsão/priorização exibida | ❌ | Rótulo "Prophet" executa Holt-Winters; KPIs fixos (`ia_engine.py:355-357`) | P0 (rótulos) / P1 |
| 4.7 | Relatório periódico de disparidades por região (mitigação de viés prometida) | ❌ | — | P2 |

## 5. Criptografia e rede

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 5.1 | HTTPS/TLS 1.2+ com HSTS | ⏳ | Local em HTTP; borda Cloudflare ou ALB | P0 no deploy |
| 5.2 | TLS no banco (`sslmode=require`/`verify-full`) | ⏳ | SQLite local | P0 no deploy |
| 5.3 | Criptografia em repouso do banco e dos backups | ⏳ | SQLite sem cifra; `predmed-original.db` em disco comum (ativar FileVault) | P0 no deploy |
| 5.4 | Criptografia em repouso dos objetos | ⏳ | R2/S3 cifram por padrão | P1 |
| 5.5 | Uvicorn não exposto em `0.0.0.0` sem proxy em ambientes compartilhados | 🟡 | `start.sh:36` expõe na rede local | P1 |
| 5.6 | Headers de segurança (CSP, X-Frame-Options, Referrer-Policy) | ❌ | — | P1 |

## 6. Retenção e ciclo de vida

| # | Controle | Estado | Proposta | Prio. |
|---|---|---|---|---|
| 6.1 | Política de retenção documentada e aprovada pela controladora | ❌ | Tabela abaixo | P1 |
| 6.2 | Lifecycle automático no bucket (CSV bruto) | ⏳ | Regra de expiração S3/R2 | P1 |
| 6.3 | Descarte ao fim do contrato (exportação + exclusão + termo) | ❌ | Procedimento em `docs/operacao/` | P2 |

Retenção proposta (a validar com o jurídico e o cliente):

| Dado | Retenção |
|---|---|
| CSV bruto IntegraSUS | 30 dias após carga validada |
| Snapshots pseudonimizados da fila | 24 meses, para treino e série histórica. Reavaliar necessidade |
| Fila atual | Enquanto vigente o contrato |
| SIH público | Sem limite (dado público), com minimização aplicada |
| Auditoria | ≥ 5 anos |
| Logs de aplicação | 90 dias |
| Backups | PITR de 7 dias + diários por 30 dias |

## 7. Backups e continuidade

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 7.1 | Backup das bases locais atuais fora do repositório, com hash | ❌ | `predmed-original.db` (1,9 GB) é cópia única | **P0** |
| 7.2 | Importação não destrutiva (staging + troca atômica + snapshot) | ❌ | `data_import.py:643` apaga a fila antes de inserir; `:400`, `:489`, `:755` idem | P0 |
| 7.3 | PITR e snapshots automáticos do Postgres | ⏳ | ADR-002 | P1 |
| 7.4 | Restauração testada e registrada (trimestral) | ❌ | Critério transversal do checklist | P1 |
| 7.5 | Backup antes de cada migração em produção | ❌ | Pipeline (visão geral, seção 6) | P1 |
| 7.6 | Procedimento de rollback da aplicação | ❌ | Imagem anterior + `alembic downgrade` | P1 |

## 8. Logs e observabilidade

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 8.1 | Logs estruturados (JSON) com `request_id` | ❌ | `print` em `data_import.py` e `seed.py` | P1 |
| 8.2 | Nenhum dado de paciente em log | 🟡 | Logs atuais imprimem contagens e colunas (não linhas), mas não há filtro de proteção | P1 |
| 8.3 | Sem credenciais em log ou stdout | ❌ | `seed.py:120-123` | P0 |
| 8.4 | `/health` sem dados de negócio | ❌ | `main.py:825-833` expõe contagens sem autenticação | P1 |
| 8.5 | Swagger desabilitado ou protegido em produção | ❌ | Padrão FastAPI aberto | P1 |
| 8.6 | Alertas: falha de ETL, erro 5xx, login anômalo, custo | ❌ | — | P2 |

## 9. Código e dependências

| # | Controle | Estado | Evidência / lacuna | Prio. |
|---|---|---|---|---|
| 9.1 | Upload com nome gerado, limite de tamanho, validação de tipo e esquema | ❌ | `main.py:432`, `:456` (`/tmp/{file.filename}`) | P0 |
| 9.2 | Sem desserialização insegura | ❌ | `previsoes_ml.py:25-30` (`weights_only=False` global) | P1 |
| 9.3 | Dependências declaradas e fixadas; auditoria de vulnerabilidades | ❌ | `requirements.txt` incompleto, `prophet` sem versão; `python-jose` | P1 |
| 9.4 | Rotas GET sem efeito colateral | ❌ | `/zerarfilas` recalcula | P2 |
| 9.5 | Imagem de contêiner mínima, usuário não root, varredura (Trivy) | ⏳ | Sem Dockerfile | P1 |

## 10. Governança e documentos

| # | Item | Estado | Prio. |
|---|---|---|---|
| 10.1 | Contrato ou termo de tratamento com cada instituição (papéis controladora/operadora) | ⏳ | P1 |
| 10.2 | Registro de operações de tratamento (art. 37) | ❌ | P1 |
| 10.3 | RIPD do piloto | ❌ | P1 |
| 10.4 | Encarregado (DPO) ou canal de titulares | ❌ | P1 |
| 10.5 | Plano de resposta a incidentes | ❌ | P1 |
| 10.6 | Parecer sobre localização e transferência internacional (Cloudflare) | ❌ | P1, antes de dado real em Cloudflare |
| 10.7 | Termos de uso com o aviso "apoio à decisão; não substitui regulação nem julgamento clínico" | ❌ | P1 |

## Ordem sugerida (P0)

1. 7.1 Backup verificado das bases locais.
2. 3.1 / ADR-005 Fase A: parar de versionar dados e artefatos. Verificar o remoto no GitHub.
3. 1.1, 1.6, 1.7: segredo obrigatório, CORS configurável, seed não destrutivo.
4. 2.3–2.6 e 3.4: escopo de tenant e testes de acesso.
5. 7.2 e 9.1: importação não destrutiva e upload seguro.
6. 4.5 (texto) e 4.6 (rótulos): honestidade do modo apoio à decisão e das métricas.
