# Dados públicos DATASUS para o Ceará: CNES e SIH-RD

Versão: 29/09/2026. Scripts: `backend/_SCRIPTS/coleta_datasus.py`, `cnes_capacidade.py`, `casar_estabelecimentos_cnes.py`.
Usos: funcionalidade 3 (redistribuição), com a capacidade instalada real, e funcionalidade 1 (previsão), com a série SIH atualizada.
Os arquivos brutos e processados ficam em `~/PredmedDados/datasus/`, fora do git. `predmed-original.db` só é lido (modo `ro`). Em 29/09/2026 foram carregados no `predmed.db` a capacidade CNES, o vínculo fila→CNES e a série de produção cirúrgica (seção **Carga no predmed.db**).

## Fontes verificadas (FTP público do DATASUS, testado em 28–29/09/2026)

| Fonte | Caminho | Cobertura verificada | Publicação observada (MDTM) |
|---|---|---|---|
| SIH-RD (AIH reduzida) | `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RDCEaamm.dbc` | até **2026-07** | por volta do dia 7 de cada mês; em 07/09/2026 as competências 2025-08 a 2026-07 foram republicadas |
| CNES — Estabelecimentos | `.../CNES/200508_/Dados/ST/STCEaamm.dbc` | até **2026-08** | ~dia 15 |
| CNES — Leitos | `.../CNES/200508_/Dados/LT/LTCEaamm.dbc` | até 2026-08 | ~dia 15 |
| CNES — Habilitações | `.../CNES/200508_/Dados/HB/HBCEaamm.dbc` | até 2026-08 | ~dia 15 |
| CNES — Serviço especializado | `.../CNES/200508_/Dados/SR/SRCEaamm.dbc` | até 2026-08 | ~dia 15 |
| CNES — Equipamentos | `.../CNES/200508_/Dados/EQ/EQCEaamm.dbc` | até 2026-08 | ~dia 15 |
| CNES — tabelas TabWin | `.../CNES/200508_/Auxiliar/TAB_CNES.zip` (127 MB) | CADGERCE atualizado em 15/09/2026 | ~dia 16 |
| Dicionário CNES | `.../CNES/200508_/Doc/IT_CNES_1706.pdf` (também dentro do TAB_CNES.zip) | — | — |

Descartados:
- **OpenDataSUS** `cnes_estabelecimentos.zip` (S3 `ckan.saude.gov.br`): responde, mas a última modificação é de 11/06/2025 (desatualizado).
- **API `cnes.datasus.gov.br/services`**: HTTP 503 no teste.
- **pysus**: desnecessário. `pyreaddbc` e `dbfread`, que já estão no `backend/venv`, leem os `.dbc`. Nenhuma dependência foi adicionada.

## O que cada arquivo traz (campos usados)

- **ST**: um registro por estabelecimento ativo na competência (16.520 no CE em 2026-08). Traz município (`CODUFMUN`), tipo (`TP_UNID`), natureza jurídica (`NAT_JUR`), esfera, vínculo SUS e as instalações físicas. **Não traz o nome.** Mapeamento conferido no `Estabelecimento.def` do TabWin (o PDF só diz "quantidade de salas"):
  - `CENTRCIR` = tem centro cirúrgico; `QTINST31` = **salas de cirurgia**; `QTINST32` = salas de recuperação; `QTLEIT32` = leitos de recuperação; `QTINST33` = salas de cirurgia ambulatorial (centro cirúrgico);
  - `QTINST30` = cirurgia ambulatorial (ambulatório); `QTINST13` e `QTINST24` = pequena cirurgia; `QTINST37` = sala de cirurgia do centro obstétrico; `QTLEITP1` = leitos cirúrgicos.
- **LT**: leitos por tipo (`TP_LEITO`: 1 cirúrgico, 2 clínico, 3 complementar/UTI, 4 obstétrico, 5 pediátrico, 6 outras, 7 hospital-dia) e especialidade (`CODLEITO`). Colunas `QT_EXIST`, `QT_SUS`, `QT_CONTR`.
- **HB**: habilitações com vigência (`CMPT_INI`/`CMPT_FIM`). A descrição vem de `HABILITA.DBF`. Exemplos: oncologia, alta complexidade cardiovascular, traumato-ortopedia e "Programa Nacional de Redução de Filas de Cirurgias Eletivas".
- **SR / EQ**: serviços especializados e equipamentos. Foram baixados e validados, mas ainda não entram na tabela de capacidade.
- **TAB_CNES.zip**: `CADGERCE.dbf` (nome fantasia e razão social de 20.139 CNES do CE, inclusive inativos) e as tabelas `.cnv` de município, região de saúde, macrorregião, tipo de estabelecimento e natureza jurídica.
- **SIH-RD**: uma linha por AIH paga na competência de processamento. Traz `CNES`, `PROC_REA` e datas de internação e saída, entre outros campos. O arquivo contém dados de pacientes (datas, CEP, idade); ele é lido só para gerar agregados.

## Coleta automática (`coleta_datasus.py`)

- Lista o FTP e baixa **só o que falta ou mudou**, comparando tamanho e MDTM com `estado.json`. Grava em `.part` e renomeia. Tem retentativas, timeout de 120 s por operação FTP e baixa prioridade de I/O no launchd.
- **Valida** cada arquivo: colunas esperadas, competência (`ANO_CMPT/MES_CMPT` no SIH, `COMPETEN` no CNES) e número de registros. Arquivo inválido é apagado e a execução termina com erro.
- Grava no manifesto `~/PredmedDados/datasus/manifesto.jsonl` **somente agregados**: registros, estabelecimentos, AIHs com procedimento do grupo 04 (cirúrgico), intervalo de internação, sha256.
- Depois de um CNES novo, gera `processado/cnes_capacidade.csv` e `processado/vinculo_fila_cnes.csv`.
- Padrão: SIH a partir de 2025-01 (`--sih-inicio`) e só a última competência CNES (`--cnes-competencias N` para histórico). Outras opções: `--so-sih`, `--so-cnes`, `--verificar`.
- Idempotência testada: a 2ª execução terminou com 0 arquivos novos e 0 erros. Houve um timeout de FTP, recuperado na retentativa.

### Agendamento (plist criado, **não instalado**)

Arquivo `backend/_SCRIPTS/launchd/br.predmed.coleta-datasus.plist`: roda nos dias 10 e 25, às 4h. Log em `~/PredmedDados/logs/coleta-datasus.log`.

```bash
mkdir -p ~/PredmedDados/logs
cp backend/_SCRIPTS/launchd/br.predmed.coleta-datasus.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/br.predmed.coleta-datasus.plist
launchctl kickstart gui/$(id -u)/br.predmed.coleta-datasus    # rodar agora
launchctl bootout gui/$(id -u)/br.predmed.coleta-datasus      # desinstalar
```

## SIH-RD 2025+ baixado e validado

19 competências (2025-01 a 2026-07), 75 MB, **958.269 AIHs**, das quais 407.607 têm procedimento realizado do grupo 04 (cirúrgico). Em todos os arquivos, 100% dos registros estão na competência esperada.

| Ano | AIHs | AIHs grupo 04 | Observação |
|---|---:|---:|---|
| 2024 (local, `backend/data/sih`) | 587.132 | 245.680 | referência de continuidade |
| 2025 (12 competências) | 597.976 | 248.751 | +1,8% sobre 2024: série contínua, sem quebra |
| 2026-01 a 2026-07 | 360.293 | 158.856 | 2026-07 tem 202 estabelecimentos (média de ~230) e pode ainda ser complementado |

Contagem por competência no manifesto. O intervalo de `DT_INTER` começa em 2019 ou 2023: são AIHs apresentadas com atraso. A série deve usar a competência ou a data de saída, nunca contar só a data de internação.

**Não verificado:** se o DATASUS reprocessa competências antigas além da republicação de 07/09/2026. A coleta detecta mudança de tamanho ou MDTM, baixa de novo e registra `acao = atualizado`.

### Como carregar (não executado)

1. Backup: `cp backend/predmed.db ~/PredmedDados/backups/predmed_$(date +%Y%m%d%H%M).db`.
2. Recomendado: **não** carregar AIH linha a linha no `predmed.db` (3,2 mi + 0,96 mi linhas). Gerar um agregado mensal por CNES × especialidade × grupo SIGTAP, lendo os `.dbc` de `backend/data/sih` (2019–2024) e de `~/PredmedDados/datasus/sih/RD` (2025+), e gravar numa tabela de série.
3. `SIH/download_sih.py --so-importar --pasta ~/PredmedDados/datasus/sih/RD` é a via existente (não testada nesta rodada; o módulo agora pode ser importado sem efeitos colaterais). Mas ele grava AIH linha a linha e recalcula `SerieHistorica` com `entradas = 1,3 × saídas`, que é **sintético**. Não usar esse recálculo como resultado medido.

## Capacidade instalada (CNES 2026-08) — `processado/cnes_capacidade.csv`

Uma linha por CNES ativo (16.520). Colunas: nome, município, `cir_ads_predmed`, região e macrorregião CNES, tipo, natureza, vínculo SUS, salas (cirúrgicas, recuperação, ambulatoriais, obstétricas), leitos cirúrgicos/totais/complementares (existentes e SUS), habilitações vigentes e marcadores (`hab_oncologia`, `hab_cardiovascular`, `hab_traumato_ortopedia`, `hab_oftalmologia`, `hab_pnrf_eletivas`...). O nome de estabelecimento de pessoa física é omitido.

| Indicador (CE, 2026-08) | Valor |
|---|---:|
| Estabelecimentos com centro cirúrgico | 284 (217 com vínculo SUS) |
| Natureza dos com centro cirúrgico | 133 públicos, 98 privados, 52 sem fins lucrativos, 1 PF |
| Salas de cirurgia (`QTINST31`) | 722 (560 em estabelecimentos com vínculo SUS) |
| Salas por macrorregião | Fortaleza 443, Cariri 125, Sobral 96, Litoral Leste/Jaguaribe 31, Sertão Central 27 |
| Leitos cirúrgicos (LT) | 5.517 existentes, 4.146 SUS |
| Centro cirúrgico com 0 salas informadas | 22 (qualidade do cadastro) |

**Regiões:** o TabWin usa a regionalização atual do CE, com 5 regiões de saúde e 5 macrorregiões. O PREDMED usa as 22 ADS com o rótulo "CIR ..." (`gerador_CIR_ceara.py`, SESA 2022). A tabela traz as duas; todos os municípios foram mapeados para uma ADS. Falta confirmar com a SESA qual recorte é a "CIR" operacional da regulação.

**Limites:** salas e leitos são **capacidade cadastrada**, não disponibilidade. Não informam turnos, equipe, agenda nem ocupação. A capacidade ociosa ainda precisa ser estimada assim: produção observada no SIH por CNES comparada com a capacidade teórica (salas × turnos × dias), com a hipótese de turnos declarada. A disponibilidade real depende de confirmação do hospital, o que não está feito.

## Vínculo nome da fila → CNES — `processado/vinculo_fila_cnes.csv`

O IntegraSUS publica o nome do estabelecimento (194 distintos), não o CNES. O campo `municipio` da fila é o **município de residência do paciente**, não o do hospital. Por isso a restrição por município é:

- **dura** quando o nome contém "DE/DO/DA <município>" ou termina no nome do município (ex.: "Santa Casa de Misericórdia de Sobral");
- **suave** nos demais casos: bônus para CNES localizados nos 3 municípios de residência mais frequentes da fila daquele estabelecimento.

Método: normalização (acentos, pontuação, abreviações HOSP/MATERN/MUNIC/DR/STA), similaridade (sequência + tokens com tolerância a erro de digitação) contra nome fantasia e razão social. Candidatos: CNES ativos no ST e, em segundo plano, cadastrados no CADGERCE (só pessoa jurídica).

| Confiança | Estabelecimentos | Registros da fila |
|---|---:|---:|
| ALTA | 163 (84%) | 55.647 (90,1%) |
| MEDIA | 12 | 3.967 (6,4%) |
| AMBIGUO (mesmo nome em 2+ CNES ativos) | 7 | 1.020 |
| BAIXA | 7 | 1.097 |
| SEM_CORRESPONDENCIA (ex.: "OUTROS", "SECRETARIA MUNICIPAL DE SAUDE") | 5 | 25 |

- ALTA + MEDIA = 175 estabelecimentos, com 96,5% dos registros da fila.
- 121 desses estabelecimentos têm centro cirúrgico no CNES e concentram 59.153 registros.
- Nunca recebem ALTA: CNES ausente do ST da competência, ou homônimo ativo em outro município desempatado só pela residência dos pacientes.
- Revisão manual: `docs/dados/vinculo-fila-cnes-revisao.md` (só nomes de estabelecimentos e contagens).

**Tabela atual `hospital_alias` (fonte `integrasus_auto`):** só 37 dos 194 nomes têm CNES, e **12 dos 37 divergem** do novo casamento. Nos casos conferidos, os aliases antigos estão errados. Exemplos:
- "HCF Hospital Central de Fortaleza" aponta para o CNES do HGF;
- "Santa Casa de Sobral" aponta para a Santa Casa de Fortaleza;
- três unidades "Gonzaga Mota" diferentes apontam para o mesmo CNES;
- "ICO" aponta para o hospital de Santa Quitéria.

Consequência: o vínculo tenant→hospital e a capacidade por hospital que usam essa tabela hoje podem estar atribuídos ao estabelecimento errado.

## Carga no predmed.db (29/09/2026)

Backup anterior: `~/PredmedDados/backups/predmed_antes_vinculo_cnes_202609290922.db` (chmod 600).
Script idempotente: `backend/_SCRIPTS/carregar_vinculo_cnes.py --backup-feito` (`--simular` faz rollback; `--somente-alta` não grava provisórios). Regras em `backend/services/cnes_vinculo.py`; testes em `backend/tests/test_vinculo_cnes.py`.

**Tabela `cnes_capacidade`** (nova, `create_all`, compatível com PostgreSQL): 16.520 linhas da competência 2026-08, chave única (competência, CNES). Cada carga substitui só as competências presentes no CSV.

**Vínculo** (decisão do responsável de 29/09/2026: aceitar as sugestões, mas marcar as não-ALTA como provisórias):

| Situação no `hospital_alias` | Fonte / confiança | Estabelecimentos | Registros da fila |
|---|---|---:|---:|
| Definitivo automático | `cnes_casamento_v1` / ALTA | 163 | 55.647 |
| Provisório (1º candidato) | `cnes_auto_provisorio` / MEDIA | 12 | 3.967 |
| Provisório (1º candidato) | `cnes_auto_provisorio` / AMBIGUO | 7 | 1.020 |
| Provisório (1º candidato) | `cnes_auto_provisorio` / BAIXA | 7 | 1.097 |
| Sem CNES | SEM_CORRESPONDENCIA | 5 | 25 |

- `pacientes_fila.cnes` preenchido em 61.731 de 61.756 registros; a nova coluna `pacientes_fila.cnes_confianca` diz a origem (`ALTA`, `MANUAL` ou `PROVISORIO_<confiança>`; 6.084 registros provisórios).
- Os 12 aliases `integrasus_auto` errados foram corrigidos: 9 por vínculo ALTA e 3 por provisórios (Santa Casa de Sobral, Hospital Nova Saúde, Instituto Lucena).
- **Provável erro, revisar primeiro** (`metodo = PROVAVEL_ERRO_REVISAR`): "HOSPITAL INFANTIL LUCIA DE FATIMA HIF" (sugestão SOPAI parece errada) e "HOSPITAL SAO RAIMUNDO" (homônimos em Crato e Várzea Alegre). O tenant de demonstração "Hospital São Raimundo" (Fortaleza) **não** foi vinculado a nenhum CNES.
- Vínculo manual (`fonte = manual` ou `revisao_manual`) nunca é sobrescrito. Para corrigir um caso: gravar o alias com `fonte='manual'` e o CNES correto; a próxima carga da fila já o aplica.
- `import_integrasus` chama `aplicar_cnes_na_fila` a cada nova coleta: a fila recebe o CNES dos aliases ALTA, manuais e provisórios. Nome novo, que não está no CSV, fica sem CNES até rodar de novo `casar_estabelecimentos_cnes.py` e o carregador.
- Para cada CNES vinculado sem linha em `hospitais`, foi criada uma (fonte `cnes`, dados do `cnes_capacidade`): 95 linhas novas. `pacientes_fila.hospital_id` passou a apontar para o hospital do CNES. O escopo de tenant continua por nome (`main.py`) e não foi alterado.

## Próximos passos

1. SESA/equipe revisa os 26 provisórios e os 5 sem correspondência (relatório `vinculo-fila-cnes-revisao.md`), começando pelos 2 marcados como provável erro; correções entram como alias `manual`.
2. Trocar a "capacidade ociosa" inferida (`capacidade_hospitais`) por produção SIH ÷ capacidade CNES (`cnes_capacidade`), com hipóteses explícitas e rótulo "estimado".
3. Série de previsão: feita — ver `docs/dados/previsao-demanda-v1.md`.
4. Instalar o plist (coordenador) e, na AWS, migrar para agendamento + S3.
