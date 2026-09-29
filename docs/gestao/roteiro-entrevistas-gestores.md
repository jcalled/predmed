# PREDMED — Roteiro das entrevistas com gestores (atividade 4)

Versão: 29/09/2026 (v1). Item B15 do backlog. Elaborado pelo gerente de projetos (agente); **revisão e condução: proponente**.
Atividade 4 do plano — "Validação do roadmap com gestores" (M2–M3). Indicadores de aceite (proposta): **5 entrevistas realizadas; 1 hospital parceiro identificado para piloto; wireframes aprovados**.

Este roteiro não é instrumento de pesquisa científica. Se houver intenção de publicar os resultados como pesquisa, consultar a jurídica sobre necessidade de submissão a Comitê de Ética antes de realizar as entrevistas.

## 1. Objetivos

| # | Objetivo | Indicador / uso |
|---|---|---|
| O1 | Entender o processo real de regulação cirúrgica (quem decide, com que dados, em que ritmo) | Ajuste do roadmap e das telas (ativ. 4 e 8) |
| O2 | Validar as regras de priorização v0.1 (`docs/dados/regras-priorizacao-v0.1.md`) | Revisão clínica/jurídica (B34, ativ. 6) |
| O3 | Calibrar os parâmetros da redistribuição e obter a decisão política sobre redistribuir fora da CIR (`docs/dados/redistribuicao-v1.md`) | Ativ. 7; caminho da meta de −40% (R19) |
| O4 | Confirmar o significado oficial do campo `data` do IntegraSUS e revisar vínculos CNES provisórios | Linha de base de espera (R08); R20 |
| O5 | Obter aprovação dos wireframes/telas por perfil (`docs/ux/arquitetura-telas.md`) | Indicador "wireframes aprovados" |
| O6 | Identificar ao menos 1 hospital público para o piloto de 90 dias e as condições para o termo de cooperação | Indicador "1 hospital parceiro"; ativ. 10 |
| O7 | Mapear o caminho de contratação pública (modalidade, orçamento, quem compra) | Ativ. 11 e 15 |

## 2. Perfis dos entrevistados (5 entrevistas)

A lista nominal de contatos fica **fora do Git** (local restrito do proponente). Aqui só perfis e códigos.

| Código | Perfil | Por que | Blocos prioritários |
|---|---|---|---|
| E01 | **SESA** — gestão estadual de regulação/atenção especializada (coordenadoria de regulação, CIEGES ou equivalente) | Dona da fila estadual e do IntegraSUS; aprova redistribuição em todo o estado (D11); decide sobre fora da CIR | A, B, C, E1–E5, F, G |
| E02 | **SMS** — secretaria municipal de saúde de município-sede de CIR com pressão alta (ex.: CIR de Fortaleza ou Maracanaú, pressão 5,8 e 7,4) | Aprova redistribuição na própria CIR (D11); gestora de hospitais municipais | A, B, D, E2, E3, F, G |
| E03 | **Diretor(a) de hospital público** (estadual ou municipal) com fila cirúrgica relevante | Candidato natural ao piloto; valida capacidade ociosa e parâmetros | A, B, C, D, E2, E5, F |
| E04 | **Regulador(a)** — médico(a) regulador(a) ou coordenador(a) de central de regulação | Valida SWALIS, pesos da priorização, uso do campo `data` e rotina de trabalho | A, B, C, D, E1, E4 |
| E05 | **Hospital privado conveniado/contratualizado ao SUS** (diretor ou gestor comercial) | Lado "oferta": vagas SUS declaradas, remuneração, interesse em receber redistribuição | A, B, D, E2, G |

Se possível, entrevistar mais de um perfil por instituição não conta como entrevista extra para o indicador; registrar à parte.

## 3. Logística

- Duração: 50–60 min (E01 e E04 podem precisar de 75 min por causa do bloco de validação). Remoto ou presencial.
- Equipe: proponente conduz; uma segunda pessoa anota (se não houver, gravar o áudio com consentimento).
- Material: demonstração do PREDMED em ambiente **sem dados de pacientes** (tenant de demonstração ou telas com dados agregados); cópia impressa/PDF das tabelas do bloco E.
- Antes: enviar convite com objetivo, duração e aviso de que **não serão pedidos dados de pacientes**.
- Ordem sugerida: E04 (regulador) e E03 (hospital) primeiro, para chegar à SESA (E01) com as regras já testadas; E01 antes de fechar o hospital do piloto.

## 4. Protocolo de registro sem dados pessoais

| Regra | Como aplicar |
|---|---|
| Identificação do entrevistado | No Git e nas sínteses: só código (E01–E05), perfil e tipo de instituição. Nome, cargo exato, e-mail e telefone ficam na lista restrita fora do Git |
| Dados de pacientes | **Não pedir, não anotar, não gravar.** Se o entrevistado citar um caso com nome, iniciais, nº de solicitação, prontuário ou CPF, interromper a anotação daquele trecho e registrar só "caso ilustrativo sobre [tema]" |
| Instituições | Nomes de hospitais e municípios podem ser registrados (dado institucional). Números de fila por hospital só agregados |
| Consentimento | Pedir consentimento verbal no início para anotar e (se for o caso) gravar; registrar "consentimento: sim/não" na síntese. Gravações ficam fora do Git e são apagadas após a síntese validada (prazo: 30 dias) |
| Citações | Sem atribuição nominal. Citação textual só com autorização explícita e anonimizada ("gestor(a) municipal") |
| Informação sensível institucional | Se o entrevistado pedir sigilo sobre algum ponto (ex.: orçamento, conflito entre gestores), registrar só no local restrito |
| Armazenamento | Síntese sem dados pessoais: `docs/gestao/entrevistas/EXX-sintese.md` (criar a pasta quando houver a primeira). Notas brutas e áudio: local restrito, criptografado |
| Revisão | GP revisa cada síntese antes do commit, procurando nomes, iniciais, números de solicitação, CPF/CNS |

## 5. Roteiro

### Bloco A — Abertura e contexto (5 min)

1. Apresentação do PREDMED: apoio à decisão para previsão de demanda, priorização clínica e redistribuição regional. **Não** executa regulação, transferência nem emissão de AIH.
2. Consentimento (seção 4).
3. Qual é o seu papel na fila cirúrgica? Com que frequência toma decisões sobre ela (diária, semanal, mensal)?

### Bloco B — Processo e dores (10 min)

1. Descreva o caminho de um pedido cirúrgico desde a solicitação até a cirurgia. Onde ele mais trava?
2. Quem decide a ordem de chamada? Que critérios são usados na prática (SWALIS, data, judicial, gravidade, capacidade do hospital)?
3. Como você sabe hoje se a fila está crescendo ou diminuindo? Com que dado e com que atraso?
4. Que decisão você gostaria de tomar e não consegue por falta de informação?
5. Como são tratados hoje os pedidos com mandado judicial?
6. Já houve mutirões ou remanejamento de pacientes entre hospitais? Como foi decidido e como foi medido o resultado?

### Bloco C — Dados e sistemas (5–10 min)

1. Quais sistemas vocês usam (Fastmedic, IntegraSUS, sistema do hospital, planilhas)? Quem tem acesso ao quê?
2. A data de entrada na fila e a data de saída (cirurgia, cancelamento, desistência) ficam registradas? Onde?
3. Existe algum indicador oficial de tempo de espera cirúrgico? Como é calculado?
4. Com que frequência os dados precisam estar atualizados para serem úteis (hora, dia, semana)?

### Bloco D — Demonstração e aprovação das telas (10–15 min)

Mostrar as telas do perfil do entrevistado (`docs/ux/arquitetura-telas.md`): Painel, Fila cirúrgica, Priorização, Previsão de demanda, Redistribuição (+ Oportunidades SUS para E05).

1. O que nesta tela você usaria toda semana? O que não usaria?
2. Falta alguma informação para decidir? Sobra alguma?
3. Os selos "medido", "estimado" e "simulado" ficaram claros?
4. Para quem mais essa tela seria útil na sua instituição?
5. **Registro de aprovação:** "As telas apresentadas atendem ao seu perfil, com os ajustes anotados?" — aprovado / aprovado com ajustes / não aprovado. Anotar ajustes pedidos.

Se o entrevistado aceitar, aplicar ao final as tarefas curtas e o questionário SUS (atividade 8); registrar separadamente, pois o teste formal de usabilidade tem protocolo próprio.

### Bloco E — Validação (20–30 min)

Apresentar como **proposta a validar**, nunca como regra em uso. Anotar a resposta em cada linha das tabelas.

#### E1. Regras de priorização v0.1 (E01, E04; E03 opcional)

Critérios atuais (máx. 100): SWALIS até 40 (A1 = 40, A2 = 32, B = 24, C = 12, D = 4; ausente = 12 + alerta); tempo de espera até 30 (satura em 2 anos); mandado judicial +15; oncologia +10; cardiovascular grave (SWALIS A1/A2) +5. Desempate: maior espera.

| # | Pergunta (de `regras-priorizacao-v0.1.md`) | Resposta |
|---|---|---|
| P1 | Os pesos relativos (SWALIS 40 × espera 30 × judicial 15 × oncologia 10) refletem a prática da regulação? | |
| P2 | O tempo de espera deve ser medido contra o **tempo-alvo de cada categoria SWALIS** em vez de uma escala única de 2 anos? Quais são os tempos-alvo adotados? | |
| P3 | Mandado judicial deve somar pontos ou ser tratado como obrigação à parte (fila separada)? | |
| P4 | Quais procedimentos cardiológicos e oncológicos devem receber prioridade adicional além da especialidade? | |
| P5 | Como tratar SWALIS "Não Informada" (1.741 pedidos na coleta de 28/09/2026)? | |
| P6 | Há critérios de equidade a monitorar (por CIR, município, hospital)? A proposta prevê auditoria de disparidades regionais | |

Pergunta complementar (Lei 12.732/2012): o sistema só sinaliza oncologia com mais de 60 dias desde a **solicitação**; o prazo legal conta do diagnóstico. Existe fonte da data de diagnóstico acessível à regulação?

#### E2. Parâmetros da redistribuição (E01, E02, E03, E05)

Hoje as sugestões são **estimadas**, restritas à mesma CIR e sempre sujeitas à aprovação humana (SMS na própria CIR, SESA no estado — D11).

| Parâmetro | Valor atual | Pergunta de calibração | Resposta |
|---|---|---|---|
| Turnos cirúrgicos por sala por dia | 2 | Quantos turnos eletivos uma sala realmente opera (manhã/tarde/noite; dias úteis)? | |
| Cirurgias por turno por sala | 2 (≈ 88 cirurgias/sala/mês em 22 dias) | É realista? Varia por especialidade? | |
| Permanência pós-operatória média | 3 dias (ocupação-alvo 85% dos leitos cirúrgicos SUS) | Qual a permanência típica? O gargalo é sala, leito, UTI, anestesista ou OPME? | |
| Máximo recebido pelo destino | +50% da produção mensal do destino na especialidade | Quanto um hospital absorve a mais sem desorganizar a própria fila? | |
| Excedente redistribuível na origem | Fila acima de **1,5 mês** da própria produção na especialidade | A partir de quantos meses de fila faz sentido transferir? | |
| Destino apto | ≥ 2 AIH/mês na especialidade; fila própria ≤ 1 mês; habilitação CNES para oncologia, cardiovascular e neurologia | Faltam critérios (equipe, OPME, contrato, teto financeiro)? | |
| Capacidade | Estimada por produção histórica, salas e leitos do CNES — não é vaga confirmada | O hospital aceitaria **declarar** vagas mensais no sistema (como já fazem os privados)? | |

#### E3. Decisão política: redistribuição fora da CIR (E01 obrigatório; E02 opinião)

Contexto (agregado, `redistribuicao-v1.md`): pressão de 7,4 na CIR de Maracanaú e 5,8 na de Fortaleza, enquanto há CIR do interior com pressão < 1. A regra atual "mesma CIR" impede que essa capacidade estimada alivie a capital. Com ela, a simulação de mutirão de 90 dias redistribui 2,9% da fila (**simulado**).

| # | Pergunta | Resposta |
|---|---|---|
| F1 | A SESA admite recomendar redistribuição **entre CIR da mesma macrorregião**? E **em todo o estado**? Para quais especialidades? | |
| F2 | Que instância teria de pactuar isso (CIR, CIB, PPI) e quem aprovaria cada transferência no sistema? | |
| F3 | Condições: transporte/TFD, acompanhante, retorno pós-operatório, consentimento do paciente, financiamento (teto do destino) | |
| F4 | Distância ou tempo máximo de deslocamento aceitável por tipo de cirurgia? | |
| F5 | Se não for permitido hoje, aceitaria como **cenário de simulação** rotulado, para subsidiar pactuação? | |

A decisão cabe à gestão (SESA/CIB); o PREDMED só recomenda. Registrar a resposta como decisão do gestor, com data, sem atribuição nominal no Git.

#### E4. Significado oficial do campo `data` do IntegraSUS (E01, E04)

O PREDMED usa o campo `data` do painel público "Consulta da Fila de Espera" como data de entrada na fila (coerente com o nº de solicitação em 94% da fila; séries legadas de 3 a 6 dígitos, cerca de 4,5%, marcadas "a confirmar"). O significado não está documentado.

| # | Pergunta | Resposta |
|---|---|---|
| D1 | O campo `data` é a data de criação da solicitação no sistema de regulação, de inserção na fila cirúrgica, de autorização ou outra? | |
| D2 | Muda quando o pedido é reclassificado, transferido de unidade ou reinserido? | |
| D3 | As numerações antigas (3 a 6 dígitos) vieram de migração de outro sistema? A data delas é confiável? | |
| D4 | Há dado oficial de **saída** da fila (data e motivo) acessível ao projeto? (painel restrito "Fila de Cirurgias Eletivas") | |
| D5 | Há restrição de uso dos dados do painel público por terceiros? Existe termo de uso ou canal formal (ofício, cooperação)? | |

Encaminhamento: formalizar D1–D5 no ofício à SESA.

#### E5. Revisão de vínculos CNES provisórios (E01, E03 quando for da região)

| Nome na fila | Sugestão automática (provisória) | Alternativa | Pergunta | Resposta (CNES correto) |
|---|---|---|---|---|
| HOSPITAL INFANTIL LUCIA DE FATIMA (HIF) | SOPAI Hospital Infantil — Fortaleza (confiança baixa; provavelmente errada) | HIAS Hospital Infantil Albert Sabin — Fortaleza, ou outro | Qual estabelecimento (CNES) opera essa fila? | |
| HOSPITAL SAO RAIMUNDO | Hospital São Raimundo — Crato | Hospital São Raimundo — Várzea Alegre | Qual dos dois? Ou ambos? | |

Outros 24 CNES provisórios estão em `docs/dados/vinculo-fila-cnes-revisao.md`; perguntar se o entrevistado pode indicar quem na SESA valida essa lista.

### Bloco F — Piloto (10 min; E01, E02, E03)

1. Sua instituição (ou alguma que indique) teria interesse em um piloto de 90 dias, em modo apoio à decisão, sem acesso a sistemas internos no início?
2. Quem precisaria autorizar (direção, secretaria, jurídico, TI, encarregado de dados)?
3. Que dados o hospital poderia fornecer sob termo de cooperação (data de entrada e saída da fila, agenda cirúrgica, vagas)? Em que formato?
4. Qual resultado tornaria o piloto um sucesso para você? (tempo de espera, fila zerada em uma especialidade, previsibilidade de agenda, redução de judicialização)
5. Qual especialidade ou fila seria o melhor recorte para o piloto?
6. Relatórios quinzenais de KPIs: para quem e em que formato?

### Bloco G — Adoção e contratação (5 min; E01, E02, E05)

1. Se o piloto funcionar, como a instituição contrataria (dispensa, inexigibilidade, pregão, termo com ICT, outro)?
2. Há orçamento ou programa (estadual ou federal de redução de filas) que financie esse tipo de ferramenta?
3. Quem mais deveríamos ouvir? (pedir indicação, sem registrar nomes no Git)

### Encerramento (2 min)

Agradecer; combinar retorno com a síntese para validação do entrevistado; perguntar se aceita ser contatado para o teste de usabilidade (atividade 8).

## 6. Identificação do hospital para o piloto

Critérios para classificar os candidatos (preencher após E01–E03; lista nominal fora do Git se houver sigilo):

| Critério | Peso | Como verificar |
|---|---|---|
| Hospital público (exigência do indicador da atividade 10) | eliminatório | CNES (natureza jurídica) |
| Fila cirúrgica relevante na coleta IntegraSUS (volume e pressão) | alto | Dados agregados do PREDMED |
| Direção disposta a assinar termo de cooperação técnica | eliminatório | Bloco F, pergunta 2 |
| Consegue fornecer datas de entrada e saída da fila (linha de base e medição) | alto | Bloco F, pergunta 3 |
| Vínculo CNES com confiança ALTA (não provisório) | médio | `vinculo-fila-cnes-revisao.md` |
| Gestão (SMS/SESA) da CIR apoia o piloto | alto | E01/E02 |
| Tem especialidade com capacidade ociosa estimada ou recebe redistribuição na CIR | médio | `redistribuicao-v1.md` |
| Distância e disponibilidade para acompanhamento quinzenal | baixo | — |

Resultado esperado ao fim da atividade 4: **1 hospital identificado** (interesse registrado + responsável indicado) e 1–2 alternativas. "Identificado" ≠ "formalizado": a formalização é o termo de cooperação (B41, jurídica).

## 7. Modelo de síntese por entrevista

```markdown
# Entrevista EXX — síntese (sem dados pessoais)

Data: __/__/____ | Perfil: [SESA / SMS / hospital público / regulador / hospital privado conveniado]
Tipo de instituição: [...] | Formato: remoto/presencial | Duração: __ min
Consentimento para anotação: sim/não | Gravação: sim/não (apagar até __/__/____)

## Principais dores (até 5)
## Decisões que o sistema deve apoiar
## Validação
- Priorização P1–P6: [respostas]
- Redistribuição (parâmetros): [respostas]
- Fora da CIR F1–F5: [respostas]
- Campo `data` D1–D5: [respostas]
- Vínculos CNES: [respostas]
## Telas: aprovado / aprovado com ajustes / não aprovado — ajustes: [...]
## Piloto: interesse [sim/não/talvez]; condições; recorte sugerido
## Contratação: modalidade provável; orçamento
## Ações decorrentes (item do backlog, responsável)
Revisado por GP em __/__/____ (checagem de dados pessoais: ok)
```

## 8. Consolidação

Após as 5 entrevistas, o GP consolida em `docs/gestao/entrevistas/consolidado.md`: necessidades por perfil, respostas do bloco E lado a lado, decisões do gestor para registrar em `decisoes.md` (ex.: regra de CIR, pesos), ajustes de backlog e o status dos três indicadores da atividade 4.
