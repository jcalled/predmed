# PREDMED — Matriz de riscos

Versão: 29/09/2026, rev. 2 (período preparatório: Termo assinado, recurso não recebido). Revisar a cada sprint (quinzenal) e no relatório mensal.

Escala: Probabilidade (P) e Impacto (I) de 1 (baixo) a 5 (muito alto). Exposição = P × I. **Crítico ≥ 15**, alto 10–14, médio 5–9, baixo < 5.

Este documento não é parecer jurídico. Onde a mitigação depende de norma (LGPD, regras da FUNCAP/FINEP, Termo de Outorga), a ação indicada é consultar o instrumento ou o profissional competente.

## Resumo

| ID | Risco | P | I | Exp. | Dono | Status em 29/09/2026 |
|---|---|---|---|---|---|---|
| R01 | Dados de pacientes versionados no Git | 2 | 5 | 10 | PROP / ARQ | Mitigado (D05); residual: branch local `historico-local` (D08 aguarda backup) e cópias locais |
| R02 | Rubrica UX/UI (R$ 6.288) sem consultoria | 5 | 3 | 15 | PROP / GP | Aberto — remanejamento em standby |
| R03 | Troca AWS → Cloudflare frente ao texto aprovado | — | — | — | ARQ / PROP | **Encerrado** por D07 (AWS São Paulo). Pendência: ADR-003 ainda descreve Cloudflare |
| R04 | Métricas fixas no código apresentadas como resultado | 2 | 4 | 8 | ENG / DS | Mitigado (`b3d3ab3b`, teste `test_honestidade_metricas.py`); manter revisão em material externo |
| R05 | Piloto sem hospital confirmado | 4 | 5 | 20 | PROP | Aberto — roteiro de entrevistas pronto |
| R06 | Atividades 1 e 2 sem evidência | 3 | 4 | 12 | PROP / GP | Reformulado: dependem do recurso (ver R18) |
| R07 | Termo de Outorga não lido | 4 | 4 | 16 | PROP / GP | Aberto — Termo assinado, cláusulas não extraídas |
| R08 | Ausência de datas na fila impede medir tempo de espera | 2 | 5 | 10 | DS | Reduzido: data de solicitação disponível na coleta JSON; significado oficial a confirmar com a SESA |
| R09 | Meta MAPE < 15% não atingida com dados reais | 2 | 4 | 8 | DS | Reduzido: atingida no total e em 13/15 especialidades a 30 d; alvo é produção SIH, não fila |
| R10 | Coleta IntegraSUS via endpoint não documentado / termos de uso | 3 | 4 | 12 | PROP / ENG | Reformulado — coleta funciona; falta respaldo institucional |
| R11 | Divergências orçamentárias PDF × planilha | 3 | 4 | 12 | PROP / contábil | Aberto |
| R12 | Concentração de atividades em M4–M6 e equipe de uma pessoa | 3 | 4 | 12 | GP | Reduzido: 3, 5, 6, 7, 9 antecipadas; gargalo migra para atividades com pessoas |
| R13 | Segredo JWT e senha padrão | 1 | 4 | 4 | ENG | Mitigado (`246f2f75`, `test_config_seguranca.py`) |
| R14 | Nomenclatura de modelos divergente (Prophet × Holt-Winters) | 1 | 2 | 2 | DS | Mitigado: função renomeada; Prophet real avaliado (`previsao-demanda-v1.md`) |
| R15 | Expansão Nordeste sem rubrica de viagens/eventos | 3 | 2 | 6 | PROP | Aberto |
| R16 | Viés algorítmico e disparidade regional na priorização | 3 | 4 | 12 | DS | Aberto — pergunta 6 no roteiro de entrevistas |
| R17 | Ambiguidade do Mês 12 | 2 | 2 | 4 | GP | Absorvido por R18 (cenário M1 = out/26 fecha 12 meses) |
| **R18** | **Início formal postergado (recurso não recebido)** | 4 | 4 | **16** | PROP / GP | **Novo** |
| **R19** | **Meta de −40% no tempo de espera sem caminho demonstrado** | 4 | 5 | **20** | DS / PROP | **Novo** — caminho em elaboração (`docs/dados/meta-40-caminho.md`) |
| **R20** | **Vínculos fila→CNES provisórios distorcem capacidade e sugestões** | 3 | 3 | 9 | DS | **Novo** — 26 CNES provisórios; HIF e Hospital São Raimundo prioritários |
| **R21** | **Coleta IntegraSUS em máquina local (perda de coletas, cópia de dado pessoal fora da nuvem)** | 4 | 3 | 12 | ENG / ARQ | **Novo** |

## Detalhamento

### R01 — Dados de pacientes versionados no Git (crítico)
- **Fato verificado:** `backend/data/consulta-fila-espera_2026-02-22_*.csv` e `_2026-02-24_*.csv` (63.495 linhas cada; colunas incluem iniciais do paciente e número de solicitação) e `backend/predmed.db` (tabela da fila e tabela de usuários com hash de senha) estão rastreados e presentes em 4 commits. `.gitignore` já tem `*.db`, mas o arquivo foi adicionado antes e continua versionado.
- **Por que importa mesmo com repositório privado:** iniciais + número de solicitação permitem reidentificação (a própria regra do `CLAUDE.md` os trata como dado pessoal); todo clone, backup, fork ou acesso de colaborador/consultoria carrega os dados; contraria o compromisso de anonimização da proposta (p. 2–3). A consultoria jurídica deve avaliar se há obrigações adicionais — não presumir.
- **Atualização 28/09/2026:** B01–B03 concluídos (D05 em `decisoes.md`): o remoto recebeu histórico novo sem os arquivos; o histórico antigo ficou só na branch local não publicada `historico-local`. Risco residual: publicação acidental dessa branch, cópias locais e clones antigos.
- **Mitigação:** B01–B03 do backlog (feitos), manter dados reais só em armazenamento restrito e criptografado, usar dados anonimizados ou sintéticos rotulados em desenvolvimento, revisar quem teve acesso ao repositório.
- **Gatilho de escalonamento:** qualquer compartilhamento do repositório com terceiros (consultorias, bolsistas) antes da limpeza.

### R02 — Rubrica UX/UI sem consultoria
- **Fato:** planilha prevê consultoria UX/UI de R$ 6.288; o responsável decidiu fazer UX internamente.
- **Risco:** gastar o valor em outra finalidade sem autorização pode gerar glosa na prestação de contas; deixar de gastar pode exigir devolução. O procedimento correto depende do Termo de Outorga e das regras da FUNCAP — **não foram lidos**.
- **Mitigação:** B08/B09 — solicitar formalmente o remanejamento **antes** de qualquer gasto diferente; registrar no relatório mensal que a rubrica está sem execução aguardando resposta. Indicadores que citavam a consultoria (wireframes, teste SUS) continuam obrigatórios e passam a ser entregues internamente.

### R03 — Troca AWS → Cloudflare frente ao texto aprovado
- **Fato:** a proposta aprovada cita AWS (EC2, RDS PostgreSQL, S3) na estratégia, na atividade de infra e na rubrica; decisão atual é infra portável com preferência por Cloudflare Workers.
- **Risco:** avaliador interpretar como mudança de escopo; limitações técnicas (Workers não roda diretamente o stack Python atual de ML/pandas; limites de CPU/memória) exigindo componente AWS mesmo assim.
- **Mitigação:** ADR (B11) mostrando que o indicador ("ambientes configurados, CI/CD, arquitetura documentada") é cumprido; manter AWS como opção real para o componente de ML; comunicar a mudança no relatório mensal; confirmar no Termo se mudança de fornecedor exige anuência.
- **Atualização 29/09/2026:** encerrado pela D07 (AWS sa-east-1, portável). Resta atualizar ADR-003 (ainda com status "Proposto" e Cloudflare preferencial).

### R04 — Métricas fixas no código
- **Fato verificado:** `backend/services/ia_engine.py:355-357` retorna `reducao_estimada_pct: 40` e `acuracia_mape: 11.2`; tela de previsões diz "MAPE < 15% - aprovado no Programa Centelha"; telas dizem "dados em tempo real".
- **Risco:** apresentar a gestores, avaliadores ou em relatório número não medido; perda de credibilidade no piloto.
- **Mitigação:** B05; qualquer captura de tela para relatório só após a correção.
- **Atualização 29/09/2026:** B05 concluído (`b3d3ab3b`); telas com selos "medido/estimado/simulado" (`f7108d5d`). Risco residual: apresentações e relatórios externos citarem o −40% ou a simulação de mutirão como resultado.

### R05 — Piloto sem hospital confirmado
- **Fato:** nenhum parceiro identificado em registro; atividade 4 (M2–M3) tem indicador "1 hospital parceiro identificado"; piloto de 90 dias em M7–M9.
- **Risco:** sem hospital, caem os indicadores das atividades 10, 12 e 14 e a comprovação de impacto.
- **Mitigação:** começar contatos em S2; mirar 2–3 candidatos; minuta de termo de cooperação pela jurídica até M4; plano B: piloto com secretaria municipal ou em modo "sombra" com dados públicos (precisa ser justificado no relatório, pois o indicador fala em hospital público).

### R06 — Atividades já no Mês 1
- **Fato:** atividades 1 (M1–M3) e 2 (M1–M2) estão em curso; não há evidência no repositório de ambiente em nuvem nem de contratos (contratos podem existir fora — a confirmar).
- **Mitigação:** registrar em S1 o que já existe; priorizar contratos (B12) e ADR (B11); relatório de M1 deve dizer exatamente o estado.
- **Atualização 29/09/2026:** com o recurso não recebido, a ausência de contratos e de conta AWS é esperada. Tratado em R18.

### R07 — Termo de Outorga não lido
- Afeta: data exata de início/fim, periodicidade e formato de relatórios, regras de remanejamento, condições da 2ª parcela, conta exclusiva, prestação de contas.
- **Mitigação:** B09 em S1. Até lá, todo documento de gestão marca essas regras como "a confirmar".
- **Atualização 29/09/2026:** Termo assinado. Extrair: data de início (Mês 1), se a vigência conta da assinatura ou do recebimento, elegibilidade de gastos anteriores, relatórios, remanejamento.

### R08 — Sem datas na fila (crítico técnico)
- **Fato verificado:** o CSV exportado do IntegraSUS não tem coluna de data; `pacientes_fila.data_insercao` está vazio em 100% dos registros.
- **Risco:** tempo de espera — critério da priorização (atividade 6) e KPI central do piloto ("redução mensurável do tempo de espera") — não é calculável.
- **Mitigação:** B17 (verificar campos da fonte/API), snapshots datados para inferir entrada/saída, B35 (linha de base) e, no piloto, obter as datas do sistema do hospital via termo de cooperação.
- **Atualização 29/09/2026:** o endpoint JSON do painel público traz o campo `data` em 100% dos 61.756 registros (coleta de 28/09), coerente com o nº de solicitação (`coleta-integrasus.md`). Tempo de espera do estoque passa a ser calculável. Residual: significado oficial não documentado; ~4,5% com numeração legada marcados "a confirmar"; saídas só observáveis por snapshots.

### R09 — MAPE < 15% não atingido
- Base SIH real (`aih_registro`) vazia na base padrão; validação atual retorna nulo.
- **Mitigação:** B13, B21, B26, B33; reportar o obtido por recorte; plano de melhoria documentado.
- **Atualização 29/09/2026:** fora da amostra, 5,1% a 30 d no total sem obstetrícia; 13/15 especialidades < 15% a 30 d (9/15 a 90 d; eletivas 9/15 a 30 d). Residual: alvo é produção SIH, não a fila; ganho sobre "repetir o último mês" é pequeno a 30 d; recorte por CIR/hospital não avaliado.

### R10 — IntegraSUS
- **Mitigação:** B17; não prometer "tempo real" se a fonte não oferece; coleta agendada com snapshots.
- **Atualização 29/09/2026:** a coleta usa o endpoint JSON do painel público 214, **não documentado**; termos de uso do portal não verificados. A nota técnica recomenda via institucional. **Mitigação:** ofício à SESA (significado de `data`, termos de uso, acesso ao painel restrito 232); manter frequência baixa (2×/dia) e User-Agent identificado; plano B por termo de cooperação no piloto.

### R11 — Divergências orçamentárias
- PDF: capital R$ 0; consultorias de ML (16.000) e integração (10.000); infra como material de consumo. Planilha: capital R$ 29.712 (computador), sem ML/integração, infra em custeio PJ.
- Computador (R$ 29.712) equivale a ~69% da subvenção da 1ª parcela (R$ 42.876), limitando custeio no 1º semestre. **A confirmar:** se a planilha é a versão aprovada/contratada e qual fonte (FINEP ou FUNCAP) cobre capital.
- **Mitigação:** conciliar com a contabilidade antes do primeiro gasto; cronograma de desembolso por rubrica.

### R12 — Concentração M4–M6 e equipe enxuta
- Cinco atividades técnicas em paralelo, desenvolvimento central pelo proponente. Bolsas CNPq (R$ 50.000) podem ampliar a equipe — situação a confirmar.
- **Mitigação:** antecipar em M2–M3 tudo que não depende de dados (CI, testes, exportação, mapa); dividir trabalho entre agentes; definir escopo mínimo apto ao piloto.
- **Atualização 29/09/2026:** previsão, priorização, redistribuição e coleta avançaram antes do M1. O gargalo passa a ser o que depende de terceiros (entrevistas, hospital, contratos, revisão clínica/jurídica).

### R13 — Segurança de autenticação
- `backend/auth.py:14` usa valor padrão para `SECRET_KEY`; `seed.py` cria usuários com senha comum. **Mitigação:** B04 antes de qualquer ambiente acessível pela internet.
- **Atualização 29/09/2026:** B04 concluído (`246f2f75`).

### R14 — Nomenclatura dos modelos
- Proposta cita Prophet, ARIMA e XGBoost; código usa Holt-Winters sob nomes "Prophet". **Mitigação:** B05 e B33; relatório técnico descreve o modelo efetivamente usado.
- **Atualização 29/09/2026:** mitigado; relatório técnico descreve os modelos escolhidos por série.

### R15 — Eventos e viagens
- A atividade 16 cita HIMSS e Hospitalar; não há rubrica de diárias/passagens na planilha. **Mitigação:** prospecção remota ou custeio fora do projeto; confirmar com a FUNCAP antes de usar recursos.

### R16 — Viés algorítmico
- Mitigação prevista na proposta: auditoria periódica dos critérios e monitoramento de disparidades por região. Incluir em B34/B37 testes por região.

### R17 — Mês 12
- Contagem set/2026–set/2027 depende da data de início da vigência. **Mitigação:** B09.
- **Atualização 29/09/2026:** absorvido por R18.

### R18 — Início formal postergado (novo, 29/09/2026)
- **Fato:** Termo com a FUNCAP assinado; recurso não recebido. Execução formal só após o recebimento; Mês 1 possivelmente out/2026 (a confirmar no Termo).
- **Riscos:** (a) cronograma deslizar sem registro formal, gerando divergência entre plano e prestação de contas; (b) compressão de M1–M3 se a vigência correr da assinatura e o dinheiro chegar tarde (contratos e AWS atrasam); (c) trabalho e gastos de setembro não serem elegíveis como execução ou contrapartida.
- **Mitigação:** extrair do Termo a regra de início (assinatura × recebimento); registrar a data de recebimento como evento; relatório de setembro declarado **preparatório e com zero despesa** (`relatorios/2026-09-relatorio-mensal.md`); não pagar nada do projeto antes do crédito na conta; preparar contratos (minutas) e conta AWS para acionar no dia do crédito; se o atraso passar de 30 dias, consultar a FUNCAP sobre ajuste de cronograma.
- **Gatilho:** recurso não recebido até 31/10/2026.

### R19 — Meta de −40% no tempo de espera (novo, 29/09/2026)
- **Fato:** a meta da proposta não é medida por nada hoje. A simulação de mutirão de 90 dias com a regra "mesma CIR" redistribui 1.768 de 61.756 pedidos (2,9%) — **simulado**. A pressão está concentrada em Maracanaú (7,4) e Fortaleza (5,8), e a ociosidade estimada do interior não alcança a capital pela regra da CIR (`redistribuicao-v1.md`).
- **Riscos:** meta inalcançável no desenho atual; ou afirmada sem medição, com dano à credibilidade na prestação de contas.
- **Mitigação:** documento do caminho em elaboração pelo cientista de dados (`docs/dados/meta-40-caminho.md` — **em elaboração**, não lido nesta revisão); levar às entrevistas a decisão política de redistribuir fora da CIR e a calibração dos parâmetros; definir no piloto o recorte e a linha de base (data de entrada e saída) antes de iniciar; reportar resultado obtido por recorte, mesmo abaixo da meta.
- **Gatilho:** caminho sem cenário plausível ≥ 40% até o fim de M3 → propor à FUNCAP redação da meta como alvo de recorte (ex.: especialidade × CIR do piloto).

### R20 — Vínculos fila→CNES provisórios (novo)
- **Fato:** D12 aceitou vínculos MEDIA/AMBÍGUO/BAIXA como provisórios (26 CNES; 14 sugestões, 173 pacientes/mês). "Hospital Infantil Lúcia de Fátima (HIF)" provavelmente com sugestão errada; "Hospital São Raimundo" ambíguo entre Crato e Várzea Alegre.
- **Mitigação:** revisão manual (alias `fonte = manual`) priorizando os dois casos; confirmar nas entrevistas com a SESA/SMS; sugestões com vínculo provisório continuam sinalizadas.

### R21 — Coleta IntegraSUS em máquina local (novo)
- **Fato:** agendamento launchd no Mac às 7h e 19h; se o Mac estiver desligado, a coleta é perdida; arquivos criptografados (Fernet) fora do Git; chave em `~/.predmed/`.
- **Mitigação:** cópia da chave em gerenciador de senhas; FileVault ativo; migrar para AWS (agendamento + S3 criptografado) logo após a conta existir; monitorar lacunas no manifesto.

## Histórico

| Data | Alteração |
|---|---|
| 28/09/2026 | Criação (R01–R17) |
| 29/09/2026 | Rev. 2: R03 encerrado (D07); R04, R08, R09, R13, R14 reduzidos com evidência; R10 reformulado; R17 absorvido; novos R18 (início postergado), R19 (meta −40%), R20 (vínculos CNES), R21 (coleta local) |
