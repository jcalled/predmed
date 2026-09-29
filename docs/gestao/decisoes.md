# PREDMED — Registro de decisões

Versão: 28/09/2026. Mantido pelo gerente de projetos (agente); **decisões são do proponente**. Item B07 do `backlog.md`.

## Como usar

- Uma linha por decisão, nunca apagar. Decisão revista ganha nova linha que **substitui** a anterior (coluna "Situação": "substituída por Dxx").
- Situações: **Tomada** (vale a partir da data), **Executada** (tomada e com evidência verificável), **Pendente** (aguarda decisão do proponente), **Proposta** (recomendação de agente, ainda não aprovada).
- Nada de dados pessoais, senhas ou conteúdo de contratos aqui; só referências a locais restritos.
- Numeração: `Dxx` neste registro. As decisões do checklist mantêm o código original com prefixo **CK-** (CK-R01 a CK-R06) para não confundir com os riscos R01–R06 de `riscos.md`.
- Toda decisão que altere escopo, fornecedor ou rubrica aprovada deve ser verificada contra o Termo de Outorga (B09, ainda não lido) e, se preciso, comunicada à FUNCAP.

## 1. Decisões tomadas e executadas

| ID | Data | Decisão | Quem decidiu | Justificativa | Situação | Próxima ação |
|---|---|---|---|---|---|---|
| D01 | 28/09/2026 | Repositório GitHub do projeto é **privado** | Proponente | Código e documentação de sistema para governo/saúde; proteção da propriedade intelectual antes do registro no INPI (atividade 13) | Tomada | Revisar periodicamente quem tem acesso; conceder acesso a consultorias/bolsistas só após contrato com cláusula de confidencialidade |
| D02 | 28/09/2026 | **UX/UI feito internamente** (proponente + agente `designer-ux-ui`), sem contratar consultoria | Proponente | Capacidade interna para wireframes, interface e teste de usabilidade; mantém as metas do plano (wireframes aprovados, teste com 5 gestores, SUS > 70) | Tomada — **remanejamento em standby (28/09/2026)**: proponente avalia outro destino antes de enviar | Enviar à FUNCAP a solicitação de remanejamento (minuta em `minuta-remanejamento-ux.md`, B08); **não gastar os R$ 6.288,00 em outra finalidade antes da resposta**; conferir regra de remanejamento no Termo (B09) |
| D03 | 28/09/2026 | **Infraestrutura portável**, com preferência por Cloudflare; nenhum componente acoplado a um único provedor sem camada de abstração | Proponente | Custo, simplicidade de operação na borda e possibilidade de trocar de provedor; a proposta aprovada citava AWS (EC2/RDS/S3) | **Substituída por D07** (preferência por Cloudflare revista; portabilidade mantida) | Ver D07 |
| D04 | 28/09/2026 | Para **cronograma e orçamento**, a planilha xlsx (plano de trabalho atualizado) **prevalece** sobre o PDF da proposta; o PDF continua valendo para metas, indicadores, descrição do produto e riscos | Proponente | A planilha é a versão atualizada do plano; o PDF tem datas e rubricas anteriores | Tomada | Marcar `docs/CHECKLIST_CONCLUSAO.md` como "versão PDF" ou atualizá-lo (ver seção 5 de `roadmap.md`); confirmar no Termo qual versão do plano é a oficial (CK-R01) |
| D05 | 28/09/2026 | **Publicação do repositório com histórico novo e limpo**: o remoto (`origin`, GitHub privado) estava vazio e recebeu apenas o código-fonte e a documentação, sem dados de pacientes, sem `venv/`, `node_modules/`, `.next/` nem bancos (`*.db`). O histórico antigo, que continha esses arquivos, foi preservado **somente** na branch local `historico-local`, **não publicada** | Proponente (execução com apoio de agente) | Resolve a exposição de dados pessoais e os ~35 mil arquivos de dependências versionados sem precisar reescrever histórico nem fazer push forçado, porque nada tinha sido publicado antes | **Executada** | Ver evidência e ações remanescentes logo abaixo |

### Evidência da D05 (verificada em 28/09/2026, somente leitura)

- `origin/main` tem 2 commits: `afb1eebf` (versão inicial limpa) e `6f666217` (inclusão do código do frontend, antes em repositório Git aninhado). Árvore publicada: 77 arquivos.
- `git ls-tree -r origin/main` não lista `*.db`, `*.csv` de fila, `venv/`, `node_modules/`, `.next/`, `__pycache__`, `.DS_Store` nem `lightning_logs/`.
- `git log origin/main -- '*.db' 'backend/data/*.csv'` não retorna commits.
- A branch `historico-local` (ponta `c1f4f443`) não é ancestral de `origin/main` e não tem correspondente remoto.

Observação: a instrução original falava em "um único commit limpo"; o remoto tem dois commits, ambos limpos pela verificação acima. Não altera a conclusão.

### Ações remanescentes da D05 (não bloqueiam o encerramento de B01–B03)

1. **Nunca publicar** a branch `historico-local` (`git push --all` ou `git push origin historico-local` reexporiam os dados). Avaliar movê-la para um backup criptografado fora do diretório de trabalho e apagá-la do repositório local — decisão do proponente.
2. Guardar as cópias reais de `backend/predmed.db` e dos CSV de fila apenas em local restrito e criptografado; documentar o procedimento de carga sem dados (B01, critério residual).
3. Confirmar que `.gitignore` cobre `*.db`, CSV de fila, `venv/`, `node_modules/`, `.next/` (tarefa do engenheiro na branch de Sprint 1).
4. Descartar cópias/clones antigos que tenham o histórico com dados, se existirem fora desta máquina.
5. Confirmar que `./start.sh` funciona num clone limpo do remoto (critério de aceite de B03) — a registrar como evidência quando executado.

## 2. Decisões propostas (aguardando aprovação)

| ID | Data | Proposta | Quem propôs | Justificativa | Situação | Próxima ação |
|---|---|---|---|---|---|---|
| D06 | 28/09/2026 | **Arranjo híbrido**: Cloudflare na borda e no frontend (CDN, DNS, TLS, WAF, hospedagem do Next.js); API, banco de dados e arquivos que contenham dados pessoais hospedados em **região de São Paulo** | Agente `arquiteto-sistemas` | Residência dos dados pessoais no Brasil (LGPD, expectativa de órgãos públicos); o stack Python de ML/pandas não roda diretamente em Workers; mantém a preferência por Cloudflare (D03) onde ela não envolve dados pessoais | **Rejeitada — substituída por D07** | — (histórico: proponente aprovaria ou rejeitaria; se aprovar, formalizar no ADR (B11) com provedor e serviços da região SP, custos contra a rubrica de nuvem/APIs (R$ 9.552,00) e pedido de revisão da consultoria jurídica (LGPD) |
| D07 | 28/09/2026 | **Nuvem principal: AWS, região São Paulo (sa-east-1)** para API, banco PostgreSQL, arquivos e jobs de ETL/ML. Aplicação continua **portável** (Docker, PostgreSQL padrão, armazenamento compatível com S3, configuração por variáveis de ambiente) | Proponente | AWS fatura clientes brasileiros com **nota fiscal brasileira**, o que simplifica a prestação de contas; coincide com o texto aprovado (EC2/RDS/S3), dispensando justificar troca de fornecedor; dados pessoais permanecem no Brasil | Tomada | Arquiteto atualiza ADR-003 e visão geral; estimar custo mensal contra a rubrica de nuvem/APIs (R$ 9.552,00 ≈ R$ 796/mês); criar conta AWS no CNPJ da empresa com faturamento pela AWS Serviços Brasil |
| D08 | 28/09/2026 | Branch local **`historico-local`** (contém dados de pacientes do histórico antigo) será arquivada junto ao backup dos bancos e depois **removida do repositório local**; nunca publicada | Proponente | Reduz cópias de dados pessoais; o histórico antigo não é necessário para o desenvolvimento | Aprovada — **aguarda local do backup** | Gerar `git bundle` da branch no local de backup, verificar integridade, então apagar a branch local |

## 3. Decisões pendentes do checklist (`docs/CHECKLIST_CONCLUSAO.md`, seção R)

| ID | Decisão a tomar | Estado no checklist | Quem decide | Próxima ação | Item do backlog |
|---|---|---|---|---|---|
| CK-R01 | Confirmar cronograma e escopo vigentes (versão do plano e do Termo de Outorga; mudanças aprovadas) | A confirmar | Proponente | Fornecer o Termo de Outorga; GP extrai vigência, relatórios e regra de remanejamento. D04 já fixa a planilha como referência interna, mas falta confirmar a versão oficial junto à FUNCAP | B09 |
| CK-R02 | Definir versão e ambiente de referência (repositório, revisão, banco ativo, uso da base de backup) | A confirmar — **parcialmente resolvida** por D05 (repositório e revisão de referência: `origin/main`) | Proponente + ARQ | Decidir qual banco alimenta o MVP após a reconciliação de `predmed.db` × `predmed-original.db`, sem sobrescrever bases | B13 |
| CK-R03 | Fixar o objeto da previsão (produção cirúrgica, entradas ou estoque da fila; unidade, recortes, horizontes 30/60/90 dias) | Pendente | Proponente, com DS | DS redige a especificação; proponente aprova | B14 |
| CK-R04 | Alinhar os modelos ao plano (Prophet/ARIMA/XGBoost do PDF × Holt-Winters atual) e ver se a mudança precisa ser formalizada | Pendente | Proponente, com DS | DS entrega plano comparativo com critérios de seleção; parar de chamar Holt-Winters de "Prophet" (B05) | B33, B05 |
| CK-R05 | Definir o modo de apoio à decisão (sem regulação, transferência ou AIH; quem revisa/aprova recomendações) | Parcial (regra já no `CLAUDE.md`) | Proponente | Registrar aqui quem revisa e aprova recomendações no piloto; refletir na UI e no termo de cooperação | B34, B41 |
| CK-R06 | Confirmar entregas externas (empresa, contratos, conta, cloud, entrevistas, parceiros, comprovantes) | A confirmar | Proponente | Inventário com referências a locais restritos (sem conteúdo no Git); priorizar CNPJ/conta exclusiva e contratos da atividade 2 | B12, B16 |

## 4. Histórico deste registro

| Data | Alteração | Autor |
|---|---|---|
| 28/09/2026 | Criação: D01–D05, proposta D06, pendências CK-R01 a CK-R06 | Gerente de projetos (agente) |
| 28/09/2026 | D02 em standby; D03 e D06 substituídas por D07 (AWS São Paulo); D08 aprovada | Proponente |
