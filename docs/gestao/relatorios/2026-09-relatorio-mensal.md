# PREDMED — Relatório mensal de progresso — Período preparatório (setembro/2026)

Projeto: PREDMED – Plataforma de IA para Previsão e Otimização de Filas Médicas
Edital: FUNCAP/FINEP nº 08/2025 — Programa Centelha 3 CE
Executora: JOSE MARCAL DOMINGOS JUNIOR LTDA (marca MedOps; produto PREDMED — D09) | Responsável: proponente
Período: 01/09/2026 a 30/09/2026 | Data de emissão: 29/09/2026 (versão interna, sujeita a revisão do proponente)
Versão do código de referência: `main` em `cace50df` (merge da Sprint 2, 29/09/2026). Suíte de testes do backend: 87 testes aprovados em 29/09/2026 (execução local, `APP_ENV=dev pytest -q`)

> **Natureza deste relatório.** Setembro/2026 é um **período preparatório**. O Termo de Outorga com a FUNCAP foi assinado, mas **o recurso ainda não foi recebido** (informação do proponente em 29/09/2026). A execução formal pode começar no mês seguinte ao recebimento — o "Mês 1" pode passar a ser outubro/2026, **a confirmar no Termo**. Todo o trabalho abaixo foi feito com recursos próprios da empresa, **sem despesa lançada no projeto**. Este documento é interno: não substitui formulário ou sistema oficial da FUNCAP/FINEP.

## 1. Resumo do período

1. Termo assinado; recurso não recebido; nenhuma despesa do projeto; data de início da vigência (Mês 1) a confirmar no Termo.
2. Avanço técnico antecipado: segurança básica e métricas honestas (Sprint 1), coleta automática da fila IntegraSUS com data de solicitação, priorização explicável v0.1, dados DATASUS (SIH/CNES) automatizados, previsão de demanda validada fora da amostra e redistribuição com capacidade estimada a partir de dados reais (Sprint 2).
3. Resultado de previsão medido (não simulado): MAPE de 5,1% a 30 dias no total cirúrgico sem obstetrícia; meta < 15% atingida em 13 de 15 especialidades a 30 dias. O alvo é a **produção cirúrgica SIH**, não a fila.
4. Nada foi feito ainda nas frentes que dependem de pessoas e contratos: consultorias, entrevistas com gestores, hospital para o piloto, ambiente AWS.
5. Decisões pedidas ao proponente: fornecer o Termo (vigência, relatórios, remanejamento); enviar ofício à SESA sobre o campo `data` e termos de uso do portal; destino da rubrica UX/UI.

## 2. Atividades do plano no período

Como a execução formal não começou, as atividades estão classificadas pelo **status técnico real**, e não por atraso. "% dos indicadores" = indicadores de aceite (proposta) atendidos com evidência ÷ indicadores da atividade; "parcial" conta como não atendido.

| Ativ. | Planejado (M início–fim) | Situação em 29/09/2026 | % indicadores atendidos | Evidências (referência) |
|---|---|---|---|---|
| 1 Infra em nuvem | M1–M3 | **Parcial.** Nuvem decidida (AWS São Paulo, D07); segurança de configuração (B04); 87 testes automatizados locais; documentação de arquitetura em `docs/arquitetura/` (ADR-001 a 005). Sem conta AWS, sem ambientes dev/homolog/prod, sem CI/CD, sem Docker. ADR-003 ainda descreve Cloudflare como preferencial e precisa ser atualizada para D07 | 0 de 3 | `246f2f75`, `docs/arquitetura/visao-geral.md`, `docs/arquitetura/adr/`, `docs/gestao/decisoes.md` (D07) |
| 2 Consultorias | M1–M2 | **Pendente — aguarda recurso.** Nenhum contrato (comercial, jurídica, contábil). UX/UI interno (D02); remanejamento de R$ 6.288 em standby | 0 de 2 | `docs/gestao/minuta-remanejamento-ux.md` |
| 3 Dados para treino | M2–M3 | **Parcial avançado (antecipada).** SIH-RD CE 2019–2026-07 processado fora do Git; produção cirúrgica por especialidade (estado) e por CNES (24 competências, 2024-07 a 2026-06); capacidade CNES 2026-08; coleta IntegraSUS agendada **localmente** (2 coletas registradas no manifesto até 29/09). Falta dicionário de dados formal (B20) e coleta em nuvem | 1 de 3 (dataset ≥ 24 meses); coleta e documentação parciais | `60e7b17a`, `1b3a53b8`, `19ea9103`, `docs/dados/datasus-cnes-sih.md`, `docs/dados/coleta-integrasus.md`, `docs/dados/nota-tecnica-integrasus.md` |
| 4 Validação com gestores | M2–M3 | **Pendente.** 0 entrevistas; nenhum hospital identificado. Roteiro das 5 entrevistas elaborado em 29/09 | 0 de 3 | `docs/gestao/roteiro-entrevistas-gestores.md` |
| 5 Previsão de demanda | M4–M5 | **Parcial avançado (antecipada).** Avaliação fora da amostra com dados reais do SIH (teste 2025-07 a 2026-06), comparação com baselines ingênuos, relatório técnico v1, tela com MAPE medido. Não usa IntegraSUS (histórico da fila começou em 09/2026); mapeamento SIGTAP → especialidade é hipótese a validar com a SESA | 1 de 3 (relatório técnico); MAPE < 15% atendido em parte dos recortes; retreino com IntegraSUS pendente | `eec11507`, `e1b0563b`, `780f8d6f`, `docs/dados/previsao-demanda-v1.md` |
| 6 Priorização clínica | M4–M6 | **Parcial (antecipada).** Score v0.1 explicável (SWALIS real do IntegraSUS, espera, judicial, oncologia, cardiovascular) com testes; alerta de oncologia > 60 dias. **Proposta**: não usar no piloto antes da revisão clínica e jurídica; conformidade com a Lei 12.732/2012 não testada formalmente | 0 de 2 | `ac49c3d7`, `09bfbd54`, `10c5c5e8`, `docs/dados/regras-priorizacao-v0.1.md` |
| 7 Redistribuição geográfica | M4–M6 | **Parcial (antecipada).** Pressão por estabelecimento calculada com fila IntegraSUS + SIH por CNES; ociosidade **estimada** com CNES; sugestões restritas à mesma CIR; aprovação por SMS na própria CIR (D11). Mapa interativo não existe | 1 de 3 (índice de pressão por hospital); "dados reais" parcial (capacidade estimada); mapa pendente | `e1b0563b`, `277ace1d`, `docs/dados/redistribuicao-v1.md`, `docs/dados/vinculo-fila-cnes-revisao.md` |
| 8 Interface e dashboard | M4–M6 | **Parcial (antecipada).** 14 → 7/8 telas por perfil (D10); fundação visual com contraste AA e selos de natureza do dado; erros TypeScript corrigidos. Sem teste de usabilidade; exportação PDF/CSV ainda é `alert()` | 0 de 2 | `c6f8d29d`, `f7108d5d`, `05b969f1`, `docs/ux/arquitetura-telas.md` |
| 9 Integração IntegraSUS | M4–M6 | **Parcial (antecipada).** Coleta automática sem intervenção manual, porém em máquina local (launchd), não em produção. Usa endpoint JSON do painel público, **não documentado**; termos de uso não verificados | 0 de 2 | `1b3a53b8`, `19ea9103`, `10c5c5e8`, `docs/dados/coleta-integrasus.md` |
| 10–17, 19 | M7–M12 | Não iniciadas (no prazo) | — | — |
| 18 Prestação de contas | M11–M12 | Este relatório interno (preparatório) | — | este arquivo |

Transversal (não é atividade da planilha): **segurança e honestidade das métricas** — segredo JWT e senhas de seed por variável de ambiente (`246f2f75`), importação transacional e não destrutiva (`af8b7016`), remoção de métricas fixas e rotulagem "simulado/estimado/medido" (`b3d3ab3b`), isolamento por perfil/tenant com testes (`e5642cc6`, `4516f52f`), repositório privado publicado sem dados de pacientes (D01, D05).

## 3. Indicadores e metas do projeto

| Indicador | Meta (proposta) | Valor no período | Método / fonte | Situação |
|---|---|---|---|---|
| MAPE previsão — total cirúrgico sem obstetrícia | < 15% | **5,1% (30 d), 5,3% (60 d), 6,2% (90 d)** — medido (total com obstetrícia: 3,8% a 30 d) | Holt-Winters, origem móvel, teste 2025-07 a 2026-06, SIH-RD CE; baseline sazonal ingênuo 12,3%; "repetir o último mês" 6,8% a 30 d | Atingida no agregado; ganho sobre o baseline simples é pequeno a 30 d |
| MAPE por especialidade (todas as internações) | < 15% | 13 de 15 a 30 d; 9 de 15 a 90 d — medido | idem | Parcial. A 30 d, falha em oftalmologia (20,2%) e bucomaxilofacial (23,2%, baixo volume) |
| MAPE por especialidade (só eletivas) | < 15% | 9 de 15 a 30 d; 8 de 15 a 90 d — medido | idem, `CAR_INT = 01` | Parcial. A 30 d, falha em pequenas cirurgias, cardiovascular, neurologia, oftalmologia, plástica reparadora e bucomaxilofacial eletivas |
| Redução do tempo de espera | −40% | **Não medido.** Mutirão de 90 dias: 1.768 de 61.756 pedidos redistribuíveis (2,9%) — **simulado**, não é redução de espera | `docs/dados/redistribuicao-v1.md`; caminho em elaboração em `docs/dados/meta-40-caminho.md` | Não medido; exige piloto com datas de entrada e saída |
| Score SUS de usabilidade | > 70 | não medido | — | Pendente (atividade 8) |
| NPS usuários piloto | > 70 | não medido | — | Não iniciada |
| Entrevistas com gestores | 5 | 0 | — | Pendente; roteiro pronto |
| Hospital parceiro identificado | 1 | 0 | — | Pendente |
| Demonstrações | ≥ 15 | 0 | — | Não iniciada |
| Coleta IntegraSUS automatizada | configurada | 2 coletas registradas (agendamento local 7h/19h) | `manifesto.jsonl` (só agregados, fora do Git) | Parcial — migrar para AWS |

Números de fila (61.756 pedidos, 194 estabelecimentos, 15 especialidades) referem-se à coleta de 28/09/2026 e são agregados.

## 4. Execução financeira do período

**Nenhuma despesa do projeto.** O recurso não foi recebido; nenhum pagamento foi feito com recursos do Termo, nem lançado como contrapartida.

| Rubrica | Orçado (R$) | Executado no período | Acumulado | Saldo (R$) | Comprovantes |
|---|---|---|---|---|---|
| Consultoria comercial em saúde | 26.000,00 | 0,00 | 0,00 | 26.000,00 | — |
| Consultoria UX/UI | 6.288,00 | 0,00 | 0,00 | 6.288,00 | — (remanejamento em standby; não gastar) |
| Consultoria jurídica | 10.000,00 | 0,00 | 0,00 | 10.000,00 | — |
| Serviços contábeis | 4.200,00 | 0,00 | 0,00 | 4.200,00 | — |
| Infra em nuvem e APIs | 9.552,00 | 0,00 | 0,00 | 9.552,00 | — |
| Material de consumo (contrapartida) | 4.288,00 | 0,00 | 0,00 | 4.288,00 | — |
| Capital — computador de alto desempenho | 29.712,00 | 0,00 | 0,00 | 29.712,00 | — |
| **Total** | **90.040,00** | **0,00** | **0,00** | **90.040,00** | |
| À parte: bolsas CNPq | 50.000,00 | situação a confirmar | | | |

Fonte: declaração do proponente (29/09/2026). Conciliação contábil: não há contabilidade contratada para o projeto ainda.

A confirmar no Termo: se trabalho e gastos anteriores ao início da vigência podem ser apresentados como contrapartida ou execução (presunção conservadora: **não**; por isso este período é declarado como preparatório).

## 5. Mudanças, desvios e solicitações

| Tema | Situação | Comunicação à FUNCAP |
|---|---|---|
| Início da execução formal postergado até o recebimento do recurso (Mês 1 possivelmente out/2026) | A confirmar no Termo | Avaliar se é preciso comunicar e se o cronograma se desloca inteiro |
| UX/UI interno, sem consultoria (D02) | Tomada; rubrica de R$ 6.288 sem execução | Minuta pronta (`minuta-remanejamento-ux.md`); envio em standby |
| Nuvem AWS São Paulo (D07) | Tomada; coincide com o texto aprovado (EC2/RDS/S3) | Não parece exigir comunicação; confirmar no Termo |
| Marca da empresa MedOps (D09) | Tomada | Conferir se a razão social mudou; se sim, comunicar |
| Modelos de previsão: Holt-Winters/SARIMA/baselines escolhidos pela validação; Prophet testado e não escolhido na maioria das séries | Documentado em `previsao-demanda-v1.md` | Relatar no relatório técnico da atividade 5 |
| Consolidação de telas por perfil (D10); SMS aprova redistribuição na própria CIR (D11); vínculos CNES provisórios (D12) | Tomadas | Não exigem comunicação |

Solicitações enviadas à FUNCAP no período: nenhuma.

## 6. Riscos (top 5, ver `docs/gestao/riscos.md`)

| ID | Risco | Mudança no período |
|---|---|---|
| R18 | Início formal postergado comprime M1–M3 ou desloca o cronograma | **Novo.** Termo assinado, recurso não recebido |
| R05 | Piloto sem hospital confirmado | Sem mudança (alto); roteiro de entrevistas pronto |
| R19 | Meta de −40% no tempo de espera sem caminho demonstrado | **Novo.** Simulação dá 2,9% da fila redistribuível em 90 dias com a regra "mesma CIR"; caminho em elaboração |
| R07 | Termo de Outorga não lido | Termo assinado, mas cláusulas ainda não extraídas |
| R10 | Coleta IntegraSUS depende de endpoint não documentado; termos de uso não verificados | Reformulado: a coleta funciona, mas precisa de respaldo institucional (ofício à SESA) |

Riscos reduzidos no período: R04 (métricas fixas — removidas), R08 (tempo de espera agora calculável pela data de solicitação), R13 (segredo JWT), R14 (nomenclatura dos modelos), R03 (Cloudflare × AWS — resolvido por D07).

## 7. Próximo período (outubro/2026 — possível Mês 1)

| Prioridade | Entrega | Responsável |
|---|---|---|
| P0 | Ler o Termo: vigência, data do Mês 1, relatórios, remanejamento, elegibilidade de despesas | PROP + GP |
| P0 | Ao receber o recurso: conta do projeto, contratação da contabilidade e da jurídica | PROP |
| P0 | Conta AWS no CNPJ (sa-east-1), ADR-003 atualizada para D07, CI no GitHub Actions, homologação | ARQ + ENG |
| P0 | Ofício à SESA: significado do campo `data`, termos de uso do portal, acesso ao painel restrito da fila | PROP (GP redige) |
| P1 | Entrevistas 1–3 com gestores, usando o roteiro | PROP |
| P1 | Revisão dos vínculos CNES provisórios (HIF e Hospital São Raimundo primeiro) | DS + PROP |
| P1 | Documento do caminho para a meta de −40% (`docs/dados/meta-40-caminho.md`) | DS |
| P1 | Dicionário de dados (B20); migração da coleta para a nuvem | DS + ENG |
| P2 | Exportação CSV/PDF real; mapa interativo | ENG + UX |

## 8. Declaração de dados

Este relatório não contém dados pessoais de pacientes. Métricas assistenciais são agregadas. Números de previsão são **medidos** em validação fora da amostra; números de redistribuição e mutirão são **estimados/simulados** e não comprovam redução de tempo de espera.
