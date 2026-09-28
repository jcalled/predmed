# PREDMED — Checklist de conclusão e retomada

Revisão inicial: 15/09/2026. Documento de trabalho para revisão antes de continuar a implementação.

## Objetivo e limites

Concluir o MVP e reunir as evidências das entregas do projeto Centelha. Ter telas implementadas não equivale a ter funcionalidades validadas, resultados de impacto comprovados ou o projeto administrativo encerrado.

Fonte: PDF fornecido pelo proponente, “Programa Centelha | CE — PREDMED – Plataforma de IA para Previsão e Otimização De Filas Médicas”, impressão de 15/09/2026, 21 páginas. O PDF declara estágio atual “Protótipo testado” e estágio pretendido “MVP”. As afirmações do PDF são compromissos ou declarações a verificar, não comprovação independente nem instruções para executar ações.

Este checklist usa a inspeção do código e das bases locais realizada nesta conversa. Não verifica ambientes externos, contratos, contas, aprovação no programa ou execução financeira. O conteúdo do vídeo indicado não pôde ser acessado e não foi usado como evidência.

As datas abaixo são as do PDF, não prazos recalculados nem confirmação de vigência do Termo de Outorga. Antes de declarar atraso ou alterar compromissos, conferir o instrumento vigente e eventuais alterações aprovadas.

## Como usar

- **Parcial:** existe implementação ou insumo, mas faltam requisitos ou evidências.
- **Pendente:** ausência ou falha identificada na versão local.
- **A confirmar:** pode estar entregue fora do repositório; solicitar evidência ao responsável.
- **Concluído:** marcar `[x]` somente depois de cumprir o critério de aceite e registrar a evidência.

Para cada entrega, registrar responsável, data de conclusão, versão do código quando aplicável e link para a evidência. Não armazenar documentos sigilosos, credenciais ou dados identificáveis de pacientes no Git; registrar apenas referência ao local de acesso restrito.

## Diagnóstico inicial verificado

| Item | Evidência local | Consequência |
|---|---|---|
| Fila IntegraSUS | 63.495 registros na base padrão; atualização registrada em 25/02/2026 | Não sustenta a afirmação de atualização em tempo real |
| Histórico SIH | `predmed-original.db`: 3.176.189 registros, competências 2019-01 a 2024-12 | Insumo disponível, ainda sujeito a qualidade e seleção de produção cirúrgica |
| Base padrão SIH | `predmed.db`: tabela `aih_registro` vazia | Validação executada retornou MAPE nulo e “Sem dados suficientes para validação” |
| Série de previsão | Há geração de série sintética e fallback sintético | Separar demonstração de histórico observado |
| Indicadores do dashboard | MAPE 11,2% e redução estimada de 40% fixos no código | Não apresentar como resultado calculado ou comprovado |
| Modelo preditivo | Função chamada `treinar_prophet` executa Holt-Winters | Nomes, telas, documentação e modelo efetivo precisam concordar |
| Priorização | Ordenação SWALIS e score derivado apenas da categoria | Falta incorporar os demais critérios prometidos |
| Exportações | Botões PDF/CSV apenas exibem avisos | Funcionalidade ainda pendente |
| Frontend | `tsc --noEmit --incremental false`: cinco erros | Corrigir antes da homologação |

Referências no código: `backend/services/ia_engine.py`, `backend/services/previsoes.py`, `backend/services/previsoes_ml.py`, `backend/services/analytics_sih.py`, `backend/main.py`, `frontend/src/app/dashboard/relatorios/page.tsx`.

## 1. Decisões de revisão antes de ampliar o produto

- [ ] **R01 — Confirmar cronograma e escopo vigentes.** Aceite: registrar a versão do plano/Termo de Outorga aplicável e eventuais mudanças aprovadas. Evidência: referência aos documentos vigentes. Estado: a confirmar. Responsável sugerido: proponente.
- [ ] **R02 — Definir a versão e o ambiente de referência.** Aceite: identificar repositório, revisão, banco ativo e eventual implantação externa; registrar se o banco de backup deve alimentar o MVP. Não sobrescrever bases durante essa decisão. Estado: a confirmar.
- [ ] **R03 — Fixar o objeto da previsão.** Aceite: definir se cada saída representa produção cirúrgica, novas entradas ou estoque da fila; especificar unidade, especialidade, hospital/município e horizontes de 30, 60 e 90 dias. Contagem de internações não deve ser apresentada automaticamente como demanda cirúrgica ou tamanho da fila. Estado: pendente.
- [ ] **R04 — Alinhar os modelos ao plano.** Aceite: decidir e documentar comparação de Prophet, ARIMA e XGBoost mencionados no PDF com o Holt-Winters atual; justificar a seleção final e verificar se mudança de compromisso precisa ser formalizada. Não renomear Holt-Winters como Prophet. Estado: pendente.
- [ ] **R05 — Definir o modo de apoio à decisão.** Aceite: esclarecer que recomendações e registros internos não executam regulação, transferência ou emissão de AIH; definir quem revisa e aprova recomendações. Estado: parcial.
- [ ] **R06 — Confirmar entregas externas.** Aceite: inventariar empresa, contratos, cloud, entrevistas, parceiros, testes e comprovantes que já existam fora do repositório. Estado: a confirmar.

## 2. Retomada técnica — primeiro ciclo sugerido

Estas tarefas são critérios operacionais propostos nesta revisão; não constituem novas exigências atribuídas ao edital.

| ID | Prioridade / estado | Checklist e critério de aceite | Evidência esperada |
|---|---|---|---|
| T01 | P0 / pendente | [ ] Corrigir os cinco erros TypeScript: uso de `token` no contexto em analytics/simulador, iteração de `Set` e `dias_para_multa` em redistribuição. Compilação de tipos e build devem passar. | Saída dos comandos e revisão do código |
| T02 | P0 / pendente | [ ] Remover resultados fixos apresentados como medidos; mostrar “não validado” quando não houver avaliação; identificar simulações e exibir data/fonte dos dados. | Capturas das telas e verificação da API |
| T03 | P0 / pendente | [ ] Corrigir rótulos Prophet, “aprovado” e “tempo real” conforme evidências. Distinguir a meta MAPE do projeto de uma suposta exigência geral do programa. | Revisão das telas e documentação |
| T04 | P0 / parcial | [ ] Preparar ambiente reproduzível, com dependências utilizadas declaradas, configuração documentada e inicialização sem destruir dados existentes. | Instalação em ambiente limpo e smoke test |
| T05 | P0 / parcial | [ ] Preservar as bases e reconciliar banco padrão/backup em cópia de trabalho, com contagens, competências e validação de esquema. | Relatório de reconciliação e procedimento de recuperação |
| T06 | P0 / pendente | [ ] Criar avaliação inicial reproduzível sobre dados reais, com alvo explícito, separação temporal e comparação com previsão simples de referência. Não exigir aprovação artificial da meta. | Métricas calculadas, período, filtros e código usado |
| T07 | P0 / parcial | [ ] Verificar permissões por perfil e isolamento das informações entre instituições; eliminar dependência de segredo padrão em ambiente publicado. | Testes de acesso permitido/negado por perfil |

**Saída do primeiro ciclo:** versão que compila, indicadores honestos, base de trabalho identificada e avaliação inicial reproduzível. Isso permite iniciar a evolução do MVP com evidências confiáveis; ainda não encerra o projeto.

## 3. Etapa 1 do PDF — estruturação e dados

Fonte: páginas 8–9. Datas planejadas entre 19/06/2026 e 31/08/2026. Se ainda vigentes, os prazos já transcorreram na data desta revisão; a execução precisa ser confirmada antes de classificá-los como atrasados.

| ID | Prazo do PDF | Estado inicial | Checklist / critério de aceite | Evidência |
|---|---|---|---|---|
| E1.1 | 31/07/2026 | A confirmar | [ ] Empresa constituída, CNPJ ativo, conta exclusiva do projeto e contratação contábil conforme instrumento vigente. | Documentos societários, conta e contrato |
| E1.2 | 15/08/2026 | A confirmar; padrão local SQLite | [ ] AWS EC2/RDS PostgreSQL/S3 configurados; desenvolvimento, homologação e produção separados; CI/CD funcional; arquitetura e segurança documentadas. | Inventário de ambientes, execução do pipeline e documento de arquitetura |
| E1.3 | 31/07/2026 | A confirmar | [ ] Contratar as consultorias com escopo, entregas e cronogramas; reconciliar a quantidade de contratos indicada com as rubricas do orçamento. | Contratos e matriz contrato → entrega → rubrica |
| E1.4 | 31/08/2026 | Parcial | [ ] Estruturar pelo menos 24 meses de histórico DATASUS por especialidade, município e hospital; documentar filtros cirúrgicos, cobertura, qualidade e coleta IntegraSUS. | Dicionário de dados, relatório de cobertura e execução de coleta |
| E1.5 | 31/08/2026 | A confirmar | [ ] Realizar cinco entrevistas, identificar pelo menos um hospital para piloto e aprovar wireframes. | Registros de entrevistas, referência ao parceiro e aprovação de wireframes |

## 4. Etapa 2 do PDF — MVP técnico

Fonte: páginas 11–12.

### E2.1 — Previsão de demanda — até 31/10/2026 — parcial

- [ ] Definir o alvo conforme R03 e preparar dados reais com rastreabilidade por fonte e competência.
- [ ] Separar histórico observado de séries sintéticas; nenhum fallback sintético pode gerar selo de validação real.
- [ ] Selecionar o modelo conforme R04, com resultados comparativos documentados.
- [ ] Validar em períodos futuros não usados no treinamento, evitando vazamento temporal.
- [ ] Medir horizontes de 30–90 dias e os recortes acordados; explicitar séries sem cobertura suficiente, tratamento de zeros e limitações.
- [ ] Reportar MAPE abaixo de 15% apenas nos recortes em que o resultado for efetivamente obtido; registrar falhas e plano de melhoria nos demais.
- [ ] Garantir que tela, API e relatório utilizem a mesma avaliação versionada; MAPE calculado sobre ajuste ao próprio treino não substitui teste fora da amostra.
- [ ] Entregar relatório técnico reproduzível com fontes, períodos, preparação, modelo, métricas e limitações.

**Evidência de conclusão:** dataset documentado, execução reproduzível da avaliação, relatório técnico e versão integrada do modelo.

### E2.2 — Priorização clínica — até 15/11/2026 — parcial

- [ ] Incorporar SWALIS, tempo de espera e judicialização ao algoritmo, com regras explícitas para casos graves oncológicos e cardiológicos.
- [ ] Validar qualidade e disponibilidade das datas; não converter ausência de data em espera zero sem identificação.
- [ ] Definir desempates e comportamento para dados ausentes ou inconsistentes.
- [ ] Mostrar ao gestor a justificativa da posição/recomendação e permitir revisão humana.
- [ ] Submeter as regras a revisão clínica e a interpretação normativa a profissional competente, antes de alegar conformidade legal.
- [ ] Documentar testes com cenários representativos e verificar disparidades por região, conforme mitigação prevista no PDF.

**Evidência de conclusão:** especificação das regras, revisão dos responsáveis, testes e exemplos explicáveis, sem exposição de pacientes.

### E2.3 — Redistribuição geográfica — até 30/11/2026 — parcial

- [ ] Validar vínculos CNES, município, hospital e CIR; sinalizar correspondências incertas.
- [ ] Calcular pressão por hospital e especialidade com dados rastreáveis.
- [ ] Distinguir produção histórica de capacidade disponível confirmada; explicar hipóteses de ociosidade.
- [ ] Validar compatibilidade de especialidade, capacidade, região e viabilidade da recomendação; documentar eventuais exceções à mesma CIR.
- [ ] Entregar mapa geográfico interativo por município, vinculado às sugestões e seus filtros.
- [ ] Manter revisão humana e trilha de auditoria das decisões internas; não indicar que pacientes foram transferidos ou AIHs emitidas sem integração e comprovação correspondentes.

**Evidência de conclusão:** mapa operacional, cenários de recomendação revisados, testes de regras e histórico auditável.

### E2.4 — Interface e dashboard — até 30/11/2026 — parcial

- [ ] Integrar os módulos em interface responsiva com estados de carregamento, erro, ausência de dados e atualização desatualizada.
- [ ] Exibir KPIs calculados e fontes/datas; metas e simulações devem ter identificação visível.
- [ ] Implementar exportações PDF/CSV com conteúdo, filtros e datas coerentes com a tela e permissões.
- [ ] Homologar os fluxos de login, fila, previsão, priorização, redistribuição, importação e relatórios por perfil.
- [ ] Realizar teste de usabilidade com cinco gestores reais e atingir score SUS acima de 70, conforme o plano.
- [ ] Registrar NPS separadamente: SUS e NPS são métricas diferentes, ambas mencionadas no PDF.

**Evidência de conclusão:** build aprovado, registros de homologação, arquivos exportados e relatório de usabilidade com método e respostas agregadas.

### E2.5 — IntegraSUS automatizado — até 30/11/2026 — pendente

- [ ] Verificar disponibilidade, condições de acesso e campos da fonte/API antes de definir a integração.
- [ ] Definir frequência real de atualização e limite de atraso aceitável; não prometer tempo real se a fonte não o oferecer.
- [ ] Automatizar coleta, validação e carga sem intervenção manual em cada atualização.
- [ ] Preservar snapshots históricos necessários ao treinamento, sem apagar a única cópia do histórico.
- [ ] Tratar duplicações, falhas, mudanças de esquema e reprocessamento sem corromper a base válida anterior.
- [ ] Monitorar execução, volume, competência e falhas; refletir a última atualização válida na interface.

**Evidência de conclusão:** execuções sucessivas automatizadas em produção, logs sem dados sensíveis, teste de recuperação de falha e documentação da integração.

### Critérios transversais antes do piloto

- [ ] Documentar acesso e tratamento de dados, anonimização utilizada, criptografia em trânsito e em repouso e responsabilidades contratuais previstas no PDF. Não presumir conformidade pela presença de iniciais em vez de nomes.
- [ ] Demonstrar permissões por perfil e instituição, registro de ações relevantes e configuração segura dos ambientes.
- [ ] Executar e registrar backup/restauração e procedimento de atualização/reversão da aplicação.
- [ ] Eliminar erros que bloqueiem os fluxos do piloto e documentar limitações conhecidas.
- [ ] Publicar instruções de operação e treinamento para os gestores participantes.

Esses critérios tornam verificáveis os compromissos de segurança e operação; não constituem parecer jurídico ou certificação.

## 5. Etapa 3 do PDF — piloto e preparação comercial

Fonte: página 14. Estado inicial: a confirmar para entregas externas; não comprovadas nesta inspeção.

| ID | Prazo do PDF | Checklist / critério de aceite | Evidência |
|---|---|---|---|
| E3.1 | 01/12/2026–28/02/2027 | [ ] Implantar piloto em hospital público parceiro, formalizar cooperação, treinar gestores e acompanhar KPIs quinzenalmente durante os 90 dias previstos. | Termo, implantação, treinamento e relatórios |
| E3.2 | 28/02/2027 | [ ] Realizar pelo menos 15 demonstrações, enviar três propostas e mapear um processo de contratação pública. | Registros comerciais e propostas |
| E3.3 | 28/02/2027 | [ ] Priorizar feedbacks, implementar melhorias, publicar nova versão e atualizar avaliação com dados do piloto. | Registro de feedback, mudanças e métricas |
| E3.4 | 31/01/2027 | [ ] Protocolar pedido de registro de software no INPI. | Número de protocolo e referência ao comprovante |
| E3.5 | 28/02/2027 | [ ] Produzir um case com dados reais, kit comercial, site institucional com contato e minuta de contrato SaaS revisada. | Materiais publicados e minuta aprovada |

### Comprovação de impacto

- [ ] Definir a linha de base de espera, população, especialidades e janela de acompanhamento antes da medição do piloto.
- [ ] Usar datas adequadas para medir espera por cirurgia; dias de internação do SIH não medem diretamente espera na fila.
- [ ] Definir como comparar os períodos e registrar mudanças de volume, capacidade e composição dos casos.
- [ ] Reportar o resultado efetivamente observado, com limitações; manter “até 40%” como potencial/meta enquanto não houver comprovação.
- [ ] Distinguir projeção do simulador, recomendação aceita e resultado assistencial observado.

## 6. Etapa 4 do PDF — comercial, suporte e encerramento

Fonte: página 16. Estado inicial: a confirmar; entregas não comprovadas no repositório.

| ID | Prazo do PDF | Checklist / critério de aceite | Evidência |
|---|---|---|---|
| E4.1 | 30/04/2027 | [ ] Obter ao menos uma proposta formal aceita e iniciar ao menos um processo de contratação pública, conforme procedimentos vigentes. | Aceite e referência ao processo |
| E4.2 | 31/05/2027 | [ ] Prospectar pelo menos três estados nordestinos e enviar cinco propostas fora do Ceará. | Registros e propostas |
| E4.3 | 30/04/2027 | [ ] Disponibilizar suporte por tickets, base de conhecimento, manuais, SLA e onboarding padronizado. | Sistema de suporte e documentação publicada |
| E4.4 | 31/05/2027 | [ ] Entregar relatório final e prestação de contas com atividades, recursos, resultados versus metas e comprovantes. | Relatório, documentação financeira e protocolo de entrega |
| E4.5 | 31/05/2027 | [ ] Elaborar plano de expansão, mapear pelo menos dois editais e atualizar pitch com resultados reais. | Plano, mapeamento e pitch |

## 7. Revisão de coerência do documento e orçamento

São pontos para revisão, não autorização para alterar o projeto aprovado.

- [ ] **Metas versus resultados:** uniformizar “potencial de redução” e evitar “reduzindo 40%” como fato já demonstrado.
- [ ] **Modelos existentes:** revisar a declaração Prophet/ARIMA/XGBoost frente ao código atual.
- [ ] **Integração atual versus futura:** deixar claro que automação IntegraSUS é entrega prevista e importação manual pertence ao protótipo.
- [ ] **Piloto de 30 versus 90 dias:** o texto comercial propõe 30 dias; o cronograma de execução prevê 90 dias. Explicar se são ofertas diferentes ou corrigir a divergência.
- [ ] **Consultorias:** a etapa 1 indica cinco contratos; o orçamento discrimina ML, comercial público, comercial privado, UX/UI, integração e jurídico. Mapear as seis frentes e explicar eventual agrupamento de contratos.
- [ ] **SUS versus NPS:** estabelecer instrumentos, amostras e momentos de coleta separados; não tratar um indicador como evidência do outro.
- [ ] **Afirmações de mercado:** reunir fontes para tamanho de mercado, números de fila, ausência de concorrentes e pioneirismo; ajustar afirmações absolutas sem sustentação.
- [ ] **Referências legais e regulatórias:** solicitar revisão atualizada das afirmações sobre contratação, limites monetários, prazos assistenciais e enquadramento regulatório antes de reutilizá-las comercialmente.
- [ ] **Orçamento:** reconciliar rubricas e execução com R$ 85.752,00 de subvenção, R$ 4.288,00 de contrapartida e R$ 90.040,00 totais indicados no PDF; validar classificação das despesas com contabilidade e regras aplicáveis.
- [ ] **Completude textual:** revisar o trecho truncado em “contratos de processamento com parc” e a duplicação de texto na atividade de constituição da empresa.

## 8. O que fica fora da conclusão do MVP

O PDF posiciona integração Tasy, MV e RNDS/FHIR para redes privadas como pós-MVP. Não bloquear a entrega inicial por essas integrações sem alteração expressa do escopo. Da mesma forma, funcionalidades adicionais do README, como billing automatizado, não devem ser transformadas automaticamente em obrigação do plano Centelha.

## 9. Marcos de aceite

| Marco | Condição para declarar concluído |
|---|---|
| Retomada técnica | T01–T07 atendidos e decisões R01–R06 registradas |
| MVP apto ao piloto | Entregas técnicas E2.1–E2.5 aceitas; dados, segurança, infraestrutura e operação demonstrados; limitações explícitas |
| MVP validado no cliente | Piloto e usabilidade executados; resultados reais documentados; correções críticas resolvidas |
| Projeto Centelha encerrado | Entregas técnicas, comerciais e administrativas do plano vigente comprovadas, com relatório final e prestação de contas |

Não atribuir percentual geral de conclusão antes de revisar os itens “a confirmar” e definir pesos: contar telas prontas distorceria o avanço do projeto.

## 10. Registro de revisão e decisões

| Data | ID | Decisão / evidência | Responsável | Próxima ação |
|---|---|---|---|---|
| 15/09/2026 | Diagnóstico | Checklist inicial baseado no PDF e inspeção local; nenhuma entrega externa presumida concluída | A definir | Revisar R01–R06 e priorizar primeiro ciclo |

**Ordem sugerida para continuar:** confirmar ambiente e escopo → corrigir compilação e afirmações → reconciliar dados em cópia → avaliar previsão real → completar priorização, redistribuição e exportação → automatizar atualização → homologar → executar piloto → concluir entregas comerciais e prestação de contas. Infraestrutura e organização administrativa podem avançar em paralelo quando houver responsáveis definidos.
