# PREDMED — Roadmap do plano de trabalho Centelha 3 CE

Versão: 29/09/2026, rev. 2 — Termo assinado, recurso ainda não recebido (período preparatório); status atualizado após as Sprints 1 e 2. Rev. 1 (28/09): repositório limpo publicado (D05). Responsável pelo documento: gerente de projetos (agente). Revisão obrigatória: proponente.

## 1. Fontes e regra de precedência

| Fonte | Vale para |
|---|---|
| Plano de trabalho atualizado (planilha xlsx, resumida em `.claude/agents/gerente-projetos.md` e `CLAUDE.md`) | **Cronograma** (19 atividades, meses 1–12) e **orçamento** |
| Proposta original (`docs/referencia/proposta-centelha-pdf.txt`, 21 p.) | Metas, **indicadores de aceite**, descrição das atividades e riscos |
| Inspeção do repositório em 29/09/2026 (`main` em `cace50df`) e `docs/dados/`, `docs/ux/`, `docs/arquitetura/` | Status técnico real |
| Registro de decisões (`docs/gestao/decisoes.md`) | Decisões do proponente e pendências CK-R01–CK-R06 |
| Termo de Outorga | **Assinado (informação do proponente, 29/09/2026); cláusulas ainda não extraídas.** Define a data do Mês 1, regras de relatório e remanejamento |

Onde PDF e planilha divergem (datas, etapas, rubricas, valores), a planilha prevalece. Os indicadores do PDF foram mantidos como critério de aceite, exceto quando a própria planilha ou uma decisão do responsável os tornou inaplicáveis (sinalizado com ⚠).

### Convenção de meses

**Fato novo (29/09/2026):** o Termo com a FUNCAP foi assinado, mas o recurso **não foi recebido**. A execução formal só começa após o recebimento; setembro/2026 é **período preparatório** (sem despesa do projeto). A data do Mês 1 depende do Termo:

| Cenário | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A — plano original (M1 = set/26) | set/26 | out/26 | nov/26 | dez/26 | jan/27 | fev/27 | mar/27 | abr/27 | mai/27 | jun/27 | jul/27 | ago–set/27 |
| **B — provável (M1 = out/26), a confirmar** | out/26 | nov/26 | dez/26 | jan/27 | fev/27 | mar/27 | abr/27 | mai/27 | jun/27 | jul/27 | ago/27 | set/27 |

- O cenário B fecha exatamente 12 meses (out/2026–set/2027) e resolve a ambiguidade do cenário A (13 meses civis). Se a vigência for contada a partir do recebimento do recurso e o recebimento atrasar mais, o fim desliza junto (M12 = out/27 ou depois) — ver R18.
- Até o Termo ser lido, este documento usa os **números de mês** (M1–M12) como referência; as datas civis nas tabelas abaixo não foram fixadas.
- O avanço técnico de setembro/2026 é antecipação com recursos próprios; não conta como execução financeira do Termo.

### Legenda de status

- **Feito:** critério de aceite cumprido e evidência verificável registrada.
- **Parcial:** existe implementação ou insumo, mas falta requisito ou evidência.
- **A confirmar:** pode existir fora do repositório (contratos, conta, entrevistas); pedir evidência ao responsável.
- **Pendente:** nada encontrado ou falha verificada.
- **Não iniciada (no prazo):** atividade que ainda não começou pelo cronograma.

Nenhuma atividade está marcada como "feito" nesta versão. "Parcial avançado" = implementação com evidência verificável que atende ao menos um indicador de aceite, faltando os demais.

## 2. As 19 atividades

Status verificado em 29/09/2026 contra `git log main` (ponta `cace50df`), `docs/dados/`, `docs/ux/`, `docs/arquitetura/` e execução local dos testes do backend (87 aprovados). Como a execução formal ainda não começou (seção 1, convenção de meses), avanço em atividades de M4–M6 é **antecipação com recursos próprios**, não execução do Termo.

| # | Atividade | Início–fim | Indicadores de aceite (PDF) | Status em 29/09/2026 | Evidência / observação | Depende de |
|---|---|---|---|---|---|---|
| 1 | Configuração da infraestrutura em nuvem | M1–M3 | Ambientes configurados (dev, homologação, produção separados); pipeline CI/CD funcional; documentação de arquitetura entregue. Nuvem: AWS São Paulo (D07), coincide com o PDF | **Parcial** (0 de 3 indicadores) | Feito: B04 (`246f2f75`, segredo JWT e senhas por variável de ambiente), 87 testes automatizados locais, documentação em `docs/arquitetura/` (visão geral, segurança/LGPD, ADR-001 a 005). Falta: conta AWS, ambientes, CI (sem `.github/workflows`), Docker, PostgreSQL. **ADR-003 ainda diz "Cloudflare preferencial" (status Proposto)** — atualizar para D07 | Recurso recebido (conta AWS no CNPJ); ADR-003 revista |
| 2 | Contratação das consultorias | M1–M2 | Contratos PJ assinados (comercial, jurídica, contábil); cronogramas. UX/UI interna (D02) | **Pendente — aguarda recurso** | Nenhum contrato informado. Remanejamento UX em standby (`minuta-remanejamento-ux.md`) | Recebimento do recurso; conta do projeto; Termo lido |
| 3 | Coleta e estruturação dos dados para treino | M2–M3 | Dataset SIH ≥ 24 meses por especialidade, município e hospital; coleta IntegraSUS automatizada; documentação dos dados | **Parcial avançado** (1 de 3; antecipada) | SIH-RD CE 2019–2026-07 fora do Git; produção cirúrgica por especialidade (estado) e por CNES, 24 competências 2024-07 a 2026-06, soma por CNES = série estadual (`60e7b17a`, `e1b0563b`, `docs/dados/datasus-cnes-sih.md`). Coleta da fila com data de solicitação agendada **localmente** (launchd, 2 coletas no manifesto até 29/09; `1b3a53b8`, `19ea9103`). Documentação por fonte existe; **dicionário de dados formal (B20) pendente** | Migração da coleta para AWS; B20 |
| 4 | Validação do roadmap com gestores | M2–M3 | 5 entrevistas; 1 hospital parceiro identificado; wireframes aprovados (internos) | **Pendente** (0 de 3) | Roteiro pronto em 29/09 (`roteiro-entrevistas-gestores.md`, B15). Telas consolidadas (D10, `docs/ux/arquitetura-telas.md`) servem de base aos wireframes, sem aprovação de gestores | Lista de contatos (B16); consultoria comercial (após recurso) |
| 5 | Modelos de previsão de demanda | M4–M5 | Modelos retreinados com dados reais DATASUS + IntegraSUS; MAPE < 15% validado; relatório técnico | **Parcial avançado** (1 de 3; antecipada) | Avaliação fora da amostra (teste 2025-07 a 2026-06): **MAPE 5,1% a 30 d** no total sem obstetrícia; meta < 15% em **13 de 15** especialidades a 30 d (todas as internações) e 9 de 15 (eletivas). Relatório `docs/dados/previsao-demanda-v1.md` (`eec11507`, `e1b0563b`). Ressalvas: alvo é **produção SIH, não fila**; IntegraSUS fora do treino (histórico só desde 09/2026); mapa SIGTAP → especialidade é hipótese | Histórico de snapshots da fila; validação do mapeamento com a SESA |
| 6 | Priorização clínica | M4–M6 | Algoritmo com SWALIS real; testes de conformidade com Lei 12.732 documentados | **Parcial** (0 de 2; antecipada) | Score v0.1 explicável (SWALIS 40, espera 30, judicial 15, oncologia 10, cardiovascular 5) com testes (`ac49c3d7`, `10c5c5e8`, `docs/dados/regras-priorizacao-v0.1.md`). É **proposta**: sem revisão clínica/jurídica; Lei 12.732 só como alerta | Entrevistas (bloco de validação); revisão clínica e jurídica (B34) |
| 7 | Redistribuição geográfica | M4–M6 | Módulo com dados reais; índice de pressão por hospital; mapa interativo | **Parcial** (1 de 3; antecipada) | Pressão por CNES com fila + SIH; ociosidade **estimada** (CNES salas/leitos + produção demonstrada); sugestões só na mesma CIR; SMS aprova na própria CIR (D11, `277ace1d`); vínculos CNES provisórios sinalizados (D12). `docs/dados/redistribuicao-v1.md`. Sem mapa (B40). Meta −40%: não medida; caminho em elaboração (`docs/dados/meta-40-caminho.md`) | Calibração dos parâmetros com gestores; decisão sobre redistribuição fora da CIR; revisão de vínculos |
| 8 | Interface e dashboard de gestão | M4–M6 | Usabilidade com 5 gestores reais; SUS > 70 | **Parcial** (0 de 2; antecipada) | 14 → 7/8 telas por perfil (D10, `c6f8d29d`); fundação visual AA e selos de natureza do dado (`f7108d5d`); `tsc` sem erros (`05b969f1`); métricas fixas removidas (`b3d3ab3b`). Exportação PDF/CSV ainda `alert()` (B39) | Teste de usabilidade com gestores |
| 9 | Integração automatizada IntegraSUS | M4–M6 | Integração em produção; atualização sem intervenção manual | **Parcial** (0 de 2; antecipada) | Coleta automática sem intervenção, **em máquina local**; importador lê a coleta JSON; status da coleta na tela de Configurações (`10c5c5e8`). Usa endpoint JSON do painel público, **não documentado**; termos de uso não verificados (`nota-tecnica-integrasus.md`) | Atividade 1 (produção); ofício à SESA |
| 10 | Piloto em hospital público | M7–M9 | Sistema em produção no hospital; relatórios quinzenais; redução mensurável do tempo de espera | Não iniciada (no prazo) — **risco alto** | Nenhum hospital identificado. Linha de base de espera agora é calculável pela data de solicitação (R08 reduzido) | Atividades 1, 4, 5–9; termo de cooperação (jurídica) |
| 11 | Prospecção comercial | M7–M9 | ≥ 15 demonstrações; 3 propostas; 1 processo público mapeado | Não iniciada (no prazo) | Versão demonstrável existe localmente | Consultoria comercial; ambiente de homologação |
| 12 | Ajustes pós-piloto | M7–M9 | Melhorias documentadas; nova versão; acurácia atualizada | Não iniciada (no prazo) | — | Atividade 10 |
| 13 | Registro no INPI | M7–M8 | Pedido protocolado; nº de protocolo | Não iniciada (no prazo) | Repositório privado (D01); histórico limpo (D05) | Jurídica; titularidade do código |
| 14 | Cases, materiais comerciais e site | M8–M9 | 1 case real; kit comercial; minuta SaaS | Não iniciada (no prazo) | — | Atividade 10; jurídica |
| 15 | Contratação formal | M10–M11 | ≥ 1 proposta aceita; ≥ 1 processo público iniciado | Não iniciada (no prazo) | — | Atividades 11, 14 |
| 16 | Expansão Nordeste | M10–M12 | ≥ 3 estados prospectados; 5 propostas fora do CE | Não iniciada (no prazo) | Sem rubrica de viagens/eventos | Atividades 11, 14 |
| 17 | Suporte e Customer Success | M10–M11 | Suporte operacional; documentação publicada; SLA | Não iniciada (no prazo) | — | Atividade 12 |
| 18 | Prestação de contas e relatório final | M11–M12 | Relatório final no prazo; prestação financeira completa | Não iniciada (no prazo); relatório interno do período preparatório emitido | `relatorios/2026-09-relatorio-mensal.md` (zero despesa) | Contabilidade; Termo |
| 19 | Planejamento da próxima fase | M11–M12 | Plano de expansão; ≥ 2 editais; pitch com resultados reais | Não iniciada (no prazo) | — | Atividades 10, 15 |

Atividade do PDF sem correspondente na planilha: **"Constituição da empresa e estruturação jurídica"** (Etapa 1, nº 1). Status: **a confirmar** (CNPJ, conta exclusiva do projeto, contrato contábil). A conta exclusiva é necessária antes de qualquer pagamento.

## 3. Linha do tempo

```
Ativ.  M1  M2  M3  M4  M5  M6  M7  M8  M9  M10 M11 M12
 1     ███ ███ ███
 2     ███ ███
 3         ███ ███
 4         ███ ███
 5                 ███ ███
 6                 ███ ███ ███
 7                 ███ ███ ███
 8                 ███ ███ ███
 9                 ███ ███ ███
10                             ███ ███ ███
11                             ███ ███ ███
12                             ███ ███ ███
13                             ███ ███
14                                 ███ ███
15                                         ███ ███
16                                         ███ ███ ███
17                                         ███ ███
18                                             ███ ███
19                                             ███ ███
```

## 4. Caminho crítico

1 Infra (M1–3) → 3 Dados (M2–3) → 5/6/7 Modelos, priorização, redistribuição (M4–6) → 8/9 Interface e IntegraSUS (M4–6) → **10 Piloto (M7–9)** → 12 Ajustes → 14 Case → 15 Contratação → 18 Prestação de contas.

Paralelo, mas bloqueante para o piloto: 4 Validação com gestores (hospital parceiro identificado até M3) e o termo de cooperação técnica (consultoria jurídica, atividade 2).

Pontos de atenção (rev. 2):
- **Início formal postergado** (R18): M1 provavelmente em out/2026. Atividades 1 e 2 dependem do recurso (conta AWS, contratos); as de dados e modelos (3, 5, 6, 7, 9) já avançaram antecipadamente e deixam folga em M4–M6.
- O **caminho crítico real passou a ser não técnico**: atividade 4 (entrevistas, hospital parceiro) e o termo de cooperação (jurídica) bloqueiam o piloto (M7–M9). Começar as entrevistas no M1, sem esperar M2.
- A linha de base do tempo de espera agora é calculável (data de solicitação no IntegraSUS), mas o **significado oficial do campo** precisa de confirmação da SESA antes de servir de base para a meta do piloto.
- A meta de **−40% no tempo de espera** não tem caminho demonstrado: a simulação de mutirão com a regra "mesma CIR" redistribui 2,9% da fila em 90 dias (simulado). Caminho em elaboração pelo cientista de dados em `docs/dados/meta-40-caminho.md` (R19).
- Coleta IntegraSUS roda numa máquina local; coletas perdidas não se recuperam. Migrar para a AWS assim que houver conta.

## 5. Onde `docs/CHECKLIST_CONCLUSAO.md` ficou desatualizado

O checklist (15/09/2026) usa as datas e a estrutura do PDF. Não foi editado; pontos a considerar na leitura:

| Seção do checklist | Divergência com o plano vigente |
|---|---|
| Seção 3 (Etapa 1): datas 19/06–31/08/2026 e nota "os prazos já transcorreram" | Pela planilha, infra é M1–M3 e dados/validação M2–M3 (set–nov/26 no cenário A; out–dez/26 no cenário B). Não há atraso nessas atividades |
| E1.1 Constituição da empresa | Não é atividade da planilha. Continua necessária como pré-condição (a confirmar) |
| E1.2 "AWS EC2/RDS PostgreSQL/S3" | Decisão D07 (28/09): AWS São Paulo, aplicação portável — coincide com o PDF. R03 encerrado |
| E1.3 e seção 7 "cinco contratos / seis frentes (ML, comercial público, comercial privado, UX/UI, integração, jurídico)" | Planilha: comercial saúde (26.000), UX/UI (6.288), jurídica (10.000), contábil (4.200), infra/APIs (9.552). Consultorias de ML e de integração saíram; UX/UI não será contratada |
| E1.5 "wireframes aprovados" pela consultoria | Wireframes serão internos (agente designer-ux-ui + proponente) |
| Seção 4 (Etapa 2): prazos 31/10–30/11/2026 | Planilha: M4–M6 (dez/26–fev/27 no cenário A; jan–mar/27 no B) |
| Seção 5 (Etapa 3): 01/12/2026–28/02/2027 | Planilha: piloto, prospecção e ajustes M7–M9 (mar–mai/27); INPI M7–M8; cases M8–M9 |
| Seção 6 (Etapa 4): até 31/05/2027 | Planilha: M10–M12 (jun–set/27); prestação de contas M11–M12 |
| Seção 7 "Orçamento": capital R$ 0,00 no PDF | Planilha: capital R$ 29.712 (1 computador de alto desempenho); infra passa de "material de consumo" para custeio |
| Diagnóstico e T01–T07 | Confirmados em 28/09; **em 29/09 vários foram resolvidos** (5 erros TS corrigidos, MAPE 11,2% e 40% fixos removidos, série SIH carregada por agregados). Reler o checklist contra a seção 2 |

Recomendação: quando o proponente aprovar este roadmap, atualizar o checklist (tarefa do responsável) ou marcá-lo como "versão PDF — ver `docs/gestao/roadmap.md`".

## 6. Histórico

| Data | Alteração |
|---|---|
| 28/09/2026 | Criação (rev. 0) e rev. 1 após publicação do repositório limpo |
| 29/09/2026 | Rev. 2: Termo assinado, recurso não recebido (cenários de M1); status das atividades 1, 3, 5–9 atualizado com evidências das Sprints 1 e 2; pontos de atenção revistos |
