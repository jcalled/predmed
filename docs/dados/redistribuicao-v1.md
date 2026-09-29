# Redistribuição v1: pressão e ociosidade estimadas por estabelecimento (CNES)

Versão: 29/09/2026. Funcionalidade 3 do plano (meta: −40% no tempo de espera, **ainda não comprovada**). Item E2.5 do checklist.
Código: `backend/services/redistribuicao.py` (regras puras), `services/ia_engine.py` (`get_hospitais_pressao`, `get_redistribuicao_sugestoes`), endpoints `/hospitais`, `/redistribuicao`, `/zerarfilas`.
Testes: `backend/tests/test_redistribuicao.py` (dados sintéticos).

**Resumo (base de 29/09/2026).**
- 226 estabelecimentos avaliados: 192 da fila IntegraSUS (187 com CNES, 5 nomes sem CNES) e 34 fora da fila com produção cirúrgica SUS no SIH.
- **85 estabelecimentos com ociosidade estimada**, somando **≈ 2.600 cirurgias/mês** (cerca de 15% da produção cirúrgica SUS mensal sem obstetrícia do CE). Ociosidade é **estimada**, não vaga confirmada.
- **79 sugestões, 871 pacientes/mês redistribuíveis**, todas dentro da mesma CIR: 776 com capacidade estimada e 95 com vagas declaradas por hospital particular (o único particular com vagas hoje é o tenant de demonstração).
- 14 sugestões (173 pacientes/mês) envolvem vínculo nome→CNES **provisório** e vêm sinalizadas.
- Simulação de mutirão (90 dias): **1.768 pacientes redistribuíveis de uma fila de 61.756 (2,9%)**. É um cenário **simulado**. O número anterior (201.794 redistribuíveis e −100%) vinha de uma soma sem limite e foi corrigido.

## 1. Fontes

| Fonte | Tabela / arquivo | Competências | Uso |
|---|---|---|---|
| IntegraSUS (fila) | `pacientes_fila` (`cnes`, `cnes_confianca`) | coleta atual | fila por estabelecimento × especialidade |
| Vínculo nome→CNES | `hospital_alias` (ver `datasus-cnes-sih.md`) | — | CNES de cada nome da fila; não-ALTA = provisório |
| SIH-RD por CNES | `producao_cirurgica_cnes` (nova), `~/PredmedDados/datasus/processado/producao_cirurgica_cnes.csv` | 2024-07 a 2026-06 (2026-05 e 2026-06 provisórias) | produção cirúrgica mensal por estabelecimento |
| CNES | `cnes_capacidade` | 2026-08 | município → CIR, salas cirúrgicas, leitos cirúrgicos SUS, habilitações, natureza |
| Vagas declaradas | `config_vagas` (hospital particular) | mês corrente | capacidade **confirmada pelo hospital** |

**Script:** `backend/_SCRIPTS/producao_cirurgica_cnes.py`.
- Usa as mesmas regras da série estadual da previsão: AIH principal (`IDENT = 1`), `PROC_REA` do grupo 04, competência de processamento e o mapa SIGTAP → especialidade de `serie_producao_cirurgica.py`.
- **Conferência:** nas 24 competências, a soma por CNES é igual à série estadual (diferença 0).
- 155 CNES com produção e 509.867 AIHs no período.
- Saída só com contagens. Tem cache por sha256 e leva cerca de 1 min 40 s.
- Backup antes da carga: `~/PredmedDados/backups/predmed_antes_producao_cnes_202609291019.db`.

## 2. Unidade e CIR

- A unidade é o **estabelecimento (CNES)**. Os nomes da fila que apontam para o mesmo CNES são somados. O nome exibido é o mais frequente na fila; fora da fila, é o nome fantasia do CNES.
- **A CIR vem do município do estabelecimento no CNES** (`cir_ads_predmed`, 22 ADS).
  - O `hospital_cir_map` antigo usava o município de **residência dos pacientes** e diverge do CNES em 48 estabelecimentos da fila.
  - Ele só é usado como último recurso: nos nomes sem CNES e na validação de aprovação da SMS.
- Validação de escopo da SMS em `/redistribuicao/aprovar` (`_cir_do_hospital`), nesta ordem:
  1. alias → CNES → CIR do CNES;
  2. nome fantasia CNES exato e único;
  3. tenant particular;
  4. `hospital_cir_map`.

## 3. Pressão (por estabelecimento e por especialidade)

- **Pressão** = fila atual ÷ produção cirúrgica mensal média do próprio estabelecimento. A produção é de 12 meses, todas as internações, sem obstetrícia. É a mesma escala de antes: "meses de produção na fila".
- **Não é tempo de espera.**
- Status: crítico ≥ 3; alerta ≥ 1,5; normal ≥ 0,5; ocioso < 0,5. "Ocioso" passa a exigir ociosidade estimada > 0; sem ela, o status fica "normal".
- Sem produção no SIH: pressão 99, exibida como "sem dado".
- A produção de todas as internações foi usada, e não só a eletiva, porque parte dos pacientes da fila é internada como urgência. Exemplo: o hospital cardiológico de referência tem cerca de 1 AIH eletiva por mês e cerca de 450 no total.

**Disparidade regional** (fila ÷ produção mensal, soma da CIR):

| CIR | Pressão |
|---|---:|
| Maracanaú | 7,4 |
| Fortaleza | 5,8 |
| Beberibe | 2,8 |
| Crato | 2,7 |
| Iguatu | 2,5 |
| Canindé | 2,5 |
| Demais CIR | 0,2 a 1,8 |

- A fila de Fortaleza (41.784) concentra pacientes de todo o estado.
- A regra "mesma CIR" impede que a ociosidade estimada do interior (por exemplo, Icó, Crateús e Camocim, com pressão < 1) alivie a capital. Mudar isso é decisão da SESA e muda a meta de deslocamento.

## 4. Ociosidade estimada (por estabelecimento, por mês)

O cálculo pega **o menor de três limites**, para ser conservador:

| Limite | Fórmula | Hipóteses |
|---|---|---|
| (a) demonstrada | maior média móvel de 3 meses em 24 meses − média dos últimos 6 meses | o hospital já sustentou esse volume por um trimestre |
| (b) salas | salas cirúrgicas CNES × 2 turnos × 22 dias × 2 cirurgias × fração SUS − produção recente | 88 cirurgias/sala/mês nominais. Fração SUS = leitos cirúrgicos SUS ÷ existentes (público = 1) |
| (c) leitos | leitos cirúrgicos SUS × 30 ÷ 3 dias de permanência × 85% − produção recente | permanência pós-operatória média de 3 dias |

**Exclusões (ociosidade = 0):**
- sem vínculo SUS, sem centro cirúrgico ou com 0 salas;
- **queda estrutural:** produção recente abaixo de 50% da capacidade demonstrada. Isso costuma indicar reforma, fechamento, troca de CNES ou atraso de faturamento. Caíram nessa regra 47 estabelecimentos, quase todos de baixo volume, mais um hospital geral estadual com produção zerada em 2026 e uma entidade filantrópica cujo pico veio de mutirão.

**Resultado:**
- O limite que prevalece é quase sempre o **demonstrado** (73 de 85). Salas e leitos cadastrados indicam folgas bem maiores, que não aparecem na produção.
- 15 estabelecimentos produzem mais do que o limite teórico das salas. Isso indica cadastro de salas desatualizado ou premissa de 2 cirurgias por turno baixa demais; eles ficam sinalizados em `cadastro_salas_inconsistente`.

## 5. Regras das sugestões

1. **Mesma CIR** (ADS do CNES), sempre. Não há mais sugestões entre CIR da mesma macrorregião ou de outra macrorregião. O campo `tipo_transferencia` é sempre `mesma_regiao`.
2. **Origem** (estabelecimento × especialidade):
   - a fila precisa ser maior que 1,5 mês da própria produção na especialidade;
   - só o **excedente** acima de 1,5 mês é redistribuível;
   - a ordem de atendimento é da maior para a menor pressão.
3. **Destino compatível:**
   - estar apto (SUS, centro cirúrgico, salas, sem queda estrutural);
   - ter feito **≥ 2 AIH/mês na especialidade** (média de 12 meses);
   - para **oncologia, cardiovascular e neurologia**, ter a habilitação CNES vigente (`hab_oncologia`, `hab_cardiovascular`, `hab_neurocirurgia`);
   - ter fila própria na especialidade ≤ 1 mês de produção.
4. **Capacidade:**
   - o destino recebe no máximo **+50% da sua produção mensal na especialidade**;
   - a soma recebida por destino, em todas as especialidades, é ≤ ociosidade estimada;
   - transferências aprovadas no mês corrente são descontadas;
   - não são exibidas sugestões com menos de 3 pacientes por mês.
5. **Vagas declaradas por hospital particular** têm precedência:
   - são capacidade confirmada pelo hospital e não são verificadas no SIH;
   - a aprovação envia `tenant_destino_id` e o backend confere o saldo.
6. **Garantias testadas:** qtd ≤ excedente ≤ fila; soma por destino ≤ ociosidade.

**Campos novos (os antigos foram mantidos):**
- nas sugestões: `capacidade_natureza` (`estimada` ou `declarada`), `cnes_origem`, `cnes_destino`, `excedente_origem`, `fila_especialidade_origem`, `producao_especialidade_destino_mes`, `ociosidade_destino_mes`, `vinculo_provisorio`, `natureza_dado = "estimado"`;
- na resposta: `metodologia` (hipóteses, parâmetros e fontes), `natureza`, `regra_regional`, `hospitais_com_ociosidade`, `ociosidade_total_mes`;
- nos hospitais: `ociosidade_estimada_mes`, `ociosidade_limitada_por`, `capacidade_*_mes`, `queda_producao_recente`, `vinculo_cnes`, `vinculo_provisorio`, `cir_fonte`.

**Mudanças de comportamento:**
- `reducao_espera_dias` é uma heurística **simulada**: qtd ÷ produção da origem × 30. Pode ser `null`.
- `/redistribuicao` aceita `?cir=` (o frontend já enviava esse parâmetro).

**Sugestões por especialidade** (pacientes/mês): cirurgia digestiva 240, outras 227, ortopedia 118, ginecologia 92, urologia 51, otorrino 48, oftalmologia 30, pequenas cirurgias 23, plástica reparadora 19, cardiovascular 14, neurologia 9.
- **Oncologia:** 0. Nenhum destino habilitado na mesma CIR passou pelas regras.
- **Bucomaxilofacial e endocrinologia:** 0.

## 6. Simulação de mutirão (`/zerarfilas`, aba "Simulação de mutirão")

- **Cenário:** as sugestões mensais se repetem por 3 meses (`horizonte_meses`, de 1 a 6), limitadas ao excedente de cada origem.
- **Fila sem ação:** é suposta **estável** (entradas = saídas), porque não há série observada de entradas na fila. A "fila projetada em 6 meses" antiga vinha da série sintética e saiu da tela.
- **Garantias** (testadas):
  - 0 ≤ redistribuíveis ≤ fila, por especialidade e no total;
  - redução entre 0 e 100%.
- **Erro anterior:** a soma das sugestões (até 100.000 linhas sem limite de origem) era comparada com uma fila projetada simulada. Daí os 201.794 "redistribuíveis" e os −100%.
- **Rótulos:** tudo é `simulado`, inclusive o valor de AIH (R$ 1.500 fixo). A ociosidade que alimenta o cenário é `estimado`.

## 7. Limitações e próximos passos

- **Capacidade cadastrada ≠ disponibilidade.** Faltam agenda, equipe, anestesia, OPME e turnos reais. O próximo passo é a confirmação pelo hospital (fluxo de vagas declaradas também para públicos e filantrópicos) e a comparação entre ociosidade estimada e confirmada no piloto.
- **Sem SIA/APAC:** a ocupação das salas por cirurgia ambulatorial não aparece. Oftalmologia e pequenas cirurgias ficam subestimadas na compatibilidade e superestimadas na folga das salas.
- **Priorização clínica ainda não entra:** a escolha de *quais* pacientes transferir (SWALIS, judicialização, oncologia) fica para a priorização.
- **Mapa SIGTAP → especialidade** é hipótese (ver `previsao-demanda-v1.md`, seção 3). "OUTRAS" mistura torácica e politrauma; muita coisa ali é urgência.
- **Parâmetros** (turnos, cirurgias por sala, permanência, +50%, limites de pressão) precisam ser calibrados com a SESA e os hospitais do piloto. Estão em `redistribuicao.PARAMS` e são devolvidos pela API.
- **Revisar os vínculos provisórios** (26 CNES) e os 5 nomes sem CNES (`vinculo-fila-cnes-revisao.md`).
- **A meta de −40% no tempo de espera não é medida** por nada aqui. Exige um piloto com a data de entrada e saída da fila.

## 8. Como reproduzir

```bash
cp backend/predmed.db ~/PredmedDados/backups/predmed_$(date +%Y%m%d%H%M).db
backend/venv/bin/python backend/_SCRIPTS/producao_cirurgica_cnes.py     # SIH por CNES → tabela + CSV
cd backend && APP_ENV=dev venv/bin/python -m pytest -q tests/test_redistribuicao.py
```
