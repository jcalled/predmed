# Meta de −40% no tempo de espera: métrica, cenários e protocolo do piloto

Versão: 29/09/2026. Resultado versionado: `backend/avaliacoes/meta40/cenarios_20260929.json` (`versao = cenarios-meta40-v1`) e `mapa_recortes_20260929.csv`.
Código: `backend/services/cenarios_meta40.py` (regras puras), `backend/_SCRIPTS/cenarios_meta_40.py` (execução), `backend/routers/meta40.py` (`GET /meta40/cenarios`, só SESA e SMS; a SMS vê só a própria CIR).
Testes: `backend/tests/test_cenarios_meta40.py` (dados sintéticos).

Promessa da proposta: "reduzindo o tempo de espera em **até 40%**". KPI do piloto (atividade 10, M7–M9, mar–mai/2027 pela planilha): "redução mensurável do tempo de espera registrada", com relatórios quinzenais.

**Tudo neste documento é SIMULADO.** A capacidade ociosa é **estimada** (CNES + SIH), não é vaga confirmada. Nenhum número daqui pode ser apresentado como redução medida.

## Resumo

1. **Métrica escolhida:** tempo médio de espera pela **Lei de Little**, `W = L / λ`, por estabelecimento × especialidade.
   - `L` é a fila ativa saneada. `λ` são as entradas por mês.
   - Com as entradas estáveis, reduzir `W` em 40% significa fazer, no período, **atendimentos adicionais iguais a 40% da fila**. Isso vale para qualquer ordem de atendimento.
   - A mediana da idade dos pedidos na fila entra como confirmação obrigatória.
2. **No estado inteiro, −40% em 90 dias não é atingível** com a capacidade estimada, nem somando todas as alavancas ao mesmo tempo.
   - Ociosidade estimada: −12,7%.
   - Ociosidade e turno extra: −29%.
   - Ociosidade, turno extra e privados: −38%.
   - Esses três números são limite superior: supõem que qualquer capacidade serve a qualquer especialidade e CIR.
   - Com ociosidade e turno extra mantidos, −40% leva cerca de **4 meses**; só com a ociosidade, cerca de 9,5 meses.
3. **Em recortes, −40% em 90 dias é atingível**, desde que o recorte tenha precedência sobre a capacidade ociosa. De 187 recortes (fila ≥ 50):
   - 32 chegam lá só com a redistribuição na mesma CIR;
   - 77 somando a ociosidade do próprio hospital;
   - 106 somando também um turno extra;
   - 135 abrindo para a macrorregião.
   - A versão **robusta** supõe que só 60% da capacidade estimada se confirma. Nela, os números caem para 10, 52, 65 e 103.
4. **Os recortes são alternativos, não simultâneos.** Com a capacidade dividida entre todas as origens (regra atual da redistribuição v1), só 9 recortes chegam a 40%.
5. **Recomendação:** pré-registrar como piloto um hospital público com fila de 100 a 400 pedidos numa especialidade de volume, que atinja 40% no cenário robusto só com as alavancas do PREDMED (seção 5).
   - Exemplos de perfil: ortopedia ou ginecologia de hospital de Fortaleza com ociosidade própria e vizinhos compatíveis; cirurgia digestiva de hospital municipal de Sobral.
   - **Não** usar a fila de Fortaleza inteira: lá o máximo simulado é −12% a −46% em 90 dias, conforme a especialidade.

## 1. Definição operacional da métrica

### 1.1 Métrica primária: tempo médio de espera pela Lei de Little

`W = L / λ`, em dias, calculada por recorte pré-registrado (estabelecimento executante × especialidade da fila IntegraSUS).

| Termo | Definição | Fonte |
|---|---|---|
| `L` | Pedidos ativos no recorte: média das coletas dos últimos 7 dias antes da data de medição. Excluem-se os pedidos classificados como **saneamento** (1.4) | Coletas IntegraSUS, 2 por dia, `manifesto.jsonl` e snapshots criptografados |
| `λ_ref` | Entradas por mês no recorte (novos `codSolicitacao`). É a média de **todas as semanas de coleta antes do piloto**, sem 20/12 a 10/01. Fica **fixa e pré-registrada** | Diferença entre coletas consecutivas |
| `W_t` | `L_t / λ_ref × 30,44` | — |
| Redução | `R = 1 − W_fim / W_base = 1 − L*_fim / L*_base`. O `*` indica fila saneada; o saneamento é aplicado igualmente nas duas pontas | — |

**Por que esta métrica:**
- **É o tempo médio de espera.** Pela Lei de Little, numa fila estável o tempo médio de permanência é `L/λ`. É a leitura mais direta do "tempo médio de espera" citado na proposta.
- **Não depende da ordem de atendimento.** Escolher pacientes recentes ou fáceis não melhora `W`: só atendimento adicional reduz `L`. A priorização clínica não é penalizada nem premiada (seção 3.4).
- **É mensurável agora e a cada quinzena**, só com contagens das coletas públicas. Não precisa ligar pacientes a AIH, o que é bom para a LGPD.
- **Resiste à tentativa de "fechar a porta".** Com `λ_ref` fixo, recusar novos pedidos reduziria `L`. Por isso há uma trava: `λ` observado no piloto ≥ 85% de `λ_ref`.
- **O denominador fica fixo.** Com `λ` fixo, oscilações sazonais de entradas (férias, Carnaval) não fabricam redução. O `W` com `λ` observado entra como análise de sensibilidade.

**Métricas descartadas como primárias:**
- **Mediana da espera dos atendidos** (tempo entre solicitação e saída):
  - quando se atende o estoque antigo, ela **sobe** nos primeiros meses, embora o sistema melhore. Esse é o paradoxo do FIFO;
  - além disso, as coletas não dizem o motivo da saída.
  - Fica como indicador descritivo.
- **Mediana da idade do estoque:** é observada diretamente, mas depende da ordem de atendimento e da qualidade das datas antigas (numeração legada). Fica como **confirmação obrigatória**: precisa cair no mesmo sentido.
- **Tamanho da fila sozinho:** pode ser manipulado fechando entradas ou removendo pedidos sem atendimento.

### 1.2 Métricas secundárias (pré-registradas; relatadas sempre)

1. Mediana e P90 da idade dos pedidos ativos, e % acima de 180 dias.
2. `W` com `λ` observado nas últimas 12 semanas (sensibilidade).
3. `W` do subgrupo prioritário: SWALIS A1, judicializado ou oncológico.
4. Saídas por motivo informado pelo hospital, em contagem quinzenal: realizada no hospital, realizada no destino por transferência, cancelada ou desistência, óbito, saneamento.
5. `W` da mesma especialidade na CIR, **sem** o hospital piloto (trava contra deslocamento de fila).
6. Mediana da espera dos atendidos (descritiva).

### 1.3 Como apresentar "até 40%" sem enganar

1. **O recorte é declarado antes.** Hospital, especialidades, métrica, `λ_ref`, data de início e de fim e critério de sucesso ficam registrados num documento datado (commit e ofício à SESA e à FUNCAP) **antes** do primeiro dia do piloto. Não vale escolher depois o recorte que deu certo.
2. **A linha de base é medida antes** com as coletas automáticas (desde 28/09/2026: cerca de 20 semanas até mar/2027).
3. **Texto modelo:** "No recorte pré-registrado X, o tempo médio de espera (Lei de Little) caiu Y% em 90 dias. No mesmo período, recortes comparáveis sem intervenção variaram Z%. Nossa simulação estima, para o estado inteiro com a capacidade hoje ociosa, um potencial de A% em 90 dias."
4. **Nunca** extrapolar o resultado do recorte para o estado. "Até 40%" quer dizer que 40% é o **máximo demonstrado em um recorte**, e não a média do sistema.
5. **Sem atalhos:** saneamento, "fechamento da porta" e transferência sem cirurgia **não contam**.

### 1.4 Saneamento da fila (alavanca f): separado, com efeito zero na métrica

- **Remover da fila não é reduzir espera** quando não houve atendimento.
- **Regra:** todo pedido removido por saneamento é tirado **também da linha de base**, e o `L*_base` é recalculado. Motivos de saneamento: duplicidade, pedido sem validade, paciente operado em outro serviço, pedido com informação inválida.
- **Efeito na métrica:** nenhum. O ganho do saneamento é administrativo (lista fiel) e vai para um relatório à parte.

**Candidatos a saneamento hoje** (estoque de 28/09/2026; só contagens; **candidatos, não confirmados**):

| Critério | Pedidos |
|---|---:|
| Numeração legada, data a confirmar (`data_confiavel = 0`) | 2.786 |
| Mais de 2 anos na fila | 16.932 |
| Possível duplicidade (mesmas iniciais, município e procedimento no mesmo estabelecimento × especialidade; há falsos positivos esperados) | 400 |

- **Por que isso importa:** esses pedidos pesam muito no tamanho e na idade do estoque.
- **Exemplo de conta enganosa:** um "saneamento" de 17 mil pedidos antigos, contado como redução, daria −27% na fila estadual sem nenhuma cirurgia. É exatamente o número que **não** pode ser apresentado como resultado.

## 2. Linha de base atual (medida na coleta de 28/09/2026)

**Fila estadual:**
- Total: 61.731 pedidos com CNES (mais 25 sem CNES, fora do mapa).
- Entradas estimadas: ≈ 8.900 por mês.
- **W ≈ 211 dias**, que é limite superior (ver abaixo).
- Mediana da idade do estoque: 299 dias; P90: 1.259 dias; 60% do estoque passa de 180 dias.

**Por que o W é limite superior:**
- `λ` foi estimado pelos pedidos dos últimos 28 dias **que ainda estão na fila**; o valor real é maior.
- Pedidos que continuam na fila, por semana de solicitação, relativos à semana mais recente: 100%, 87%, 73%, 65%, 67% e 48%. Parte das entradas sai em poucas semanas.
- Nas duas coletas de 28 e 29/09 houve 456 entradas e 456 saídas; a mediana da idade das saídas foi de 14 dias (uma única observação).
- **A redução percentual `R` não depende de `λ`.** A linha de base oficial usará `λ` medido pela diferença entre coletas.

**Por grupo** (W de Little e idade do estoque; agregados):

| Grupo | Fila | Entradas/mês (est.) | W (dias) | Mediana da idade (dias) | > 180 dias |
|---|---:|---:|---:|---:|---:|
| SWALIS A1 (prioridade máxima) | 11.760 | 1.059 | 338 | 335 | 64% |
| SWALIS B | 8.926 | 503 | 540 | 536 | 77% |
| SWALIS C | 4.347 | 289 | 458 | 550 | 77% |
| SWALIS D | 34.982 | 7.075 | 151 | 179 | 50% |
| Judicializados | 236 | 8 | 944 | 494 | 81% |
| Oncologia | 2.640 | 845 | 95 | 76 | 36% |
| Cardiovascular | 3.490 | 331 | 321 | 383 | 70% |

**Achado:** os pacientes A1 esperam **mais** que os D. Isso é o contrário do que a classificação pretende. Há duas hipóteses a confirmar com a SESA:
- a classificação é reavaliada durante a espera (quem espera mais sobe de categoria);
- os casos A1 são mais complexos (UTI, órtese, prótese e material especial) e travam por outro gargalo.

Nos dois casos, a priorização (alavanca d) pode reduzir muito a espera dos graves **sem** mudar a média.

## 3. Modelo de cenários (SIMULADO)

### 3.1 Fórmula

Hipóteses do modelo:
- fila estável (entradas = saídas habituais);
- `λ` constante;
- a capacidade adicional é usada com pacientes **do recorte**.

Com isso:

```
redução(90 dias) = min(L, extra_mês × 3) / L
extra necessário para 40% = 0,40 × L / 3   (por mês, por 3 meses)
```

- **Depois do piloto:** com a capacidade extra encerrada e entradas iguais às saídas, a fila fica no novo nível. Esta é uma aproximação por fluxo médio; na prática, ela tende a voltar se a produção habitual for menor que as entradas.
- **Fontes:** a fila é a do IntegraSUS em `pacientes_fila`; a produção e a ociosidade vêm da redistribuição v1 (`producao_cirurgica_cnes`, 2024-07 a 2026-06; `cnes_capacidade` 2026-08).

### 3.2 Alavancas (capacidade adicional por mês)

| Id | Alavanca | Como é estimada | Natureza | Quem decide |
|---|---|---|---|---|
| a | Redistribuição na **mesma CIR** | Regras da redistribuição v1:<br>- destino compatível (produz a especialidade no SIH, com ≥ 2 AIH por mês; tem habilitação para oncologia, cardiovascular e neurologia; fila própria ≤ 1 mês);<br>- o destino recebe até +50% da sua produção na especialidade, sem passar da ociosidade estimada;<br>- a origem retém 1,5 mês de fila.<br>"Precedência": o recorte do piloto usa essa capacidade antes das outras origens | estimado | SMS/SESA (já implementado) |
| a_comp | Idem, com a capacidade **dividida** entre todas as origens | Sugestões atuais do `/redistribuicao` | estimado | — |
| b | Redistribuição na **macrorregião** / no **estado** | Mesmas regras, com destinos fora da CIR | estimado | **SESA**: muda a regra "mesma CIR" e o deslocamento dos pacientes |
| c | Vagas SUS de **privados e filantrópicos** (lado oferta do marketplace) | 10% da capacidade **não SUS** das salas: salas × 88 × (1 − fração SUS de leitos cirúrgicos) × 10%.<br>Entram hospitais gerais, especializados, hospitais-dia e unidades mistas da macrorregião. A capacidade é repartida entre as especialidades pela participação delas na produção SUS | **hipótese de mercado**: hoje há **zero** vagas confirmadas (a única declarada é do tenant de demonstração) | Contratação pela SESA/SMS, com preço e contrato |
| d | **Priorização** (reordenar) | Até 50% das saídas vão ao subgrupo prioritário (A1, judicial, oncológico) | simulado | Regulação; regras v0.1 pendentes de revisão clínica |
| e1 | **Mutirão com a ociosidade do próprio hospital** | Ociosidade estimada do estabelecimento, limitada a +50% da sua produção na especialidade | estimado | Direção do hospital |
| e2 | **Turno extra financiado** | +20% da produção mensal da especialidade, cerca de um turno de sábado por semana | **hipótese**: exige equipe e financiamento (por exemplo, programas de redução de filas) | Hospital com SESA/MS |
| f | **Saneamento** | Só contagem (seção 1.4) | — | Regulação |

### 3.3 Cenários acumulados (por recorte, com precedência do piloto)

| Cenário | Alavancas |
|---|---|
| S0 | a_comp (regra atual, capacidade dividida) |
| S1 | a |
| S2 | a + e1 |
| S3 | a + e1 + e2 (sem mudança de regra regional nem mercado) |
| S4 | S3 + b (macrorregião) |
| S5 | S4 + c (privados da macrorregião) |
| S6 | S5 com b no estado inteiro |

- **Robusto:** o mesmo cálculo, supondo que só 60% da capacidade estimada se confirma.

### 3.4 Priorização (d): o que ela faz e o que não faz

- Reordenar **não cria capacidade**. Com a mesma produção, a espera **média** não muda. O ganho dos prioritários é espera transferida aos demais: o modelo informa quantos pedidos não prioritários ficam a mais na fila (`aumento_estoque_nao_prioritarios`).
- **Estado:** com até 50% das saídas indo aos prioritários, o estoque prioritário (14.008) cairia cerca de 56% em 90 dias. Em troca, cerca de 7.900 pedidos não prioritários a mais esperariam no fim do período. Isso é **simulado**.
- **Uso no piloto:** a priorização entra como **secundária** (W dos prioritários). Não é caminho para os −40% da métrica primária. Não vale apresentar "−40% nos graves" como "−40% no tempo de espera".

## 4. Resultados: onde −40% é atingível

### 4.1 Sistema inteiro, tudo ao mesmo tempo (limite superior)

| Capacidade adicional (por mês) | Redução de W em 90 dias | Meses para −40% |
|---|---:|---:|
| Ociosidade estimada: 2.608 (≈ 15% da produção SUS sem obstetrícia, 16.787/mês) | 12,7% | 9,5 |
| + turno extra (+3.357) | 29,0% | 4,1 |
| + privados, 10% não SUS (+1.936) | 38,4% | — |
| Necessário para −40% em 90 dias | **8.231/mês** (+49% da produção) | — |

**Conclusão: não há como prometer −40% no estado em 90 dias.** É possível em cerca de 4 meses com ociosidade e turno extra **se** toda a capacidade servisse a qualquer especialidade e CIR, o que não acontece.

### 4.2 Recortes estabelecimento × especialidade (187 recortes, 56.080 pedidos)

Cada linha responde à pergunta "se este recorte fosse o piloto". Não é possível ter todos ao mesmo tempo (ver S0).

| Cenário | Atingem ≥ 40% | Robusto (60% da capacidade) | Fila nesses recortes |
|---|---:|---:|---:|
| S0 regra v1, capacidade dividida | 9 | 6 | 905 |
| S1 mesma CIR | 32 | 10 | 3.964 |
| S2 + ociosidade própria | 77 | 52 | 10.622 |
| S3 + turno extra | 106 | 65 | 16.332 |
| S4 + macrorregião | 135 | 103 | 22.831 |
| S5 + privados | 161 | 135 | 37.850 |
| S6 + estado | 165 | 151 | 39.525 |

**Capacidade adicional necessária para −40% em 90 dias**, em % da produção atual do hospital na especialidade:

| Faixa | Recortes |
|---|---:|
| ≤ 25% | 29 |
| 25–50% | 43 |
| 50–100% | 40 |
| 100–200% | 33 |
| > 200% | 39 |

- Mediana: 73%. Três recortes não têm produção no SIH.
- **Leitura:** em cerca de 40% dos recortes, a meta exige dobrar a produção por 3 meses ou mais, o que não é realista. É o caso de urologia, otorrino, bucomaxilofacial e oftalmologia em Fortaleza, e de cardiologia no hospital de referência.

**Por especialidade** (recortes que chegam a 40% em S1 / S2 / S3 / S4, de n recortes):

| Especialidade | n | Fila | S1 | S2 | S3 | S4 |
|---|---:|---:|---:|---:|---:|---:|
| Cirurgia digestiva | 40 | 11.573 | 11 | 25 | 32 | 37 |
| Ortopedia | 25 | 10.456 | 5 | 9 | 14 | 23 |
| Urologia | 19 | 7.273 | 0 | 4 | 7 | 13 |
| Ginecologia | 21 | 4.711 | 6 | 11 | 12 | 18 |
| Otorrino | 9 | 4.552 | 3 | 5 | 5 | 6 |
| Cardiovascular | 10 | 3.134 | 0 | 2 | 4 | 4 |
| Oncologia | 11 | 2.475 | 0 | 2 | 4 | 4 |
| Neurologia | 6 | 2.332 | 0 | 1 | 3 | 3 |
| Oftalmologia* | 5 | 3.434 | 0 | 0 | 1 | 1 |
| Pequenas cirurgias* | 13 | 2.106 | 3 | 5 | 7 | 9 |
| Bucomaxilofacial | 5 | 1.161 | 0 | 0 | 0 | 0 |
| Plástica reparadora | 5 | 1.107 | 1 | 2 | 2 | 2 |

\* O SIH mede mal essas especialidades, porque a cirurgia é ambulatorial (SIA/APAC). "Outras" mistura urgência e também fica fora da escolha do piloto.

### 4.3 CIR × especialidade (fila da CIR somada; 96 recortes)

| Cenário | Recortes ≥ 40% |
|---|---:|
| C1: ociosidade da própria CIR | 32 |
| C2: + turno extra | 52 |
| C3: + macrorregião | 69 |
| C4: + privados | 72 |

**Fortaleza, onde está a maior parte da fila**, nunca chega a 40% nas especialidades grandes (redução em 90 dias, C1 → C4):

| Especialidade | Fila | C1 | C4 |
|---|---:|---:|---:|
| Ortopedia | 7.795 | 11% | 35% |
| Cirurgia digestiva | 6.381 | 18% | 46% |
| Urologia | 5.945 | 5% | 13% |
| Otorrino | 4.458 | 8% | 15% |
| Cardiovascular | 2.804 | 6% | 20% |
| Neurologia | 2.104 | 20% | 29% |
| Oncologia | 1.892 | 17% | 28% |
| Ginecologia | 2.161 | 23% | 57% |

- Ginecologia só passa de 40% com privados. Cirurgia digestiva chega a 46% só em C4, também com privados.
- Maracanaú, com cirurgia digestiva (2.410) e ginecologia (1.426), fica abaixo de 20%.

**No interior, a ociosidade da própria CIR já basta** (C1 ≥ 40%) em:

| CIR | Especialidades |
|---|---|
| Juazeiro do Norte | ortopedia (456), cirurgia digestiva (316), otorrino (191), ginecologia (167) |
| Iguatu | ortopedia (449), cirurgia digestiva (174) |
| Sobral | cirurgia digestiva (419) |
| Itapipoca | cirurgia digestiva (318) |
| Acaraú | ortopedia (307) |

**Ressalva:** a fila IntegraSUS é por **estabelecimento executante** e concentra pacientes do estado todo em Fortaleza. Filas do interior são pequenas, então são "fáceis", mas menos representativas.

## 5. Recorte recomendado para o piloto

**Critérios** (aplicados no script; a lista completa está em `candidatos_piloto` no JSON):
- hospital **público**, incluindo empresas públicas como a EBSERH;
- vínculo nome→CNES de alta confiança;
- fila do recorte entre 100 e 2.500;
- ≥ 15 entradas por mês, para medir a cada quinzena;
- especialidade comparável ao SIH;
- ≥ 40% no cenário **robusto** S3, sem mudança de regra regional e sem mercado privado.

Resultado: **11 recortes candidatos.** Em 8 deles, a meta robusta vem **só das alavancas do PREDMED** (a + e1, cenário S2 ou S1).

| Recorte (hospital × especialidade) | CIR | Fila | W (d)† | Extra p/ 40% (mês) | a | e1 | e2 | S2 | S2 robusto | S3 robusto |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hosp. Mun. Dr José Evangelista de Oliveira × cir. digestiva | Sobral | 116 | 120 | 15 | 31 | 0 | 3 | 79% | 48% | 53% |
| Hospital da Polícia Militar × cir. digestiva | Fortaleza | 380 | 222 | 51 | 23 | 62 | 25 | 67% | 40% | 52% |
| Hospital Universitário do Ceará (HUC) × ortopedia | Fortaleza | 334 | 195 | 45 | 64 | 47 | 19 | 99% | 60% | 70% |
| Hosp. e Mat. Dra Zilda Arns × ginecologia | Fortaleza | 272 | 85 | 36 | 28 | 43 | 18 | 78% | 47% | 59% |
| Maternidade Escola Assis Chateaubriand × ginecologia | Fortaleza | 255 | 90 | 34 | 28 | 37 | 15 | 77% | 46% | 57% |
| Hosp. e Mat. Dra Zilda Arns × cir. digestiva | Fortaleza | 169 | 89 | 23 | 23 | 22 | 9 | 80% | 48% | 58% |
| HUC × ginecologia | Fortaleza | 161 | 141 | 22 | 28 | 10 | 4 | 71% | 43% | 47% |
| Hosp. Mun. Dr João Elísio de Holanda × cir. digestiva | Maracanaú | 118 | 118 | 16 | 0 | 29 | 16 | 74% | 44% | 68% |
| Hospital Regional de Itapipoca × cir. digestiva | Itapipoca | 275 | 57 | 37 | 36 | 18 | 10 | 59% | 35% | 42% |
| Hospital Regional Vale do Jaguaribe × ortopedia | Limoeiro do Norte | 132 | 60 | 18 | 0 | 0 | 36 | 0% | 0% | 49% |
| Hosp. Mun. Dr João Elísio de Holanda × ginecologia | Maracanaú | 121 | 178 | 16 | 6 | 16 | 6 | 55% | 33% | 42% |

† W de Little, limite superior. Todas as capacidades estão em pacientes por mês e são **estimadas**. Os percentuais são **simulados**.

**Recomendação** (a escolha final depende das entrevistas, do termo de cooperação e da confirmação de capacidade pelo hospital):
1. **Um hospital público de Fortaleza com duas especialidades pré-registradas.** Os perfis HUC (ortopedia e ginecologia) e Zilda Arns (ginecologia e cirurgia digestiva) atingem 40% no cenário robusto com as alavancas a + e1.
   - Duas especialidades no mesmo hospital dão uma segunda chance sem trocar o recorte depois.
   - O sucesso é declarado **por especialidade**.
2. **Confirmar a ociosidade antes do pré-registro** (vagas declaradas pelo hospital e pelos destinos da CIR). Se a capacidade confirmada for menor que o "extra p/ 40%", o recorte **sai** da lista antes do início, e não depois.
3. **Grupo de comparação pré-registrado:** 3 a 5 recortes da mesma especialidade, em hospitais públicos parecidos, sem intervenção.
4. **Evitar como piloto principal:**
   - filas grandes de referência (ortopedia, urologia e otorrino do hospital geral estadual; cardiologia do hospital cardiológico), que exigem de +50% (cardiologia) a mais de +1.000% (otorrino) da produção atual;
   - oftalmologia;
   - oncologia, que já tem espera curta na fila (W ≈ 95 dias) e cujos ganhos devem ser medidos pela priorização, e não pela meta de −40%.

## 6. Protocolo de medição do piloto (pré-registro)

| Item | Definição |
|---|---|
| Recorte | 1 hospital público × 1 ou 2 especialidades, com CNES e nomes da fila listados. Grupo de comparação: 3 a 5 recortes semelhantes. Tudo definido **antes** do início |
| Período | 90 dias corridos (M7–M9, mar–mai/2027). Data de início fixada no pré-registro |
| Linha de base | Coletas IntegraSUS de 28/09/2026 até a véspera do início (cerca de 20 semanas).<br>- `L*_base`: média dos 7 dias anteriores ao início.<br>- `λ_ref`: entradas por mês no período, sem 20/12 a 10/01.<br>- Variação natural: distribuição das variações de `L` em 90 dias nos recortes de comparação e nos demais recortes com tamanho parecido (teste placebo) |
| Métrica primária | `R = 1 − W_fim/W_base`, com `W = L*/λ_ref` (Lei de Little) e fila saneada nas duas pontas (seção 1.1) |
| Secundárias | Seção 1.2. Todas relatadas, inclusive se desfavoráveis |
| Frequência | Quinzenal (6 medições), com `L` como média móvel de 7 dias. Relatório quinzenal só com agregados |
| Fontes | Coletas IntegraSUS automáticas (entradas, saídas, estoque, `data`).<br>O hospital informa, por quinzena, **contagens** de saídas por motivo (realizada, transferida e realizada, cancelada, óbito, saneamento).<br>As transferências aprovadas vêm do PREDMED (`transferencias`).<br>A conferência com o SIH por CNES é feita quando as competências fecharem (cerca de 60 dias depois) |
| Sucesso (meta −40%) | Todas as condições abaixo, na medição do dia 90:<br>1. R ≥ 40%;<br>2. a mediana da idade do estoque cai;<br>3. `λ` observado ≥ 85% de `λ_ref` (sem "fechar a porta");<br>4. ≥ 90% das saídas com motivo informado, e as saídas "realizada" + "transferida e realizada" acima da taxa da linha de base explicam ≥ 90% da queda de `L*`;<br>5. o W da mesma especialidade na CIR, sem o piloto, não piora mais de 10% |
| Sucesso (KPI "redução mensurável") | R acima do percentil 95 da variação natural (placebo), mesmo que abaixo de 40%. Nesse caso, relata-se "redução de Y%, meta de 40% não atingida" |
| Atribuição | Relata-se `R_piloto` e `R_comparação` lado a lado. O efeito atribuível é a diferença. Relata-se também a parte da capacidade extra que veio de recomendações do PREDMED (transferências aprovadas e ociosidade identificada) |
| Seguimento | Medição em 180 dias, para ver se o efeito se sustenta (secundária) |
| Dados | Só agregados em relatórios. Os snapshots ficam criptografados. O hospital envia contagens, e não listas de pacientes |

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| **Sazonalidade.** Dez–fev tem menos entradas e menos produção, e a linha de base termina aí | `λ_ref` sem as festas; comparação com recortes paralelos; placebo |
| **Regressão à média.** Um recorte escolhido por estar "no pico" tende a cair sozinho | Escolher por viabilidade de capacidade, e não por pico; `L*_base` como média de 7 dias; grupo de comparação |
| **Mudança de política.** Mutirões estaduais ou federais, saneamento em massa pela regulação, mudança de fluxo do portal | Registrar datas; o saneamento sai das duas pontas; a comparação absorve efeitos gerais; se o portal mudar de formato, a coleta falha e o evento é registrado |
| **A capacidade estimada não se confirma** | Confirmação prévia; cenário robusto (60%) como critério de escolha |
| **Deslocamento.** A fila vai para o destino ou para outro hospital | Trava 5 (W da CIR sem o piloto) |
| **Significado do campo `data`** não documentado pela SESA | Confirmar por ofício antes do pré-registro |
| **Efeito Hawthorne** (a equipe muda porque está sendo medida) | O ganho é real, mas pode não persistir: seguimento de 180 dias |

## 7. Limitações

- **Capacidade estimada ≠ disponibilidade** (agenda, equipe, anestesia, órtese e prótese). Por isso a versão robusta e a confirmação prévia.
- **O modelo é determinístico e de fila estável.** Não trata a variabilidade semanal nem o descasamento de procedimento dentro da especialidade. O mapeamento SIGTAP → especialidade é hipótese (ver `previsao-demanda-v1.md`, seção 3).
- **`λ` vem dos pedidos recentes que continuam na fila** (limite inferior). Com mais coletas, passa a ser medido por diferença entre coletas. As 2 coletas atuais não bastam para medir fluxo.
- **"Precedência do piloto"** superestima o que cada recorte teria se todos disputassem a mesma capacidade (S0). Os mapas por recorte não podem ser somados.
- **A alavanca c (privados)** é hipótese de mercado (10% da capacidade não SUS); ela sozinha move muitos recortes para "atingível". Não deve ser usada para escolher o piloto enquanto não houver vagas confirmadas.
- **Achado lateral:**
  - A redistribuição v1 classifica empresas públicas (natureza jurídica 2011, por exemplo EBSERH/HUWC e MEAC) como "particular", porque o campo `natureza` do CNES as agrupa em PRIVADO.
  - Este módulo corrige isso só para seus próprios relatórios (`tipo_ajustado`).
  - Convém corrigir `redistribuicao._tipo` numa próxima rodada.

## 8. Como reproduzir

```bash
backend/venv/bin/python backend/_SCRIPTS/cenarios_meta_40.py        # ~2 s; lê predmed.db em modo leitura
cd backend && APP_ENV=dev venv/bin/python -m pytest -q tests/test_cenarios_meta40.py
```

- **Saídas:** `backend/avaliacoes/meta40/cenarios_AAAAMMDD.json` e `mapa_recortes_AAAAMMDD.csv`. Contêm só agregados; nomes de estabelecimentos são dados institucionais.
- **Parâmetros:** estão em `cenarios_meta40.PARAMS` e voltam no JSON (`metodologia.parametros`).
- **Endpoint:** `GET /meta40/cenarios?cir=&especialidade=` (SESA ou SMS; a SMS fica restrita à própria CIR) devolve o JSON mais recente, com `natureza = "simulado"`. O frontend não foi alterado.
