# PREDMED — Modelos de prestação de contas

Versão: 28/09/2026. Estes são **modelos internos de organização de evidências**. Não substituem formulários, sistemas ou regras oficiais da FUNCAP/FINEP.

## 0. O que depende do Termo de Outorga (ainda não lido)

A proposta (p. 5) afirma: relatórios mensais de progresso "serão produzidos e compartilhados com a FUNCAP conforme exigido pelo Termo de Outorga". A proposta (p. 20) também vincula os serviços contábeis à "prestação de contas à FUNCAP conforme exigido pelo Termo de Outorga". O Termo não foi lido; portanto, os itens abaixo estão **em aberto** e nada neste documento deve ser tratado como regra da FUNCAP:

| Tema | Pergunta a responder no Termo | Resposta | Cláusula |
|---|---|---|---|
| Vigência | Data exata de início e fim (define M1 e M12) | a confirmar | |
| Relatório de progresso | Periodicidade exigida, formato, canal/sistema de envio, prazo após o mês | a confirmar | |
| Relatórios parciais/final | Quantos, quando, conteúdo técnico e financeiro exigido | a confirmar | |
| Parcelas | Condições para liberação da 2ª parcela | a confirmar | |
| Remanejamento | Procedimento para alterar rubrica (caso UX/UI R$ 6.288), limites, prazo de resposta | a confirmar | |
| Conta do projeto | Exigência de conta exclusiva, aplicação financeira, rendimentos | a confirmar | |
| Comprovantes | Tipos aceitos, identificação do projeto nos documentos, guarda | a confirmar | |
| Contrapartida | Como comprovar os R$ 4.288 da empresa | a confirmar | |
| Bens de capital | Patrimônio, identificação e destinação do computador | a confirmar | |
| Mudanças de escopo | Se a troca AWS → Cloudflare e a ausência de consultoria UX/UI exigem anuência | a confirmar | |
| Bolsas CNPq | Obrigações e relatórios próprios dos bolsistas (instrumento separado?) | a confirmar | |

Até o Termo ser lido, a prática recomendada é produzir o relatório mensal internamente todo mês (o custo é baixo e ele alimenta relatórios parciais e o final).

## 1. Orçamento de referência (planilha)

| Rubrica | Item | Valor (R$) | Situação |
|---|---|---|---|
| Custeio — Serviços de terceiros PJ | Consultoria comercial em saúde | 26.000,00 | A contratar (atividade 2) |
| Custeio — Serviços de terceiros PJ | Consultoria UX/UI | 6.288,00 | **Não será contratada — aguardar remanejamento; não gastar** |
| Custeio — Serviços de terceiros PJ | Consultoria jurídica (SaaS, INPI, LGPD, termos de cooperação) | 10.000,00 | A contratar |
| Custeio — Serviços de terceiros PJ | Serviços contábeis | 4.200,00 | A contratar / a confirmar |
| Custeio — Serviços de terceiros PJ | Infraestrutura em nuvem e consumo de APIs | 9.552,00 | Sob demanda (Cloudflare/AWS) |
| **Subtotal custeio PJ** | | **56.040,00** | |
| Material de consumo (contrapartida) | Insumos técnicos | 4.288,00 | Empresa |
| Capital | 1 computador de alto desempenho | 29.712,00 | A adquirir |
| **Total** | FUNCAP/FINEP 85.752,00 + contrapartida 4.288,00 | **90.040,00** | |
| À parte | Bolsas CNPq | 50.000,00 | Fora do total financiado |

Parcelas: 1ª = FINEP 31.998,36 + FUNCAP 10.877,64 + empresa 2.144,00 = 45.020,00; 2ª igual. Data de liberação da 2ª: a confirmar no Termo.

## 2. Matriz entregas × evidências × rubrica

Preencher uma linha por indicador. Evidências com documentos sigilosos ou dados pessoais: registrar só a **referência** ao local de acesso restrito, nunca o conteúdo no Git.

| Ativ. | Mês | Indicador de aceite (PDF) | Evidência esperada | Rubrica associada | Valor executado (R$) | Nº comprovante | Status | Local da evidência |
|---|---|---|---|---|---|---|---|---|
| 1 | M1–M3 | Ambientes configurados; CI/CD funcional; arquitetura documentada | Inventário de ambientes; execução do pipeline; ADR e documento de arquitetura | Infra nuvem/APIs; capital (computador) | | | Pendente | |
| 2 | M1–M2 | Contratos de consultoria assinados; cronogramas individuais | Contratos (referência); matriz contrato → entrega → rubrica | Comercial; jurídica; contábil | | | A confirmar | |
| 3 | M2–M3 | Dataset SIH ≥ 24 meses; coleta IntegraSUS automatizada; documentação dos dados | Script + relatório de cobertura; logs de coleta; dicionário de dados | Infra nuvem/APIs | | | Parcial | |
| 4 | M2–M3 | 5 entrevistas; 1 hospital parceiro identificado; wireframes aprovados | Sínteses agregadas; referência ao contato; wireframes + registro de aprovação | UX/UI **(aguardando remanejamento)**; comercial (apoio a contatos, se previsto no contrato) | | | A confirmar | |
| 5 | M4–M5 | Modelos retreinados com dados reais; MAPE < 15% validado; relatório técnico | Relatório técnico reproduzível; versão do código | Infra nuvem/APIs; capital | | | Parcial | |
| 6 | M4–M6 | Algoritmo com SWALIS real; testes de conformidade com Lei 12.732 documentados | Especificação; testes; revisão clínica/jurídica | Jurídica (revisão normativa, se no escopo) | | | Parcial | |
| 7 | M4–M6 | Módulo com dados reais; índice de pressão por hospital; mapa interativo | Documento do índice; capturas; testes | Infra nuvem/APIs | | | Parcial | |
| 8 | M4–M6 | Usabilidade com 5 gestores; SUS > 70 | Relatório de usabilidade (método, respostas agregadas) | UX/UI **(aguardando remanejamento)** | | | Parcial | |
| 9 | M4–M6 | IntegraSUS automatizado em produção; atualização sem intervenção manual | Logs de execuções sucessivas; teste de falha | Infra nuvem/APIs | | | Pendente | |
| 10 | M7–M9 | Sistema em produção no hospital; relatórios quinzenais de KPIs; redução mensurável registrada | Termo de cooperação; relatórios quinzenais; linha de base e medição | Jurídica (termo); infra | | | Não iniciada | |
| 11 | M7–M9 | ≥ 15 demonstrações; 3 propostas; 1 processo público mapeado | Registro de demonstrações; propostas; mapeamento | Comercial | | | Não iniciada | |
| 12 | M7–M9 | Melhorias documentadas; nova versão; acurácia atualizada | Changelog; release; relatório de métricas | Infra | | | Não iniciada | |
| 13 | M7–M8 | Pedido INPI protocolado; nº de protocolo | Comprovante de protocolo | Jurídica (taxas: rubrica a confirmar) | | | Não iniciada | |
| 14 | M8–M9 | 1 case com dados reais; kit comercial; minuta SaaS aprovada | Case; kit; minuta | Comercial; jurídica | | | Não iniciada | |
| 15 | M10–M11 | ≥ 1 proposta aceita; ≥ 1 processo público iniciado | Aceite; referência ao processo | Comercial; jurídica | | | Não iniciada | |
| 16 | M10–M12 | ≥ 3 estados prospectados; 5 propostas fora do CE | Registros; propostas | Comercial | | | Não iniciada | |
| 17 | M10–M11 | Suporte operacional; documentação publicada; SLA | Sistema de tickets; manuais; SLA | Infra (licenças: a confirmar) | | | Não iniciada | |
| 18 | M11–M12 | Relatório final no prazo; prestação financeira completa | Relatório; protocolo de entrega | Contábil | | | Não iniciada | |
| 19 | M11–M12 | Plano de expansão; ≥ 2 editais; pitch atualizado | Plano; mapeamento; pitch | — | | | Não iniciada | |
| — | M1–M12 | Contrapartida executada | Comprovantes de insumos técnicos | Material de consumo (contrapartida) | | | | |

### Controle por rubrica

| Rubrica | Orçado (R$) | Executado acumulado (R$) | Saldo (R$) | Observação |
|---|---|---|---|---|
| Consultoria comercial em saúde | 26.000,00 | | | |
| Consultoria UX/UI | 6.288,00 | 0,00 | 6.288,00 | Remanejamento solicitado em __/__/____ ; resposta: ____ |
| Consultoria jurídica | 10.000,00 | | | |
| Contábil | 4.200,00 | | | |
| Infra nuvem e APIs | 9.552,00 | | | Registrar fatura por provedor (Cloudflare/AWS) |
| Material de consumo (contrapartida) | 4.288,00 | | | |
| Capital — computador | 29.712,00 | | | Fonte (FINEP/FUNCAP): a confirmar |
| **Total** | **90.040,00** | | | |

## 3. Modelo de relatório mensal de progresso

> Arquivo sugerido: `docs/gestao/relatorios/AAAA-MM.md` (sem dados pessoais, sem comprovantes anexados no Git).

```markdown
# PREDMED — Relatório mensal de progresso — Mês N (mês/ano)

Projeto: PREDMED – Plataforma de IA para Previsão e Otimização de Filas Médicas
Edital: FUNCAP/FINEP nº 08/2025 — Programa Centelha 3 CE
Executora: [razão social] | Responsável: [nome]
Período: __/__/____ a __/__/____ | Data de emissão: __/__/____
Versão do código de referência: [commit/tag]

## 1. Resumo do mês (até 5 linhas)
O que avançou, o que atrasou, decisão pedida (se houver).

## 2. Atividades do plano no período
| Ativ. | Planejado (M início–fim) | Situação | % dos indicadores atendidos | Evidências (referência) |
|---|---|---|---|---|

Status: feito / parcial / a confirmar / pendente / não iniciada (no prazo).
"% dos indicadores" = indicadores cumpridos ÷ indicadores da atividade; não usar contagem de telas.

## 3. Indicadores e metas do projeto
| Indicador | Meta (proposta) | Valor no mês | Método / fonte | Situação |
|---|---|---|---|---|
| MAPE previsão | < 15% | [calculado ou "não medido"] | holdout temporal, recorte | |
| Score SUS usabilidade | > 70 | | nº de respondentes | |
| NPS usuários piloto | > 70 | | | |
| Entrevistas com gestores | 5 | | | |
| Hospital parceiro identificado | 1 | | | |
| Demonstrações | ≥ 15 | | | |
| Municípios integrados via IntegraSUS | — | | | |
Regra: valores simulados ou não validados devem ser marcados como tal.

## 4. Execução financeira do mês
| Rubrica | Orçado | Executado no mês | Acumulado | Saldo | Comprovantes (nº/ref.) |
|---|---|---|---|---|---|
Fonte: relatório da contabilidade de [data].

## 5. Mudanças, desvios e solicitações
- Mudanças de escopo/fornecedor e justificativa (ex.: UX/UI interno; infra Cloudflare + AWS).
- Solicitações enviadas à FUNCAP e status (ex.: remanejamento).

## 6. Riscos
Top 5 da matriz (`riscos.md`) com mudança desde o mês anterior.

## 7. Próximo mês
Metas das duas sprints seguintes e entregas previstas.

## 8. Declaração de dados
Este relatório não contém dados pessoais de pacientes. Métricas assistenciais são agregadas.
```

## 4. Rotina sugerida

| Quando | O quê | Quem |
|---|---|---|
| Fim de cada sprint | Anexar evidências na matriz (seção 2); atualizar status em `roadmap.md` | GP + agente responsável |
| Até o 5º dia útil do mês seguinte (prazo interno, **não** regra da FUNCAP) | Relatório mensal (seção 3) + conciliação com a contabilidade | GP + PROP + contábil |
| Ao receber o Termo de Outorga | Preencher a tabela da seção 0 e ajustar prazos/formatos deste documento | GP |
| Antes de qualquer gasto fora do previsto | Verificar rubrica e autorização | PROP + contábil |
