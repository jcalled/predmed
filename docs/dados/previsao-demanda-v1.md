# Previsão de demanda v1: produção cirúrgica mensal SUS no Ceará

Versão: 29/09/2026. Avaliação versionada: `backend/avaliacoes/previsao_demanda/avaliacao_20260929.json`, com `avaliacao_id = previsao-demanda-v1-20260929`.
Funcionalidade 1 do plano (meta: MAPE < 15% em 30–90 dias). Itens E1.4 e E2.1 do checklist.

**Resumo.** A avaliação foi fora da amostra: cada modelo é treinado só com meses anteriores à previsão e testado de 2025-07 a 2026-06.
- **Total cirúrgico sem obstetrícia:** MAPE de **5,1% em 30 dias, 5,3% em 60 dias e 6,2% em 90 dias**, com Holt-Winters. O sazonal ingênuo erra 12,3%.
- **Especialidades, todas as internações:** a meta é atingida em 13 de 15 especialidades em 30 dias e em 9 de 15 em 90 dias.
- **Especialidades, só cirurgias eletivas:** a meta é atingida em 9 de 15 em 30 dias e em 8 de 15 em 90 dias.
- **Onde a meta falha:** oftalmologia, bucomaxilofacial, neurologia eletiva, cardiovascular eletiva e pequenas cirurgias eletivas.
- **Ressalva:** o alvo é a **produção cirúrgica registrada no SIH**, e não a entrada nem o estoque da fila. Um bom resultado aqui **não comprova** a previsão da fila.

## 1. Alvo

| Item | Definição |
|---|---|
| Variável prevista | Nº de AIH **principais** (`IDENT = 1`) pagas com procedimento realizado (`PROC_REA`) do **grupo SIGTAP 04 — procedimentos cirúrgicos** |
| Unidade temporal | Mês de **competência de processamento** (`ANO_CMPT/MES_CMPT`), não data de internação |
| Recortes | Especialidade da fila (seção 3) × caráter: `TODOS` (principal) e `ELETIVO` (`CAR_INT = 01`, mais próximo da saída da fila eletiva) |
| Agregados | `TOTAL` (todo o grupo 04) e `TOTAL_SEM_OBSTETRICIA` (escopo comparável à fila: parto cesáreo não entra na fila) |
| Horizontes | 1, 2 e 3 meses (≈ 30, 60 e 90 dias) e o total do trimestre seguinte |
| Geografia | Ceará inteiro (arquivo RDCE, estabelecimentos do CE). Recorte por CIR/hospital: pendente (seção 7) |

**Alternativas descartadas nesta versão:**
- *Novas entradas na fila* e *estoque da fila* não têm histórico: a coleta automática do IntegraSUS começou em 09/2026, e o `serie_historica` antigo é sintético (`entradas = 1,3 × saídas`).
- A produção cirúrgica é a oferta que esvazia a fila. É o único alvo com 7 anos de histórico observado.

## 2. Fontes e preparação

| Fonte | Competências | Uso |
|---|---|---|
| `backend/data/sih/RDCEaamm.dbc` (DATASUS SIH-RD) | 2019-01 → 2024-12 (72 arquivos) | série |
| `~/PredmedDados/datasus/sih/RD/RDCEaamm.dbc` (`coleta_datasus.py`) | 2025-01 → 2026-06 (18 arquivos; 2026-07 existe mas foi excluída) | série |
| `backend/predmed-original.db` (aberto com `mode=ro`) | 2019-01 → 2024-12 | **conferência**: nas 72 competências, a contagem do grupo 04 nos `.dbc` é igual à de `aih_registro` (1.277.980 linhas, diferença 0) |

O `predmed-original.db` não tem `CAR_INT` nem `IDENT`. Por isso a série é lida dos `.dbc`, que são os mesmos arquivos que geraram o banco.

**Script:** `backend/_SCRIPTS/serie_producao_cirurgica.py`.
- Tem cache de agregados por arquivo, conferido por sha256, em `~/PredmedDados/datasus/processado/cache_sih_agregado/`.
- Grava `~/PredmedDados/datasus/processado/serie_producao_cirurgica.csv` e a tabela `serie_producao_cirurgica` do `predmed.db` (90 competências × 17 séries × 3 caráteres).
- Guarda **só contagens e valores mensais**. Nenhum dado individual sai do `.dbc`.
- A 1ª execução leva cerca de 7 minutos; as seguintes usam o cache.

**Qualidade e cobertura:**
- **Linhas e competência:** 1.662.048 AIHs do grupo 04 com IDENT 1 entre 2019-01 e 2026-06. Nenhuma competência falta. Em todos os arquivos, 100% dos registros estão na competência esperada (ver `datasus-cnes-sih.md`).
- **Competências provisórias:** 2026-05 e 2026-06 estão marcadas `provisoria = 1`. O DATASUS republicou 2025-08 a 2026-07 em 07/09/2026, e as últimas competências ainda podem receber AIHs apresentadas com atraso. A 2026-07 foi excluída porque tem 202 estabelecimentos, contra uma média de ~230.
- **Zeros:** a série é regular, com zeros explícitos quando uma combinação não aparece. O MAPE ignora meses com valor real 0 e informa `n_real_zero`. O sMAPE e o MAE usam todos os meses.
- **Pandemia (2020-03 a 2021-12):** em 2020, a produção caiu 13% no total do grupo 04, 17% sem obstetrícia e 36% em ginecologia, em relação a 2019. Foram testadas duas variantes, e a escolha é feita pela validação:
  - `pos2022`: treina a partir de 2022-01;
  - `imputada`: troca cada mês da pandemia pela média do mesmo mês de 2019 e 2022. Nenhuma origem avaliada é anterior a 2023-12, então não há vazamento.

## 3. Mapeamento SIGTAP → especialidade da fila

Hipótese inicial; precisa ser revisada com a regulação (SESA). Código em `SUBGRUPO_PARA_ESPECIALIDADE`.

| SIGTAP (grupo 04) | Série | Observação |
|---|---|---|
| 0401 pele/subcutâneo/mucosa | PEQUENAS CIRURGIAS | |
| 0402 glândulas endócrinas | ENDOCRINOLOGIA | tireoide/paratireoide |
| 0403 sistema nervoso | NEUROLOGIA | neurocirurgia |
| 0404 vias aéreas superiores, face, cabeça e pescoço | OTORRINO | a fila tem "OTORRINO MÉDIA COMPLEXIDADE" e "OTORRINO E PNEUMOLOGIA", que foram somadas |
| 0405 aparelho da visão | OFTALMOLOGIA | **a maior parte da cirurgia oftalmológica eletiva (catarata) é ambulatorial (SIA/APAC)**, fora do SIH |
| 0406 aparelho circulatório | CARDIOVASCULAR | |
| 0407 aparelho digestivo e parede abdominal | CIR DIGESTIVA | |
| 0408 sistema osteomuscular | ORTOPEDIA | |
| 040901–040905 rim, bexiga, uretra, próstata, testículo, pênis | UROLOGIA | |
| 040906–040907 útero/anexos, vagina/vulva/períneo; 0410 mama | GINECOLOGIA | mama → ginecologia é hipótese (pode ser mastologia/oncologia) |
| 0411 obstétrica | OBSTETRICIA | fora da fila; fica fora de `TOTAL_SEM_OBSTETRICIA` |
| 0413 reparadora | CIR PLASTICA REPARADORA | |
| 0414 bucomaxilofacial | BUCO MAXILO-FACIAL | |
| 0416 cirurgia em oncologia | ONCOLOGIA | cirurgias oncológicas fora do 0416 ficam na especialidade do órgão |
| 0412 torácica, 0415 múltiplas/politrauma/sequenciais, 0417, 0418 | OUTRAS | 0415 é grande e majoritariamente de urgência |

## 4. Modelos comparados

Código em `backend/services/previsao_avaliacao.py`.

| Modelo | Tipo | Descrição |
|---|---|---|
| `naive_ultimo` | baseline | repete o último mês |
| `naive_sazonal` | baseline | mesmo mês do ano anterior |
| `naive_sazonal_nivel` | baseline | sazonal ingênuo × razão entre os últimos 3 meses e os mesmos 3 meses do ano anterior |
| `holt_winters_pos2022` / `_imputada` | ETS | **mesma configuração do Holt-Winters atual do PREDMED**: tendência aditiva, sazonalidade multiplicativa com 24 meses ou mais |
| `sarima_pos2022` / `_imputada` | SARIMA | (0,1,1)(0,1,1)12 "airline" em log(1+y) |
| `prophet_imputada` | Prophet 1.3 | sazonalidade anual multiplicativa. **Prophet de fato**: a função antiga `treinar_prophet` era Holt-Winters e já foi renomeada para `treinar_holt_winters` |

XGBoost não está instalado no `backend/venv` e não foi instalado.

## 5. Desenho da avaliação (sem vazamento temporal)

**Script:** `backend/_SCRIPTS/avaliar_previsao_demanda.py`, cerca de 1 minuto com 6 processos.

1. **Origem móvel:** em cada mês de 2023-12 a 2026-05, cada modelo é treinado só com competências até esse mês e prevê os 3 meses seguintes.
2. **Janela de validação** (alvos 2024-01 a 2025-06): **escolhe** o modelo de cada série pelo menor MAPE médio entre 30, 60 e 90 dias.
3. **Janela de teste** (alvos 2025-07 a 2026-06): **só reporta** o erro do modelo escolhido. O `melhor_no_teste_informativo` do JSON é otimista e não deve ser citado como resultado.
4. **Conferência com origem fixa:** treino até 2025-06 e previsão dos 12 meses seguintes.
5. **Métricas:** MAPE, sMAPE e MAE por série, modelo e horizonte, mais o erro do total trimestral.

## 6. Resultados (janela de teste 2025-07 a 2026-06; MAPE %, **negrito = abaixo de 15%**)

### 6.1 Todas as internações cirúrgicas (`carater = TODOS`)

| Série | Média/mês 2025 | Modelo escolhido | 30 d | 60 d | 90 d | Trimestre | Sazonal ingênuo 30 d | Ingênuo último 30 d |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| TOTAL | 20729 | sarima_imputada | **3,8** | **3,8** | **4,6** | **3,3** | **10,0** | **6,0** |
| TOTAL_SEM_OBSTETRICIA | 15269 | holt_winters_imputada | **5,1** | **5,3** | **6,2** | **4,7** | **12,3** | **6,8** |
| OBSTETRICIA | 5460 | prophet_imputada | **3,5** | **3,5** | **3,3** | **2,2** | **4,4** | **5,4** |
| OUTRAS | 3490 | holt_winters_imputada | **6,7** | **7,1** | **9,5** | **7,7** | 21,5 | **7,6** |
| CIR DIGESTIVA | 3291 | holt_winters_imputada | **5,8** | **7,3** | **7,5** | **5,7** | **11,6** | **7,2** |
| ORTOPEDIA | 3100 | holt_winters_imputada | **5,7** | **6,6** | **7,1** | **5,7** | **6,7** | **5,6** |
| GINECOLOGIA | 1478 | sarima_imputada | **8,9** | **8,7** | **9,7** | **6,8** | **8,5** | **10,1** |
| CARDIOVASCULAR | 1022 | naive_ultimo | **7,1** | **8,6** | **9,2** | **6,0** | **12,8** | **7,1** |
| UROLOGIA | 725 | naive_ultimo | **7,1** | **10,3** | **14,0** | **8,4** | 19,2 | **7,1** |
| PEQUENAS CIRURGIAS | 520 | naive_sazonal_nivel | **13,1** | **13,7** | **14,3** | **9,7** | 19,7 | **14,2** |
| ONCOLOGIA | 445 | naive_ultimo | **12,1** | **14,1** | 17,1 | **12,2** | 29,0 | **12,1** |
| OTORRINO | 412 | naive_ultimo | **13,1** | 15,8 | 19,5 | **10,7** | 16,2 | **13,1** |
| NEUROLOGIA | 389 | holt_winters_imputada | **13,9** | 15,1 | 15,2 | **11,4** | 24,1 | **12,0** |
| CIR PLASTICA REPARADORA | 235 | naive_ultimo | **7,3** | **5,1** | **7,7** | **6,0** | **9,4** | **7,3** |
| OFTALMOLOGIA | 80 | prophet_imputada | 20,2 | 20,5 | 20,7 | 15,7 | 58,3 | 27,1 |
| ENDOCRINOLOGIA | 68 | sarima_imputada | **12,1** | **13,8** | 16,1 | **12,6** | 19,9 | **8,8** |
| BUCO MAXILO-FACIAL (baixo volume) | 13 | holt_winters_imputada | 23,2 | 23,4 | 23,3 | 22,9 | 27,9 | 23,4 |

### 6.2 Só cirurgias eletivas (`carater = ELETIVO`, `CAR_INT = 01`)

| Série | Média/mês 2025 | Modelo escolhido | 30 d | 60 d | 90 d | Trimestre | Sazonal ingênuo 30 d | Ingênuo último 30 d |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| TOTAL | 8609 | holt_winters_imputada | **7,6** | **7,8** | **9,6** | **8,2** | 20,0 | **8,0** |
| TOTAL_SEM_OBSTETRICIA | 7917 | holt_winters_imputada | **8,1** | **8,8** | **10,9** | **8,9** | 20,9 | **8,4** |
| CIR DIGESTIVA | 2281 | holt_winters_imputada | **7,0** | **8,9** | **9,6** | **8,1** | **14,1** | **8,9** |
| OUTRAS | 1372 | holt_winters_imputada | **9,1** | **10,6** | **12,6** | **11,1** | 26,1 | **9,4** |
| GINECOLOGIA | 1182 | sarima_imputada | **11,4** | **11,8** | **13,1** | **9,4** | **10,4** | **12,5** |
| ORTOPEDIA | 906 | naive_ultimo | **11,1** | **12,7** | 15,6 | **10,7** | 35,9 | **11,1** |
| OBSTETRICIA | 692 | naive_sazonal | **14,2** | **14,2** | **14,2** | **11,8** | **14,2** | **8,5** |
| UROLOGIA | 548 | naive_ultimo | **9,1** | **9,4** | **13,3** | **8,1** | 21,2 | **9,1** |
| ONCOLOGIA | 414 | naive_ultimo | **12,3** | **14,5** | 17,5 | **12,6** | 32,5 | **12,3** |
| PEQUENAS CIRURGIAS | 379 | holt_winters_imputada | 15,5 | 15,4 | 16,4 | **13,6** | 33,1 | 16,2 |
| OTORRINO | 300 | prophet_imputada | **11,9** | **11,8** | **11,8** | **7,2** | 19,7 | 16,3 |
| CARDIOVASCULAR | 205 | holt_winters_imputada | 16,9 | 19,9 | 25,0 | 19,3 | 22,9 | 16,1 |
| NEUROLOGIA | 121 | naive_ultimo | 21,4 | 26,8 | 28,3 | 23,7 | 51,6 | 21,4 |
| OFTALMOLOGIA | 69 | prophet_imputada | 23,7 | 23,9 | 24,3 | 15,1 | 60,9 | 32,2 |
| CIR PLASTICA REPARADORA | 64 | naive_ultimo | 19,8 | **12,4** | **14,3** | **11,8** | 25,0 | 19,8 |
| ENDOCRINOLOGIA | 64 | sarima_imputada | **11,8** | **12,9** | **14,6** | **11,1** | 20,1 | **9,7** |
| BUCO MAXILO-FACIAL (baixo volume) | 11 | holt_winters_pos2022 | 27,4 | 26,6 | 27,9 | 20,9 | 28,6 | 29,7 |

### 6.3 Comparação entre modelos (MAPE mediano das 15 especialidades com volume, teste)

| Modelo | TODOS 30/60/90 d | ELETIVO 30/60/90 d |
|---|---|---|
| naive_ultimo | 8,2 / 9,7 / 12,8 | 12,4 / 13,4 / 16,5 |
| naive_sazonal | 17,7 / 17,7 / 17,7 | 23,9 / 23,9 / 23,9 |
| naive_sazonal_nivel | 11,8 / 14,1 / 15,0 | 15,7 / 17,8 / 19,8 |
| holt_winters_pos2022 | 7,9 / 8,1 / 10,9 | 12,9 / 14,0 / 15,1 |
| holt_winters_imputada | 8,6 / 9,1 / 9,7 | 12,6 / 13,4 / 14,2 |
| sarima_pos2022 | 8,7 / 9,4 / 11,1 | 13,3 / 14,4 / 14,2 |
| sarima_imputada | 8,7 / 9,8 / 10,8 | 13,8 / 14,1 / 15,1 |
| prophet_imputada | 10,4 / 11,0 / 11,4 | 18,2 / 19,4 / 20,4 |

### 6.4 Conferência com origem fixa (treino até 2025-06, previsão de 12 meses)

- **TOTAL_SEM_OBSTETRICIA, todas as internações:**
  - Holt-Winters escolhido (`imputada`): MAPE de 10,6% nos 12 meses e 5,2% nos 3 primeiros; a variante `pos2022` erra 8,9% nos 12 meses;
  - Prophet: 6,5%;
  - sazonal ingênuo: 12,3%.
- **Só eletivas:** o erro de 12 meses fica entre 12% e 20%, porque a produção eletiva cresceu em 2026 e nenhum modelo antecipou.

### 6.5 Leitura

1. **Onde a meta é atingida:**
   - total estadual e total sem obstetrícia, nos três horizontes e nos dois caráteres;
   - todas as internações: cirurgia digestiva, ortopedia, ginecologia, cardiovascular, urologia, plástica reparadora e "outras", nos três horizontes;
   - só eletivas: cirurgia digestiva, ginecologia e urologia, nos três horizontes.
2. **Onde falha:**
   - oftalmologia (20–24%): o SIH mede mal a oftalmologia, porque a cirurgia é ambulatorial;
   - bucomaxilofacial: ~12 AIHs por mês;
   - neurologia eletiva (21–28%) e cardiovascular eletiva (17–25%): séries pequenas e em mudança de patamar;
   - pequenas cirurgias eletivas: 15–16%;
   - 90 dias em oncologia, otorrino, endocrinologia e ortopedia eletiva: 15–20%.
3. **O ganho sobre o baseline "repetir o último mês" é pequeno em 30 dias:** 6,8% contra 5,1% no total, e medianas próximas entre as especialidades. A vantagem dos modelos aparece em 90 dias e no trimestre. Em várias especialidades a validação escolheu o próprio `naive_ultimo`: aí o "modelo" é o baseline, e o relatório diz isso.
4. **O Holt-Winters atual** fica entre os melhores, com a pandemia tratada. O SARIMA é equivalente. O Prophet só é melhor na origem fixa de 12 meses e em algumas séries, e é o pior na mediana em horizonte curto.

## 7. Limitações e próximos passos

- **O alvo não é a fila.** A meta do plano ("cirurgias por especialidade") foi medida como produção SIH. Prever entradas e estoque da fila exige os snapshots do IntegraSUS acumulados desde 09/2026, com ao menos 12–24 meses para sazonalidade.
- **Competência de processamento** não é a data da cirurgia: reapresentações e glosas deslocam volume entre meses. As 2 últimas competências são provisórias e podem mudar.
- **Mapeamento SIGTAP → especialidade** é hipótese: mama → ginecologia, torácica → outras e a oncologia fora do 0416. Precisa ser revisado com a SESA.
- **Oftalmologia e parte das pequenas cirurgias** exigem o SIA/APAC (produção ambulatorial). O próximo passo é incluir o SIA-PA do CE.
- **Recorte geográfico:** a série é estadual. Por CIR ou hospital, as séries ficam pequenas e o MAPE tende a passar de 15%. O próximo passo é avaliar por macrorregião e pelos 20 hospitais de maior volume, com o mesmo script.
- **Mudança de política**, como mutirões e o Programa Nacional de Redução de Filas, não é antecipada. O crescimento eletivo de 2026 aumentou o erro na origem fixa.
- Seleção por série com 8 candidatos numa janela de validação de 18 meses: há risco de sobreajuste na escolha, mitigado pelo teste separado.

## 8. Como reproduzir e onde a tela lê

```bash
backend/venv/bin/python backend/_SCRIPTS/serie_producao_cirurgica.py       # série (cache), grava CSV + tabela
backend/venv/bin/python backend/_SCRIPTS/avaliar_previsao_demanda.py       # nova avaliacao_AAAAMMDD.json
backend/venv/bin/python -m pytest backend/tests/test_previsao_avaliacao.py
```

Como a API e as telas usam a avaliação:
- **Endpoint:** `GET /analytics/validacao-mape?especialidade=...&carater=TODOS|ELETIVO` devolve a **avaliação versionada mais recente**, o último `avaliacao_*.json`.
- **Campos antigos:** `mape_real` é o MAPE de 30 dias, e `comparacao_mensal` traz as previsões de 1 mês à frente na janela de teste.
- **Campos novos:** `avaliacao_id`, `modelo`, `mape_por_horizonte`, `baseline_sazonal_teste`, `atinge_meta_por_horizonte`, `serie_avaliada`, `baixo_volume`, `desenho_avaliacao` e `competencias_provisorias`.
- **Especialidades:** `TOTAL` corresponde a `TOTAL_SEM_OBSTETRICIA`, e as duas especialidades de otorrino da fila correspondem a `OTORRINO`.
- **Parâmetro `meses`:** é ignorado quando há avaliação versionada. Sem avaliação, a API volta ao cálculo antigo.

## 9. Previsão operacional na tela (29/09/2026)

**Script:** `backend/_SCRIPTS/prever_producao_cirurgica.py` gera `backend/avaliacoes/previsao_demanda/previsao_producao_AAAAMMDD.json` (`previsao_id = previsao-producao-v1-20260929`, com referência ao `avaliacao_id`).

**Como a previsão é feita:**
- **Série:** é a mesma da avaliação; o sha256 do CSV é conferido e, se divergir, o script aborta.
- **Modelo:** em cada série (especialidade × caráter) é o `modelo_escolhido` na validação, treinado com todas as competências até 2026-06.
- **Horizontes:** prevê 2026-07, 2026-08 e 2026-09 (h1–h3 ≈ 30/60/90 dias contados da última competência consolidada).
- **Intervalo de 80%, empírico:**
  - o modelo escolhido roda de novo com origem móvel, só sobre os alvos da janela de teste (n = 12 por horizonte);
  - o intervalo é previsão × quantis 10% e 90% da razão real/previsto;
  - os limites nunca excluem a própria previsão.
- **Onde o limite inferior coincide com a previsão:** acontece em algumas séries (por exemplo, total sem obstetrícia em 60 e 90 dias). Nessas séries o modelo subestimou a produção em quase todo o teste, por causa do crescimento de 2026.
- **Conferência de reprodutibilidade:** o MAPE recalculado nesse backtest é **igual** ao da avaliação versionada nas 34 séries.

**API e tela:**
- **Endpoints:** `GET /previsoes/producao?especialidade=&carater=TODOS|ELETIVO` e `GET /previsoes/producao/resumo`. Ambos devolvem `natureza = "estimado"`, o MAPE do teste por horizonte e o `avaliacao_id`.
- **Aba "Previsão":** mostra a previsão com o selo "Estimado", o intervalo e o MAPE medido ao lado, com o aviso de que o alvo é a produção cirúrgica, e não a fila.
- **Telas antigas:** as projeções sobre a série sintética da fila (regressão linear e Holt-Winters) saíram da tela. Os endpoints `/previsoes` e `/previsoes/ml` continuam, rotulados como simulados.
- **Aba "Validação":** mostra os horizontes 30/60/90 dias (`mape_por_horizonte`), o caráter (todas ou só eletivas) e o `avaliacao_id`.
