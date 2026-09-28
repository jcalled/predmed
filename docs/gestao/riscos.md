# PREDMED — Matriz de riscos

Versão: 28/09/2026 (Mês 1). Revisar a cada sprint (quinzenal) e no relatório mensal.

Escala: Probabilidade (P) e Impacto (I) de 1 (baixo) a 5 (muito alto). Exposição = P × I. **Crítico ≥ 15**, alto 10–14, médio 5–9, baixo < 5.

Este documento não é parecer jurídico. Onde a mitigação depende de norma (LGPD, regras da FUNCAP/FINEP, Termo de Outorga), a ação indicada é consultar o instrumento ou o profissional competente.

## Resumo

| ID | Risco | P | I | Exp. | Dono | Status |
|---|---|---|---|---|---|---|
| R01 | Dados de pacientes versionados no Git | 5 | 5 | 25 | PROP / ARQ | Aberto — ativo hoje |
| R02 | Rubrica UX/UI (R$ 6.288) sem consultoria | 5 | 3 | 15 | PROP / GP | Aberto |
| R03 | Troca AWS → Cloudflare frente ao texto aprovado | 4 | 3 | 12 | ARQ / PROP | Aberto |
| R04 | Métricas fixas no código apresentadas como resultado | 5 | 4 | 20 | ENG / DS | Aberto — ativo hoje |
| R05 | Piloto sem hospital confirmado | 4 | 5 | 20 | PROP | Aberto |
| R06 | Atividades 1 e 2 já em curso no Mês 1 sem evidência | 4 | 4 | 16 | PROP / GP | Aberto |
| R07 | Termo de Outorga não lido | 4 | 4 | 16 | PROP / GP | Aberto |
| R08 | Ausência de datas na fila impede medir tempo de espera | 5 | 5 | 25 | DS | Aberto |
| R09 | Meta MAPE < 15% não atingida com dados reais | 3 | 4 | 12 | DS | Aberto |
| R10 | API IntegraSUS indisponível ou sem "tempo real" | 3 | 4 | 12 | ENG | Aberto |
| R11 | Divergências orçamentárias PDF × planilha | 3 | 4 | 12 | PROP / contábil | Aberto |
| R12 | Concentração de atividades em M4–M6 e equipe de uma pessoa | 4 | 4 | 16 | GP | Aberto |
| R13 | Segredo JWT e senha padrão | 4 | 4 | 16 | ENG | Aberto |
| R14 | Nomenclatura de modelos divergente (Prophet × Holt-Winters) | 5 | 2 | 10 | DS | Aberto |
| R15 | Expansão Nordeste sem rubrica de viagens/eventos | 3 | 2 | 6 | PROP | Aberto |
| R16 | Viés algorítmico e disparidade regional na priorização | 3 | 4 | 12 | DS | Aberto |
| R17 | Ambiguidade do Mês 12 (set/2026–set/2027 = 13 meses civis) | 3 | 2 | 6 | GP | Aberto |

## Detalhamento

### R01 — Dados de pacientes versionados no Git (crítico)
- **Fato verificado:** `backend/data/consulta-fila-espera_2026-02-22_*.csv` e `_2026-02-24_*.csv` (63.495 linhas cada; colunas incluem iniciais do paciente e número de solicitação) e `backend/predmed.db` (tabela da fila e tabela de usuários com hash de senha) estão rastreados e presentes em 4 commits. `.gitignore` já tem `*.db`, mas o arquivo foi adicionado antes e continua versionado.
- **Por que importa mesmo com repositório privado:** iniciais + número de solicitação permitem reidentificação (a própria regra do `CLAUDE.md` os trata como dado pessoal); todo clone, backup, fork ou acesso de colaborador/consultoria carrega os dados; contraria o compromisso de anonimização da proposta (p. 2–3). A consultoria jurídica deve avaliar se há obrigações adicionais — não presumir.
- **Mitigação:** B01–B03 do backlog (tirar do índice, decidir reescrita do histórico, descartar clones), manter dados reais só em armazenamento restrito e criptografado, usar dados anonimizados ou sintéticos rotulados em desenvolvimento, revisar quem teve acesso ao repositório.
- **Gatilho de escalonamento:** qualquer compartilhamento do repositório com terceiros (consultorias, bolsistas) antes da limpeza.

### R02 — Rubrica UX/UI sem consultoria
- **Fato:** planilha prevê consultoria UX/UI de R$ 6.288; o responsável decidiu fazer UX internamente.
- **Risco:** gastar o valor em outra finalidade sem autorização pode gerar glosa na prestação de contas; deixar de gastar pode exigir devolução. O procedimento correto depende do Termo de Outorga e das regras da FUNCAP — **não foram lidos**.
- **Mitigação:** B08/B09 — solicitar formalmente o remanejamento **antes** de qualquer gasto diferente; registrar no relatório mensal que a rubrica está sem execução aguardando resposta. Indicadores que citavam a consultoria (wireframes, teste SUS) continuam obrigatórios e passam a ser entregues internamente.

### R03 — Troca AWS → Cloudflare frente ao texto aprovado
- **Fato:** a proposta aprovada cita AWS (EC2, RDS PostgreSQL, S3) na estratégia, na atividade de infra e na rubrica; decisão atual é infra portável com preferência por Cloudflare Workers.
- **Risco:** avaliador interpretar como mudança de escopo; limitações técnicas (Workers não roda diretamente o stack Python atual de ML/pandas; limites de CPU/memória) exigindo componente AWS mesmo assim.
- **Mitigação:** ADR (B11) mostrando que o indicador ("ambientes configurados, CI/CD, arquitetura documentada") é cumprido; manter AWS como opção real para o componente de ML; comunicar a mudança no relatório mensal; confirmar no Termo se mudança de fornecedor exige anuência.

### R04 — Métricas fixas no código
- **Fato verificado:** `backend/services/ia_engine.py:355-357` retorna `reducao_estimada_pct: 40` e `acuracia_mape: 11.2`; tela de previsões diz "MAPE < 15% - aprovado no Programa Centelha"; telas dizem "dados em tempo real".
- **Risco:** apresentar a gestores, avaliadores ou em relatório número não medido; perda de credibilidade no piloto.
- **Mitigação:** B05; qualquer captura de tela para relatório só após a correção.

### R05 — Piloto sem hospital confirmado
- **Fato:** nenhum parceiro identificado em registro; atividade 4 (M2–M3) tem indicador "1 hospital parceiro identificado"; piloto de 90 dias em M7–M9.
- **Risco:** sem hospital, caem os indicadores das atividades 10, 12 e 14 e a comprovação de impacto.
- **Mitigação:** começar contatos em S2; mirar 2–3 candidatos; minuta de termo de cooperação pela jurídica até M4; plano B: piloto com secretaria municipal ou em modo "sombra" com dados públicos (precisa ser justificado no relatório, pois o indicador fala em hospital público).

### R06 — Atividades já no Mês 1
- **Fato:** atividades 1 (M1–M3) e 2 (M1–M2) estão em curso; não há evidência no repositório de ambiente em nuvem nem de contratos (contratos podem existir fora — a confirmar).
- **Mitigação:** registrar em S1 o que já existe; priorizar contratos (B12) e ADR (B11); relatório de M1 deve dizer exatamente o estado.

### R07 — Termo de Outorga não lido
- Afeta: data exata de início/fim, periodicidade e formato de relatórios, regras de remanejamento, condições da 2ª parcela, conta exclusiva, prestação de contas.
- **Mitigação:** B09 em S1. Até lá, todo documento de gestão marca essas regras como "a confirmar".

### R08 — Sem datas na fila (crítico técnico)
- **Fato verificado:** o CSV exportado do IntegraSUS não tem coluna de data; `pacientes_fila.data_insercao` está vazio em 100% dos registros.
- **Risco:** tempo de espera — critério da priorização (atividade 6) e KPI central do piloto ("redução mensurável do tempo de espera") — não é calculável.
- **Mitigação:** B17 (verificar campos da fonte/API), snapshots datados para inferir entrada/saída, B35 (linha de base) e, no piloto, obter as datas do sistema do hospital via termo de cooperação.

### R09 — MAPE < 15% não atingido
- Base SIH real (`aih_registro`) vazia na base padrão; validação atual retorna nulo.
- **Mitigação:** B13, B21, B26, B33; reportar o obtido por recorte; plano de melhoria documentado.

### R10 — IntegraSUS
- **Mitigação:** B17; não prometer "tempo real" se a fonte não oferece; coleta agendada com snapshots.

### R11 — Divergências orçamentárias
- PDF: capital R$ 0; consultorias de ML (16.000) e integração (10.000); infra como material de consumo. Planilha: capital R$ 29.712 (computador), sem ML/integração, infra em custeio PJ.
- Computador (R$ 29.712) equivale a ~69% da subvenção da 1ª parcela (R$ 42.876), limitando custeio no 1º semestre. **A confirmar:** se a planilha é a versão aprovada/contratada e qual fonte (FINEP ou FUNCAP) cobre capital.
- **Mitigação:** conciliar com a contabilidade antes do primeiro gasto; cronograma de desembolso por rubrica.

### R12 — Concentração M4–M6 e equipe enxuta
- Cinco atividades técnicas em paralelo, desenvolvimento central pelo proponente. Bolsas CNPq (R$ 50.000) podem ampliar a equipe — situação a confirmar.
- **Mitigação:** antecipar em M2–M3 tudo que não depende de dados (CI, testes, exportação, mapa); dividir trabalho entre agentes; definir escopo mínimo apto ao piloto.

### R13 — Segurança de autenticação
- `backend/auth.py:14` usa valor padrão para `SECRET_KEY`; `seed.py` cria usuários com senha comum. **Mitigação:** B04 antes de qualquer ambiente acessível pela internet.

### R14 — Nomenclatura dos modelos
- Proposta cita Prophet, ARIMA e XGBoost; código usa Holt-Winters sob nomes "Prophet". **Mitigação:** B05 e B33; relatório técnico descreve o modelo efetivamente usado.

### R15 — Eventos e viagens
- A atividade 16 cita HIMSS e Hospitalar; não há rubrica de diárias/passagens na planilha. **Mitigação:** prospecção remota ou custeio fora do projeto; confirmar com a FUNCAP antes de usar recursos.

### R16 — Viés algorítmico
- Mitigação prevista na proposta: auditoria periódica dos critérios e monitoramento de disparidades por região. Incluir em B34/B37 testes por região.

### R17 — Mês 12
- Contagem set/2026–set/2027 depende da data de início da vigência. **Mitigação:** B09.
