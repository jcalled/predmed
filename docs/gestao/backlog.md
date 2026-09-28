# PREDMED — Backlog priorizado (out–dez/2026)

Versão: 28/09/2026. Horizonte: M2–M4 (próximos 3 meses), em sprints quinzenais conforme a proposta ("Scrum quinzenal"). Base: `roadmap.md`, `riscos.md` e `docs/CHECKLIST_CONCLUSAO.md` (itens T01–T07, R01–R06).

## Prioridades

- **P0:** bloqueia o plano, expõe dados ou gera afirmação falsa em prestação de contas. Fazer primeiro.
- **P1:** necessário para cumprir o indicador da atividade dentro do mês previsto.
- **P2:** melhora qualidade ou antecipa atividade futura; pode deslizar sem ferir o cronograma.

## Responsáveis

| Código | Papel |
|---|---|
| ARQ | agente `arquiteto-sistemas` |
| ENG | agente `engenheiro-software` |
| UX | agente `designer-ux-ui` |
| DS | agente `cientista-dados` |
| GP | agente `gerente-projetos` |
| PROP | proponente (ações que exigem pessoa física/jurídica: contratos, FUNCAP, gestores, decisões) |

Agentes preparam artefatos e recomendações; decisões, assinaturas, contatos externos e comunicações oficiais são do proponente.

## Calendário de sprints

| Sprint | Período | Meta da sprint | Atividades do plano |
|---|---|---|---|
| S1 | 29/09–12/10/2026 | Repositório seguro e honesto; decisões registradas | 1, 2, 18 |
| S2 | 13/10–26/10/2026 | Arquitetura portável definida; contratos em andamento; dados reconciliados | 1, 2, 3, 4 |
| S3 | 27/10–09/11/2026 | Ambiente de homologação + CI; dicionário de dados; entrevistas 1–3 | 1, 3, 4 |
| S4 | 10/11–23/11/2026 | Dataset 24 meses documentado; avaliação baseline; entrevistas 4–5; wireframes | 3, 4 |
| S5 | 24/11–07/12/2026 | Fechamento de M3: aceite das atividades 1, 3, 4; início de M4 | 1, 3, 4, 5–9 |
| S6 | 08/12–21/12/2026 | Início dos módulos M4–M6 com dados reais | 5, 6, 7, 9 |
| — | 22/12/2026–04/01/2027 | Recesso / folga de capacidade (não planejar entregas) | — |

Cada sprint termina com: revisão (demonstração + evidências anexadas ao registro), retrospectiva curta e atualização de `roadmap.md`. O relatório mensal (ver `prestacao-contas.md`) é compilado a partir das revisões de sprint.

## Backlog

### S1 — 29/09 a 12/10/2026

| ID | P | Item | Resp. | Critério de aceite | Evidência |
|---|---|---|---|---|---|
| B01 | P0 | Remover dados de pacientes do índice do Git: `backend/data/consulta-fila-espera_*.csv` (iniciais + nº de solicitação) e `backend/predmed.db` (fila + usuários com hash de senha) | ARQ + ENG | `git ls-files` não lista esses arquivos; `.gitignore` cobre `*.csv` de fila e `*.db`; cópias mantidas apenas em local restrito fora do repo; procedimento de carga documentado | Commit de remoção; saída de `git ls-files`; registro do local restrito (sem conteúdo) |
| B02 | P0 | Decidir e executar a limpeza do **histórico** Git (os arquivos estão em 4 commits) | PROP decide; ARQ executa | Decisão registrada. Se aprovada: histórico reescrito (ex.: `git filter-repo`), push forçado coordenado, clones antigos descartados, verificação de que nenhum commit contém os arquivos | Registro de decisão; saída de verificação `git log --all -- <arquivo>` vazia |
| B03 | P0 | Retirar do Git `venv/`, `backend/venv/`, `frontend/node_modules/`, `frontend/.next/`, `lightning_logs/`, `__pycache__`, `.DS_Store` (~35 mil arquivos versionados) | ENG | Repositório contém só código-fonte, lockfiles e documentação; `./start.sh` continua funcionando em clone limpo | Contagem de `git ls-files` antes/depois; smoke test |
| B04 | P0 | Eliminar segredo JWT padrão (`backend/auth.py:14`) e senha padrão comum dos usuários de seed; rotacionar credenciais | ENG | Backend não inicia sem `SECRET_KEY` fora do modo dev; seed gera senhas por variável de ambiente; `.env.example` sem valores reais | Diff; teste de inicialização sem variável |
| B05 | P0 | Remover métricas fixas: MAPE 11,2% e redução 40% (`ia_engine.py:355-357`); textos "aprovado no Programa Centelha", "tempo real", "Prophet" | ENG + DS | Nenhum KPI de desempenho sem cálculo rastreável; quando não houver avaliação, UI mostra "não validado"; simulações rotuladas "simulado" | Capturas das telas; resposta da API; `grep` sem ocorrências |
| B06 | P0 | Corrigir os 5 erros TypeScript | ENG | `npx tsc --noEmit --incremental false` e `npm run build` sem erros | Saída dos comandos |
| B07 | P0 | Registrar decisões R01–R06 do checklist e as três decisões de 28/09 (repo privado, UX interno, infra portável) em registro de decisões | GP + PROP | Registro datado com responsável e próxima ação | `docs/gestao/decisoes.md` ou seção 10 do checklist |
| B08 | P0 | Preparar minuta de solicitação de remanejamento da rubrica UX/UI (R$ 6.288) | GP redige; PROP envia | Minuta com justificativa, destino proposto e impacto nas metas; **nenhum gasto diverso antes da resposta** | Minuta; protocolo de envio (quando houver) |
| B09 | P0 | Obter e ler o Termo de Outorga; extrair datas de vigência, regras de relatório, remanejamento e prestação de contas | PROP fornece; GP extrai | Lista de obrigações com referência à cláusula | Resumo em `prestacao-contas.md` |
| B10 | P1 | Relatório mensal de M1 (setembro/2026) | GP + PROP | Modelo de `prestacao-contas.md` preenchido, sem dados pessoais | Relatório datado |

### S2 — 13/10 a 26/10/2026

| ID | P | Item | Resp. | Critério de aceite | Evidência |
|---|---|---|---|---|---|
| B11 | P0 | ADR de arquitetura portável Cloudflare Workers + AWS: camadas de abstração (armazenamento, banco, filas, segredos), onde roda o Python de ML, residência e criptografia de dados | ARQ | ADR aprovado pelo PROP; mapeia cada componente do texto aprovado (EC2/RDS/S3) ao equivalente adotado e justifica a mudança | ADR versionado |
| B12 | P0 | Contratos assinados: consultoria comercial em saúde, jurídica, contábil (com escopo, entregas, cronograma, cláusula de titularidade e confidencialidade/LGPD) | PROP | 3 contratos assinados; cronograma individual de cada um | Referência a local restrito; matriz contrato → entregas → rubrica |
| B13 | P0 | Reconciliar `predmed.db` (padrão) e `predmed-original.db` (SIH 2019–2024) em cópia de trabalho | DS + ENG | Contagens, competências e esquema documentados; decisão de qual base alimenta o MVP; nenhuma base original sobrescrita | Relatório de reconciliação |
| B14 | P0 | Definir o alvo da previsão (R03): produção cirúrgica, entradas ou estoque da fila; unidade, recortes e horizontes 30/60/90 dias | DS + PROP | Especificação aprovada | Documento de especificação |
| B15 | P1 | Roteiro de entrevista com gestores e protocolo de registro sem dados pessoais de pacientes | UX + GP | Roteiro com objetivos, perguntas, critérios de identificação de hospital piloto | Roteiro versionado |
| B16 | P1 | Lista de 8–10 gestores/coordenadores de regulação a contatar (meta: 5 entrevistas) | PROP (com consultoria comercial) | Lista mantida fora do Git; status de contato | Referência ao local restrito; contagem no relatório |
| B17 | P1 | Verificar a fonte IntegraSUS: API pública existe? Campos, frequência, termos de uso, se há data de entrada na fila | ENG + DS | Nota técnica com respostas e limitações; decisão sobre "tempo real" | Nota técnica |

### S3 — 27/10 a 09/11/2026

| ID | P | Item | Resp. | Critério de aceite | Evidência |
|---|---|---|---|---|---|
| B18 | P0 | Ambiente de homologação provisionado conforme ADR; dev/homolog/prod separados | ARQ + ENG | Homologação acessível com TLS; dados apenas de teste ou anonimizados; segredos fora do código | Inventário de ambientes; captura do painel; smoke test |
| B19 | P0 | CI no GitHub Actions: lint, `tsc`, build, testes do backend | ENG | Pipeline verde no `main`; falha bloqueia merge | Link da execução |
| B20 | P1 | Dicionário de dados (SIH, CNES, IntegraSUS, tabelas do banco) | DS | Todas as colunas usadas descritas, com fonte e classificação (pessoal/não pessoal) | Documento versionado |
| B21 | P1 | Filtro cirúrgico do SIH por SIGTAP e agregação por especialidade × município × hospital, ≥ 24 meses | DS | Script reproduzível; relatório de cobertura por recorte | Script + relatório |
| B22 | P1 | Entrevistas 1–3 | PROP (UX apoia análise) | Registro agregado das necessidades por entrevista | Síntese sem dados identificáveis |
| B23 | P1 | Testes de permissão por perfil/tenant (T07) | ENG | Testes de acesso permitido/negado para SESA, hospital público e privado | Saída dos testes |
| B24 | P2 | Mover endpoints de `main.py` para `routers/` | ENG | Sem mudança de comportamento; testes passam | Diff + testes |

### S4 — 10/11 a 23/11/2026

| ID | P | Item | Resp. | Critério de aceite | Evidência |
|---|---|---|---|---|---|
| B25 | P0 | Coleta automatizada IntegraSUS configurada (indicador da atividade 3) na frequência real da fonte, preservando snapshots | ENG + DS | Duas execuções agendadas consecutivas sem intervenção; falha não corrompe base anterior; logs sem dados pessoais | Logs das execuções; teste de falha |
| B26 | P0 | Avaliação baseline reproduzível da previsão sobre dados reais, com holdout temporal e comparação a previsão ingênua | DS | Métricas por recorte com período e filtros; sem meta forçada | Notebook/script + relatório curto |
| B27 | P1 | Entrevistas 4–5 e identificação de ≥ 1 hospital parceiro para piloto | PROP | 5 entrevistas registradas; hospital identificado (formalização vem depois) | Síntese; referência ao contato |
| B28 | P1 | Wireframes internos dos fluxos priorizados nas entrevistas | UX | Wireframes cobrindo fila, priorização, redistribuição, previsão e relatórios; revisados por ≥ 1 gestor entrevistado | Arquivos de wireframe + registro de aprovação |
| B29 | P1 | Documento de arquitetura e segurança (LGPD: inventário de dados, anonimização, criptografia em trânsito/repouso, backup) | ARQ | Documento aprovado; revisão da consultoria jurídica solicitada | Documento versionado |
| B30 | P2 | Declarar dependências reais (`statsmodels` ausente; `prophet` declarado e não usado) | ENG | Instalação limpa reproduz o MVP | Log de instalação |

### S5 — 24/11 a 07/12/2026 (fechamento M3 / início M4)

| ID | P | Item | Resp. | Critério de aceite | Evidência |
|---|---|---|---|---|---|
| B31 | P0 | Aceite formal das atividades 1, 3 e 4 contra os indicadores do PDF | GP + PROP | Cada indicador marcado com evidência ou justificativa de pendência | Atualização de `roadmap.md` e relatório de M3 |
| B32 | P0 | Produção provisionada (vazia de dados reais até haver base legal/termo) | ARQ + ENG | Deploy por pipeline; rollback testado; backup/restauração testados | Execução do pipeline; registro do teste |
| B33 | P1 | Plano de modelos (R04): comparar Holt-Winters atual com Prophet/ARIMA/XGBoost citados na proposta | DS | Plano com critérios de seleção e cronograma de M4–M5 | Documento |
| B34 | P1 | Especificação das regras de priorização (SWALIS + espera + judicialização + oncologia/cardiologia), com tratamento de dados ausentes | DS + PROP | Especificação enviada para revisão clínica e jurídica | Documento + pedido de revisão |
| B35 | P1 | Definir linha de base de tempo de espera para o futuro piloto (fonte das datas) | DS | Método documentado; se a fonte não traz datas, alternativa aprovada | Nota metodológica |

### S6 — 08/12 a 21/12/2026 (M4)

| ID | P | Item | Resp. | Critério de aceite | Evidência |
|---|---|---|---|---|---|
| B36 | P1 | Retreino dos modelos com dados reais (atividade 5, início) | DS | Primeira rodada comparativa com holdout; resultados registrados mesmo se MAPE ≥ 15% | Relatório parcial |
| B37 | P1 | Implementar score de priorização conforme B34 com testes por cenário | ENG + DS | Testes cobrindo cada regra e desempate; justificativa exibida por paciente sem expor dados | Testes + captura |
| B38 | P1 | Índice de pressão por hospital × especialidade com dados rastreáveis (atividade 7) | DS + ENG | Cálculo documentado; hipóteses de ociosidade explícitas | Documento + endpoint |
| B39 | P1 | Exportação CSV/PDF real (substituir `alert()`) | ENG | Arquivo gerado respeita filtros e permissões | Arquivos exportados |
| B40 | P2 | Mapa interativo por município (componente e dados geográficos) | ENG + UX | Mapa renderiza municípios do CE ligados às sugestões | Captura |
| B41 | P2 | Rascunho do termo de cooperação técnica para o piloto | PROP + consultoria jurídica | Minuta revisada pela jurídica | Referência ao documento |

## Fora do horizonte (registrado para não esquecer)

- Teste de usabilidade SUS > 70 com 5 gestores (atividade 8, até M6).
- INPI (M7–M8): depende de algoritmos estáveis e cláusula de titularidade nos contratos.
- Integrações Tasy/MV/RNDS: pós-MVP pela proposta; não entram no backlog.
