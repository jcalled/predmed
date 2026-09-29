# Nota técnica — Fonte IntegraSUS e tempo de espera na fila cirúrgica

**Itens:** B17 (Sprint 2) e base para B35 · **Autor:** cientista de dados (agente) · **Data:** 28/09/2026
**Status:** versão 1. As seções marcam o que foi **verificado** (consultado diretamente) e o que é **inferido** ou **não verificado**.
**Script de apoio:** `backend/_SCRIPTS/analise_snapshots_integrasus.py`. Ele só lê os arquivos e imprime apenas agregados.

> Regra de privacidade: esta nota traz somente contagens e estatísticas. Não inclui iniciais, números de solicitação nem linhas de pacientes.

---

## 1. Resumo executivo

| Pergunta | Resposta |
|---|---|
| Existe API pública documentada para a fila cirúrgica? | **Não.** Não há API documentada nem dataset aberto da fila. O portal é uma aplicação Angular com backend REST próprio (`/api/`, `/api-adm/`), sem documentação ou termos de uso para consumo por terceiros. Verificado. |
| O painel público traz data de entrada na fila? | **Não.** O painel público "Consulta da Fila de Espera" (id 214) oferece filtros de município, procedimento, especialidade e unidade, sem data. O CSV exportado tem 9 colunas e nenhuma é data. Verificado. |
| A fonte tem a data? | **Tem, mas em painel restrito.** O painel "Fila de Cirurgias Eletivas" (id 232, **privado**, base Fastmedic) filtra por "competência da fila (data de início e ano que saiu da fila)". Logo, a SESA tem a data. Verificado pela descrição pública do painel; o conteúdo não foi acessado. |
| Frequência de atualização | Painel 214: "diário de hora em hora". Última execução do job observada em 28/09/2026, 18:48 UTC. Verificado. |
| Tempo de espera hoje | **Não pode ser medido** com os dados que o projeto tem. O parâmetro atual (`ESPERA_MEDIA_ESP` e 5,2 meses) é fixo e não validado. A `serie_historica` é sintética. |
| Proxy disponível | O **nº de solicitação** é estável, sequencial por série e, dentro de cada fila (unidade × procedimento × SWALIS), ordena a posição quase perfeitamente (Spearman mediano 1,00). Serve como **ordem de antiguidade**. Não serve como data sem calibração. |
| Recomendação | (1) Começar **já** a coleta horária ou diária de snapshots (histórico perdido não se recupera). (2) Pedir formalmente à SESA acesso ao campo de data (painel 232 ou extração Fastmedic). (3) Calibrar o nº de solicitação para estimar a idade do estoque antigo. (4) No piloto, usar a data do hospital por termo de cooperação. |

---

## 2. Fontes verificadas

### 2.1 Portal IntegraSUS (integrasus.saude.ce.gov.br)

| Item | O que foi verificado (28/09/2026) |
|---|---|
| Arquitetura | SPA Angular. A configuração embutida no bundle público indica `apiUrl: "/api/"`, `apiUrlAdmin: "/api-adm/"`, `authUrl: "/api/oauth/token"` e `apiDataSets: "https://datasets-integrasus.saude.ce.gov.br/datasets/"`. |
| Catálogo de painéis | `GET https://integrasus.saude.ce.gov.br/api-adm/dashboard-area/` responde JSON público com **217 painéis**, cada um com título, rota, fonte, flag `privado`, job e data da última atualização. |
| Painel 214 — Consulta da Fila de Espera | Público. Rota `indicadores-regulacao/consulta-fila-espera`. Fonte "Saúde Digital / Base fria – Fastmedic". Atualização "diário de hora em hora". Filtros: município, procedimento, especialidade (as mesmas 15 do nosso CSV), unidade. **Não tem filtro nem campo de data.** O CSV do projeto (`consulta-fila-espera_*.csv`) segue o padrão de nome da função "Baixar Dados" do portal (inferido pelo código do front; o download não foi reexecutado). |
| Painel 259 — Consulta da Fila de Espera – Município | **Privado.** |
| Painel 232 — Fila de Cirurgias Eletivas | **Privado.** Fonte "Base fria – Fastmedic". Atualização diária às 6h30. Filtro "ano competência da fila", ou seja, data de início e de saída, além de rede (SESA/SMS) e dados de residência. **É a fonte natural do tempo de espera.** |
| Painel 211 — Programa de Redução da Fila de Cirurgias Eletivas | Público. Atualização a cada 2 h. Trata de **cirurgias realizadas** (filtra pela data da alta), não do estoque. Útil para a previsão de produção, não para medir espera. |
| Painéis 274 e 268 — Indicadores Ambulatoriais (fila e tempo de espera) | Públicos, com filtro "data do cadastro" e indicador de tempo de espera. São **ambulatoriais** (consultas e exames), não cirúrgicos. Mostram que o Fastmedic guarda a data de cadastro e que a SESA já publica tempo de espera para outra fila. |
| Painel 80 — Cirurgia eletiva judicializada | Privado e **inativo** desde 2021. |
| Portal de datasets | `https://datasets-integrasus.saude.ce.gov.br/datasets/` lista 15 datasets (covid, monkeypox, relatórios de vigilância, nascidos, mortalidade). **Nenhum trata de fila ou regulação.** |
| Endpoints de dados da fila | `GET /api/indicadores-ambulatoriais/numero-fila-espera/` sem parâmetros retorna 404; `GET /api/regulacao/unidade` retorna erro de parâmetro ausente. Não foram mais sondados, por economia e para não depender de endpoint não documentado. |
| Termos de uso | Existe um endpoint `/api-adm/termo/` no front, mas o conteúdo **não foi verificado**. Não há termo público de uso de API. Nenhum termo foi aceito e nenhuma conta foi criada. |
| Acesso do paciente | Pela plataforma Saúde Digital, com cadastro por CPF: o paciente consulta a própria posição (fonte: notícias SESA). Não serve ao projeto. |

**Conclusão:** a SESA dispõe da data de entrada (Fastmedic), mas a expõe apenas em painel restrito. O caminho legítimo é a **solicitação institucional** (SESA / Coordenadoria de regulação / CIEGES) ou um termo de cooperação, e não a raspagem de endpoints não documentados.

### 2.2 Fontes nacionais

| Fonte | Situação |
|---|---|
| Programa Nacional de Redução das Filas / "Agora Tem Especialistas" | Existe dataset no Portal de Dados Abertos do SUS (`dadosabertos.saude.gov.br/dataset/mgdi-agora-tem-especialistas-componente-cirurgias`). **Conteúdo não verificado** (a consulta falhou nesta sessão). Pela natureza do programa, é provável que seja agregado por UF ou município e trate de produção, sem espera individual (inferido). |
| SISREG | O Ceará regula cirurgias eletivas no Fastmedic, não no SISREG. **Não verificado** se há espelho no SISREG para o CE. |
| SIH/SUS (já no projeto) | Tem data de internação e de saída (produção realizada), mas não a data de entrada na fila. Serve à previsão, não à espera. |
| dados.ce.gov.br | **Não verificado** nesta sessão. |

---

## 3. Dados locais (somente leitura)

### 3.1 Banco `backend/predmed.db`
- `pacientes_fila`: 63.495 registros; `data_insercao` vazia em **100%**; `data_atualizacao` tem um único valor, a data da carga (25/02/2026). Em `predmed-original.db`, a mesma tabela tem 63.477 registros, também 100% sem data.
- **O importador descarta `POSICAO_FILA` e `NUN_SOLICITACAO`** (`services/data_import.py`, `col_map`). Sem esses campos, o banco não permite comparar snapshots nem ordenar por antiguidade. Isso precisa mudar em B25, com pseudonimização (ver seção 6).
- O importador preenche SWALIS ausente com "Categoria D" (`data_import.py`). É uma imputação silenciosa que deveria virar "Não informada" (cerca de 3% da fila vem assim).
- `serie_historica`: 384 linhas (2024-03 a 2026-02) **geradas sinteticamente** por `services/previsoes.build_serie_historica`, que parte de uma espera fixa de 5,2 meses. Não é dado observado.
- `aih_registro`: vazia em `predmed.db`. Em `predmed-original.db` há datas de internação e saída (SIH), mas não data de entrada na fila.

**Nenhuma tabela ou coluna local contém data de entrada na fila.**

### 3.2 Comparação dos snapshots (22/02/2026 13:14 → 24/02/2026 07:06, cerca de 41,9 h)

**Qualidade do arquivo**
- Os dois arquivos têm 63.495 linhas, as mesmas 9 colunas e 38 números de solicitação repetidos.
- O arquivo de 22/02 perdeu os acentos na exportação: há 135.774 caracteres de substituição U+FFFD, e a perda é irreversível. O de 24/02 está em ISO-8859-1. Para comparar, o script normaliza os dois.
- Observação: o total é idêntico nos dois dias, com exatamente 562 entradas e 562 saídas. Pode ser coincidência, mas vale checar se a exportação tem teto de linhas. **Não verificado.**

**Estabilidade do nº de solicitação**
- 62.895 números aparecem nos dois snapshots (99,1%); 562 saíram e 562 entraram.
- Para os números comuns, os atributos quase não mudam: procedimento 25, unidade 16, SWALIS 9, município 7, especialidade 7, judicializado 5. **O nº de solicitação é um identificador estável** e permite acompanhar cada solicitação entre snapshots.

**Estrutura da numeração**, com séries inferidas pelo nº de dígitos:

| Série | Registros (22/02) | Unidades | Entradas no intervalo | Entradas acima do máximo anterior | Avanço do máximo |
|---|---|---|---|---|---|
| 11 dígitos | 14.277 (22,5%) | 25 | 87 | 84 | cerca de 565 números/dia |
| 7 dígitos | 44.907 (70,7%) | 133 | 474 | 464 | cerca de 2.400 números/dia |
| até 6 dígitos | 4.311 (6,8%) | 122 | 1 | 0 | 0 (série legada, sem novas emissões) |

- 548 das 562 entradas (97,5%) têm número maior que o máximo do snapshot anterior na própria série. **A numeração é sequencial.**
- O número avança cerca de 9 vezes mais rápido que as entradas na fila cirúrgica. A numeração é, portanto, compartilhada com outras solicitações do sistema (inferido: consultas e exames).
- 70 unidades têm pacientes de mais de uma série. Isso aponta migração ou coexistência de sistemas (inferido).

**Nº de solicitação × posição na fila** (Spearman, grupos com ≥ 30 registros, snapshot de 24/02)

| Recorte | Grupos | Registros | ρ mediano | ρ ponderado |
|---|---|---|---|---|
| Global | – | 63.495 | 0,11 | – |
| Unidade × especialidade | 237 | 59.719 | 0,56 | 0,40 |
| Unidade × procedimento | 415 | 40.244 | 0,93 | 0,77 |
| **Unidade × procedimento × SWALIS** | 402 | 34.619 | **1,00** | **0,95** |

- A posição é numerada por **unidade × procedimento**: há apenas cerca de 500 posições repetidas nesse recorte, contra cerca de 10.600 em unidade × especialidade.
- Dentro da mesma classe SWALIS, a posição segue a ordem do nº de solicitação, ou seja, a ordem de chegada. A correlação posição × SWALIS é mediana de apenas 0,40. A regra de ordenação da SESA mistura prioridade e antiguidade, e **não foi documentada publicamente**.
- As posições vão de 1 a 9.999. Há 3 ou 4 registros com 9.999, provavelmente um valor sentinela.

**Movimento em cerca de 42 h**
- Dos registros comuns, 10.044 subiram de posição, 51.167 ficaram na mesma e 1.684 desceram.
- Quem saiu estava perto da frente: posição mediana 12, p75 33, p95 221.

**Idade aparente do estoque: estimativa ilustrativa, NÃO validada**
Se o ritmo de emissão de números fosse constante e igual ao observado nesse intervalo (que incluiu um domingo), teríamos:
- série de 7 dígitos: mediana do estoque com cerca de 270 dias; 5% mais antigos com mais de cerca de 930 dias;
- série de 11 dígitos: mediana com cerca de 390 dias; 5% mais antigos com mais de cerca de 1.250 dias.

Isso dá só a **ordem de grandeza** (meses a poucos anos), coerente com fila crônica. O ritmo real varia por dia útil, por ano e por sistema. **Não usar estes números como resultado.**

---

## 4. Métodos para obter ou estimar o tempo de espera

| Método | Como | Prós | Contras e riscos | Viabilidade até fev/2027 |
|---|---|---|---|---|
| **(a) Data oficial da SESA** (painel 232 / Fastmedic) | Ofício ou termo com a SESA para extração periódica com data de solicitação ou inclusão, pseudonimizada | Dado verdadeiro; cobre o estoque antigo; permite KPI e priorização completa | Depende de terceiro e de prazo burocrático; exige base legal LGPD e acordo de uso | Média. Pedir em out/2026; é plausível obter até dez/2026–jan/2027 se houver patrocinador na SESA |
| **(b) Snapshots automatizados** | Baixar o CSV público do painel 214 diariamente (idealmente a cada poucas horas); a data da primeira aparição vira a data de entrada observada; a saída observada fecha o episódio | Não depende de ninguém; mede entradas, saídas e espera **real** de coortes novas; alimenta a previsão (entradas e saídas por dia) | Só mede quem entra depois do início da coleta (**censura à esquerda** do estoque); com 3–5 meses de coleta, só se observam esperas curtas (**censura à direita**); é preciso tratar reentradas, mudanças de unidade e falhas de coleta; o formato do painel pode mudar; é preciso confirmar os termos de uso | **Alta** para começar já. Em fev/2027 haverá cerca de 4 meses de coortes: dá para estimar taxas e curvas de sobrevivência iniciais (Kaplan-Meier), mas não a espera mediana de filas longas |
| **(c) Proxy pelo nº de solicitação** | Converter o número em data estimada por série, com uma curva nº → data calibrada | Cobre o estoque antigo imediatamente; a ordem já é confiável (ρ ≈ 0,95 na fila) | Precisa de pontos de âncora com data conhecida; há séries distintas e ritmo variável; o erro é desconhecido até a calibração | Média. **A calibração prospectiva começa sozinha com (b)**: cada dia de coleta registra o nº máximo emitido naquela data. Para o passado, precisa de âncoras da SESA ou do hospital piloto (algumas dezenas por série bastam para interpolar). Sem âncoras, só vale como **ordem**, não como dias |
| **(d) Dados do hospital piloto** | Termo de cooperação (B41) para extrair do sistema do hospital (Tasy/MV/planilha) a data de indicação ou inclusão da própria fila | Dado verdadeiro no escopo do piloto; linha de base do KPI (B35); fornece âncoras para (c) | Cobre apenas um hospital; a data do hospital pode diferir da data de regulação; o prazo depende do jurídico | Média-alta para o piloto; é o caminho mais provável para o KPI de −40% |

**Tratamento do estoque antigo** (quem já estava na fila antes da coleta):
1. Nunca atribuir a data da primeira coleta como data de entrada. Marcar `data_entrada_observada = NULL` e `entrada_censurada = true`.
2. Usar a ordem pelo nº de solicitação para a priorização (antiguidade relativa dentro da fila).
3. Quando houver âncoras (a, d), estimar a data pelo nº de solicitação, com intervalo e rótulo "estimado". Se a SESA fornecer a data, substituir.
4. Em análises de tempo, usar métodos de sobrevivência com censura, não médias simples.

---

## 5. Recomendação

Combinar **(b) + (c) já, (a) em paralelo e (d) para o piloto**:

1. **Esta semana:**
   - Colocar em produção uma coleta diária (depois horária, se estável) do CSV público do painel 214 (antecipa B25).
   - Preservar cada arquivo bruto com hash e carimbo de data e hora, em armazenamento restrito.
   - Registrar por série o nº máximo observado em cada coleta (âncora de calibração prospectiva).
   - Cada dia sem coleta é histórico perdido. Os dois snapshots de fevereiro já servem de marco zero parcial, mas há um intervalo de 7 meses sem dados.
2. **Ajustar o importador:**
   - Manter `POSICAO_FILA` e o nº de solicitação **pseudonimizado** (HMAC com segredo fora do código).
   - Manter as datas de primeira e última observação.
   - Parar de imputar "Categoria D".
   - Tratar a codificação dos arquivos.
3. **Em outubro/2026:** ofício à SESA pedindo extração periódica da fila cirúrgica com data de solicitação ou inclusão (dados pseudonimizados), ou acesso institucional ao painel 232, e confirmação dos termos de uso da coleta automatizada do painel 214.
4. **Até B35 (dez/2026):**
   - Linha de base do piloto com a data do hospital (d), se o termo estiver assinado.
   - Caso contrário, linha de base = coorte observada por (b) desde a data de início da coleta, declarada como tal.
5. **Priorização (B34/B37):** usar a antiguidade **ordinal** (posição relativa pelo nº de solicitação dentro de unidade × procedimento) até existir data. Não exibir "dias de espera" inventados.

---

## 6. Riscos

| Risco | Mitigação |
|---|---|
| O CSV público contém iniciais e nº de solicitação, que são dados pessoais (regra do projeto) | Guardar o bruto cifrado com acesso restrito e retenção definida; pseudonimizar no ETL; nunca logar linhas; registrar a base legal (B29) |
| Termos de uso ou bloqueio da coleta automatizada | Baixa frequência, identificação do cliente, sem contornar autenticação; formalizar com a SESA |
| Mudança de formato ou encerramento do painel | Validação de esquema no coletor; alerta de falha; manter a base anterior (critério do B25) |
| Possível teto de linhas na exportação (total idêntico nos dois snapshots) | Conferir o total contra o número exibido no painel a cada coleta |
| Proxy mal calibrado apresentado como tempo real | Rotular "estimado"; publicar o erro da calibração; usar como ordem até validar |
| A SESA não fornece a data | O KPI do piloto passa a depender de (d) e da coorte de (b) |

---

## 7. Impacto na promessa de "tempo real"

- A fonte pública atualiza **a cada hora** (painel 214). O painel privado com datas atualiza **uma vez por dia**. O PREDMED não pode ser mais "tempo real" que isso.
- **Proposta de redação:** "dados atualizados na frequência da fonte oficial (até horária para a fila, diária para indicadores)".
- O **tempo de espera** não é obtido da fonte pública. Até a SESA ou o hospital fornecerem datas, o sistema deve exibir:
  - espera **observada** apenas para coortes coletadas desde o início da coleta;
  - antiguidade **relativa** para o estoque.
- O parâmetro fixo de 5,2 meses deve continuar rotulado como não validado.
- A meta de −40% no tempo de espera só é mensurável com (a) ou (d). Com (b), são mensuráveis as taxas de saída e o tempo até a saída das novas coortes, e isso deve constar como limitação no relatório à FUNCAP.

---

### Referências consultadas
- https://integrasus.saude.ce.gov.br/ (bundle público e configuração)
- https://integrasus.saude.ce.gov.br/api-adm/dashboard-area/ (catálogo de painéis; consultado em 28/09/2026)
- https://datasets-integrasus.saude.ce.gov.br/datasets/
- https://www.ce.gov.br/saude/programa-de-cirurgias-eletivas/ e notícias SESA sobre o Saúde Digital (via busca)
- https://www.gov.br/saude/pt-br/composicao/saes/agora-tem-especialistas/pnrf
- https://dadosabertos.saude.gov.br/dataset/mgdi-agora-tem-especialistas-componente-cirurgias (existência verificada por busca; conteúdo não verificado)
- https://github.com/integrasus/api-covid-ce (a API pública do IntegraSUS existente é só de covid)
