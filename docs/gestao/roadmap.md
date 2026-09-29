# PREDMED — Roadmap do plano de trabalho Centelha 3 CE

Versão: 28/09/2026 (Mês 1), rev. 1 — repositório limpo publicado (B01–B03 concluídos; ver `decisoes.md`, D05). Responsável pelo documento: gerente de projetos (agente). Revisão obrigatória: proponente.

## 1. Fontes e regra de precedência

| Fonte | Vale para |
|---|---|
| Plano de trabalho atualizado (planilha xlsx, resumida em `.claude/agents/gerente-projetos.md` e `CLAUDE.md`) | **Cronograma** (19 atividades, meses 1–12) e **orçamento** |
| Proposta original (`docs/referencia/proposta-centelha-pdf.txt`, 21 p.) | Metas, **indicadores de aceite**, descrição das atividades e riscos |
| Inspeção do repositório em 28/09/2026 | Status técnico real |
| Registro de decisões (`docs/gestao/decisoes.md`) | Decisões do proponente e pendências CK-R01–CK-R06 |
| Termo de Outorga | **Ainda não lido.** Pode alterar datas de vigência, regras de relatório e remanejamento |

Onde PDF e planilha divergem (datas, etapas, rubricas, valores), a planilha prevalece. Os indicadores do PDF foram mantidos como critério de aceite, exceto quando a própria planilha ou uma decisão do responsável os tornou inaplicáveis (sinalizado com ⚠).

### Convenção de meses

Mês 1 = setembro/2026. Tabela de referência usada neste documento (mês civil aproximado):

| M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| set/26 | out/26 | nov/26 | dez/26 | jan/27 | fev/27 | mar/27 | abr/27 | mai/27 | jun/27 | jul/27 | ago–set/27 |

⚠ **A confirmar:** "M1 = set/2026" e "M12 = set/2027" abrangem 13 meses civis se contados por mês inteiro. Isso só fecha se a vigência começar no meio de setembro (ex.: 15/09/2026 → 14/09/2027). A data exata de início deve ser extraída do Termo de Outorga; até lá, prazos de fim de atividade são aproximados.

### Legenda de status

- **Feito:** critério de aceite cumprido e evidência verificável registrada.
- **Parcial:** existe implementação ou insumo, mas falta requisito ou evidência.
- **A confirmar:** pode existir fora do repositório (contratos, conta, entrevistas); pedir evidência ao responsável.
- **Pendente:** nada encontrado ou falha verificada.
- **Não iniciada (no prazo):** atividade que ainda não começou pelo cronograma.

Nenhuma atividade está marcada como "feito" nesta versão.

## 2. As 19 atividades

| # | Atividade | Início–fim | Indicadores de aceite (PDF) | Status em 28/09/2026 | Evidência / observação da inspeção | Depende de |
|---|---|---|---|---|---|---|
| 1 | Configuração da infraestrutura em nuvem | M1–M3 (set–nov/26) | Ambientes configurados (dev, homologação, produção separados); pipeline CI/CD funcional; documentação de arquitetura entregue. ⚠ PDF diz "AWS EC2/RDS/S3"; decisão atual: portável Cloudflare Workers + AWS | **Pendente** (em execução pelo prazo) | Nenhum `.github/workflows`, Dockerfile, `wrangler.*` ou IaC no repositório. Banco é SQLite local (`backend/predmed.db`). Segredo JWT com valor padrão em `backend/auth.py:14`. Sem testes automatizados. Repositório GitHub privado publicado em 28/09/2026 com histórico limpo, sem dados de pacientes, dependências ou bancos (B01–B03 concluídos, D05) | Decisão de arquitetura portável (ADR; arranjo híbrido D06 pendente de aprovação) |
| 2 | Contratação das consultorias | M1–M2 (set–out/26) | Contratos de consultoria PJ assinados; cronogramas individuais estabelecidos. ⚠ PDF fala em "5 contratos"; pela planilha e decisões atuais são 3 (comercial saúde, jurídica, contábil); UX/UI será interna | **A confirmar** | Nada no repositório (esperado: contratos não devem ser versionados). Pedir referência ao local restrito | Tratamento da rubrica UX/UI junto à FUNCAP; conta do projeto |
| 3 | Coleta e estruturação dos dados para treino | M2–M3 (out–nov/26) | Dataset histórico DATASUS/SIH estruturado com ≥ 24 meses por especialidade, município e hospital; coleta automatizada IntegraSUS configurada; documentação dos dados entregue | **Parcial** (não iniciada pelo prazo, mas há insumos) | 72 arquivos SIH `.dbc` (2019–2024) na cópia local (não publicados no repositório limpo); scripts em `backend/_SCRIPTS/`. `predmed.db`: `aih_registro` com 0 registros; `serie_historica` com 24 competências (2024-03 a 2026-02), origem observada/sintética **a confirmar**. Fila IntegraSUS importada por upload manual (`/admin/import/integrasus`). Campo `data_insercao` vazio em 100% dos 63.495 registros da fila → tempo de espera não é calculável hoje. Sem dicionário de dados | Atividade 1 (ambiente); definição do alvo de previsão (checklist R03) |
| 4 | Validação do roadmap com gestores | M2–M3 (out–nov/26) | 5 entrevistas realizadas; 1 hospital parceiro identificado para piloto; wireframes aprovados. ⚠ PDF atribui wireframes à consultoria UX/UI; agora internos | **A confirmar** | Nada no repositório. O PDF declara maturidade "requisitos identificados", sem registros anexados | Roteiro de entrevista; lista de contatos (consultoria comercial pode apoiar) |
| 5 | Modelos de previsão de demanda | M4–M5 (dez/26–jan/27) | Modelos retreinados com dados reais DATASUS + IntegraSUS; MAPE < 15% validado; relatório técnico entregue | **Parcial** (não iniciada pelo prazo) | `previsoes_ml.py` usa Holt-Winters (`statsmodels`), com nomes/telas "Prophet"; `statsmodels` não está em `requirements.txt`, `prophet` está mas não é usado. Há fallback para série sintética. `ia_engine.py:355-357` fixa redução 40% e MAPE 11,2%. Endpoint de holdout (`/analytics/validacao-mape`) existe mas depende de `aih_registro`, hoje vazio. PDF cita Prophet, ARIMA e XGBoost | Atividade 3; decisão de modelos (R04) |
| 6 | Priorização clínica | M4–M6 (dez/26–fev/27) | Algoritmo atualizado com classificação SWALIS real; testes de conformidade com Lei 12.732 documentados | **Parcial** (não iniciada pelo prazo) | Ordenação apenas por categoria SWALIS (`main.py:227-234`); judicializado usado só como filtro/contagem; tempo de espera ausente (sem datas); sem regra oncologia/cardiologia; sem testes | Atividade 3 (datas de entrada na fila); revisão clínica e jurídica das regras |
| 7 | Redistribuição geográfica | M4–M6 (dez/26–fev/27) | Módulo funcional com dados reais; índice de pressão calculado por hospital; mapa interativo operacional | **Parcial** (não iniciada pelo prazo) | Lógica de destinos por região em `ia_engine.py` (~l. 618-706); tela `dashboard/redistribuicao`. Nenhuma biblioteca de mapa no frontend. Capacidade ociosa derivada de produção histórica, não confirmada | Atividade 3; vínculo CNES–CIR validado |
| 8 | Interface e dashboard de gestão | M4–M6 (dez/26–fev/27) | Interface aprovada em teste de usabilidade com 5 gestores reais; score SUS > 70 | **Parcial** (não iniciada pelo prazo) | 14 telas em `frontend/src/app/dashboard/`. `tsc --noEmit` falha com 5 erros (verificado hoje). Exportação PDF/CSV é só `alert()` (`relatorios/page.tsx:76-77`). Textos "tempo real" e "aprovado no Programa Centelha" sem base | Atividade 4 (wireframes); atividades 5–7 |
| 9 | Integração automatizada IntegraSUS | M4–M6 (dez/26–fev/27) | Integração em produção; atualização sem intervenção manual configurada | **Pendente** (não iniciada pelo prazo) | Apenas importação manual por upload. Disponibilidade e termos da API pública não verificados | Atividade 1 (produção); atividade 3 (mapeamento da fonte) |
| 10 | Piloto em hospital público | M7–M9 (mar–mai/27) | Sistema em produção no hospital piloto; relatórios quinzenais de KPIs; redução mensurável do tempo de espera registrada | Não iniciada (no prazo) — **risco alto** | Nenhum hospital parceiro confirmado | Atividades 1, 4, 5–9; termo de cooperação (jurídica); linha de base de espera |
| 11 | Prospecção comercial | M7–M9 (mar–mai/27) | ≥ 15 demonstrações; 3 propostas comerciais enviadas; 1 processo de contratação pública mapeado | Não iniciada (no prazo) | — | Atividade 2 (consultoria comercial); versão demonstrável |
| 12 | Ajustes pós-piloto | M7–M9 (mar–mai/27) | Lista de melhorias implementadas documentada; nova versão publicada; acurácia atualizada com dados do piloto | Não iniciada (no prazo) | — | Atividade 10 |
| 13 | Registro no INPI | M7–M8 (mar–abr/27) | Pedido de registro de software protocolado; número de protocolo obtido | Não iniciada (no prazo) | Repositório privado é pré-condição razoável; titularidade do código de consultorias deve constar nos contratos | Atividade 2 (jurídica); atividades 6–7 estáveis |
| 14 | Cases, materiais comerciais e site | M8–M9 (abr–mai/27) | 1 case com dados reais do piloto; kit comercial completo; minuta de contrato SaaS aprovada | Não iniciada (no prazo) | — | Atividade 10 (dados reais); jurídica |
| 15 | Contratação formal | M10–M11 (jun–jul/27) | ≥ 1 proposta formal aceita; ≥ 1 processo de contratação pública iniciado | Não iniciada (no prazo) | — | Atividades 11, 14 |
| 16 | Expansão Nordeste | M10–M12 (jun–set/27) | ≥ 3 estados nordestinos prospectados; 5 propostas enviadas fora do Ceará | Não iniciada (no prazo) | PDF menciona HIMSS/Hospitalar; não há rubrica de viagens/eventos na planilha | Atividades 11, 14 |
| 17 | Suporte e Customer Success | M10–M11 (jun–jul/27) | Sistema de suporte operacional; documentação de usuário publicada; SLA definido | Não iniciada (no prazo) | — | Atividade 12 |
| 18 | Prestação de contas e relatório final | M11–M12 (jul–set/27) | Relatório final entregue dentro do prazo; prestação de contas financeira completa | Não iniciada (no prazo); relatórios mensais **devidos desde M1** | Ver `prestacao-contas.md` | Contabilidade (atividade 2); evidências de todas as atividades |
| 19 | Planejamento da próxima fase | M11–M12 (jul–set/27) | Plano de expansão nacional; ≥ 2 editais mapeados; pitch deck atualizado com resultados reais | Não iniciada (no prazo) | — | Atividades 10, 15 |

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

Pontos de atenção:
- M4–M6 concentra cinco atividades técnicas simultâneas com equipe de uma pessoa mais agentes. O MVP precisa estar apto ao piloto no fim de M6 (fev/27).
- O piloto dura 90 dias pelo PDF (M7–M9) e começa em M7; a coleta da linha de base de espera precisa acontecer antes (M5–M6).
- Atividades 1 e 2 já estão em curso pelo cronograma (Mês 1) sem evidência no repositório.

## 5. Onde `docs/CHECKLIST_CONCLUSAO.md` ficou desatualizado

O checklist (15/09/2026) usa as datas e a estrutura do PDF. Não foi editado; pontos a considerar na leitura:

| Seção do checklist | Divergência com o plano vigente |
|---|---|
| Seção 3 (Etapa 1): datas 19/06–31/08/2026 e nota "os prazos já transcorreram" | Pela planilha, infra é M1–M3 e dados/validação M2–M3 (set–nov/26). Não há atraso nessas atividades |
| E1.1 Constituição da empresa | Não é atividade da planilha. Continua necessária como pré-condição (a confirmar) |
| E1.2 "AWS EC2/RDS PostgreSQL/S3" | Decisão de 28/09: portável Cloudflare Workers + AWS. Ver risco R03 |
| E1.3 e seção 7 "cinco contratos / seis frentes (ML, comercial público, comercial privado, UX/UI, integração, jurídico)" | Planilha: comercial saúde (26.000), UX/UI (6.288), jurídica (10.000), contábil (4.200), infra/APIs (9.552). Consultorias de ML e de integração saíram; UX/UI não será contratada |
| E1.5 "wireframes aprovados" pela consultoria | Wireframes serão internos (agente designer-ux-ui + proponente) |
| Seção 4 (Etapa 2): prazos 31/10–30/11/2026 | Planilha: M4–M6 (dez/26–fev/27) |
| Seção 5 (Etapa 3): 01/12/2026–28/02/2027 | Planilha: piloto, prospecção e ajustes M7–M9 (mar–mai/27); INPI M7–M8; cases M8–M9 |
| Seção 6 (Etapa 4): até 31/05/2027 | Planilha: M10–M12 (jun–set/27); prestação de contas M11–M12 |
| Seção 7 "Orçamento": capital R$ 0,00 no PDF | Planilha: capital R$ 29.712 (1 computador de alto desempenho); infra passa de "material de consumo" para custeio |
| Diagnóstico e T01–T07 | Continuam válidos; confirmados nesta inspeção (5 erros TS, MAPE 11,2% e 40% fixos, `aih_registro` vazio) |

Recomendação: quando o proponente aprovar este roadmap, atualizar o checklist (tarefa do responsável) ou marcá-lo como "versão PDF — ver `docs/gestao/roadmap.md`".
