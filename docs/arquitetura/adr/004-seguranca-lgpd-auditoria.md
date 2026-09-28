# ADR-004 — Segurança, LGPD e trilha de auditoria

- **Status:** Proposto
- **Data:** 28/09/2026
- **Checklist operacional:** [seguranca-lgpd.md](../seguranca-lgpd.md)
- **Aviso:** esta ADR descreve controles técnicos; não é parecer jurídico. Base legal, RIPD e contratos devem ser validados pelo consultor jurídico previsto no plano.

## Contexto

- A proposta promete "conformidade com LGPD desde o início: anonimização dos dados, criptografia em trânsito e em repouso, contratos de processamento", além de modo somente leitura/apoio à decisão e auditoria periódica de algoritmos (viés).
- Estado atual (diagnóstico): segredo JWT padrão (D03), vazamento entre tenants (D02), dados pessoais no git (D01), importação destrutiva (D04), sem auditoria (D07), upload inseguro (D06), `torch.load` inseguro (D05).
- Dados tratados:
  - **fila IntegraSUS**: iniciais, nº de solicitação, município, unidade, procedimento, especialidade, SWALIS, judicialização. É **dado pessoal sensível** (saúde, art. 5º, II), porque iniciais + nº de solicitação + unidade permitem reidentificação;
  - **SIH/AIH**: dado público do DATASUS, mas com quase-identificadores (nascimento, CEP, município, CID);
  - **usuários**: nome, e-mail e instituição dos gestores.

## Decisão

### 1. Papéis LGPD e documentação

- Por padrão, a empresa atua como **operadora** para os dados de fila fornecidos ou autorizados pela instituição, que é a **controladora**. Formalizar em contrato ou termo de tratamento com cada instituição (proposta: "contratos de processamento com todas as instituições parceiras").
- Manter o **registro das operações** (art. 37) e um **RIPD** para o piloto em `docs/dados/` (sem dados reais). Nomear encarregado (DPO) ou canal equivalente.

### 2. Minimização e pseudonimização

- **Na ingestão** (job ETL, nunca na API):
  - `NUN_SOLICITACAO` → `id_solicitacao_hash = HMAC-SHA256(chave_por_ambiente, valor)`. A chave fica no gerenciador de segredos. Permite deduplicar snapshots sem guardar o número;
  - `INIC_NOME_PACIENTE` armazenado apenas se a instituição precisar da conferência operacional. Se armazenado, fica em coluna separada, exibida somente a papéis autorizados **do próprio hospital ou gestor responsável**. Caso contrário, é descartado;
  - `POSICAO_FILA` mantida (não identifica sozinha);
  - SIH: no modelo analítico, `nasc` → faixa etária, `cep` descartado, `n_aih` descartado ou transformado em hash.
- **Nos modelos de ML**: treino apenas sobre agregados mensais (especialidade × hospital/CIR). Nenhum identificador ou iniciais entra no pipeline de treino. É a "anonimização nos modelos" da proposta.
- **Supressão de pequenas células**: agregados com n < 5 exibidos como "< 5" em telas com recorte por hospital e procedimento.
- Arquivos brutos (CSV) com retenção curta no armazenamento de objetos (ver checklist) e **nunca** no git.

### 3. Isolamento multi-tenant e RBAC

- Modelo de escopo:
  - `sesa`: estado;
  - `sms`: `municipio_gestor` (e CIR, se pactuado);
  - `hospital_publico`: seus CNES;
  - `hospital_particular`: **sem acesso a dados individuais de fila**, só agregados da sua CIR e ofertas de vagas.
- Vínculo por **CNES** (tabela `tenant_estabelecimento`), nunca por substring de nome (`main.py:213-214` hoje).
- Escopo aplicado **no repositório** (ADR-001). Testes automatizados de acesso permitido e negado por papel, para cada rota que retorna dado de paciente (checklist T07).
- Defesa em profundidade opcional: Row-Level Security do Postgres com `SET app.escopo`. Avaliar depois de estabilizar.

### 4. Autenticação e sessão

- `SECRET_KEY` obrigatória e forte fora de dev (a aplicação não inicia sem ela). Rotação documentada.
- Access token curto (15–30 min) e refresh token rotativo. Cookie `HttpOnly; Secure; SameSite=Strict` no lugar de `localStorage`. JWT sem dados pessoais além do `sub`.
- Rate limit e bloqueio progressivo no login (na borda e na API). MFA (TOTP) para papéis `sesa` e administradores antes do piloto.
- Contas demo e seed **somente em dev**. Senha individual e troca obrigatória no primeiro acesso.
- Substituir `python-jose` por `PyJWT`. Fixar dependências e rodar `pip-audit`/`npm audit` no CI.

### 5. Trilha de auditoria

- Tabela `app.auditoria`, **somente inserção** (papel de banco sem `UPDATE`/`DELETE`), com: `id`, `ocorrido_em` (UTC), `usuario_id`, `tenant_id`, `papel`, `acao`, `recurso`, `recurso_id`, `escopo`, `ip_hash`, `user_agent`, `request_id`, `resultado`, `motivo`, `dados_antes`/`dados_depois` (JSON **sem** dado de paciente), `hash_anterior` (encadeamento para detectar adulteração).
- Ações auditadas: login (sucesso e falha), logout, emissão de token, **consulta a listas com dado de paciente** (fila, judicializados, priorização: registrar filtros e quantidade, não os registros), importação, configuração de vagas, **revisão de recomendação** (aceita/rejeitada/ajustada, com justificativa), exportações, mudanças de usuário e papel.
- **Modo apoio à decisão:** `POST /redistribuicao/aprovar` passa a registrar "recomendação revisada pelo gestor" (`status`: `recomendada` → `aceita_para_encaminhamento` | `rejeitada`), com texto explícito de que **não executa transferência, regulação nem emissão de AIH**.
- Retenção da auditoria: mínimo de 5 anos (a confirmar com o jurídico e o cliente). Exportável para a instituição controladora.
- **Auditoria de algoritmo** (mitigação de viés prometida): cada versão de modelo e de regra de priorização registrada com parâmetros, dados de treino (período e fonte) e métricas por região/CIR. Relatório periódico de disparidades.

### 6. Criptografia e infraestrutura

- Em trânsito: TLS 1.2+ na borda; `sslmode=require` (ou `verify-full`) no Postgres; HTTPS para objetos; HSTS.
- Em repouso: criptografia nativa do Postgres gerenciado e do S3/R2. Backups criptografados. Disco local da API sem dado persistente.
- Segredos só no gerenciador (Workers Secrets/Secrets Store, AWS Secrets Manager/SSM) e GitHub Environments. `gitleaks` no CI e em pre-commit.
- Uploads: nome gerado pelo servidor (UUID), limite de tamanho, validação de tipo e esquema, armazenamento no bucket (não em `/tmp`), job assíncrono e remoção do arquivo bruto ao fim da retenção.
- Remover o patch global `weights_only=False` (`previsoes_ml.py:25-30`). Se torch for mantido, carregar apenas checkpoints próprios, verificados por hash.
- `/docs` e `/openapi.json` desabilitados em produção ou protegidos. `/health` sem contagens (só `status`).

### 7. Logs e observabilidade

- Logs JSON em stdout com `request_id`, rota, status, latência, `usuario_id` e `tenant_id`. **Proibido** logar corpo de requisição/resposta, iniciais, nº de solicitação ou CSV. Filtro de mascaramento em `core/logging.py`.
- Retenção de logs de aplicação: 90 dias (ajustável). Log de auditoria segue o item 5.

### 8. Backup, restauração e incidentes

- PITR do Postgres (mínimo 7 dias) e snapshot diário retido por 30 dias. Snapshot manual antes de cada migração em produção.
- **Teste de restauração** trimestral em ambiente isolado, com evidência registrada (checklist "backup/restauração", item transversal do checklist).
- Plano de resposta a incidentes com comunicação à controladora e fluxo de apoio para comunicação à ANPD e aos titulares (art. 48), com contatos definidos.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Anonimização total da fila (descartar iniciais e nº) | Ideal para o modelo, mas impede conferência operacional pelo hospital. Adotada para ML e agregados; iniciais ficam opcionais e restritas |
| Criptografia de coluna na aplicação para iniciais | Pode ser somada depois; hoje o maior risco é o acesso indevido pela API, resolvido por escopo e RBAC |
| Auditoria só em logs | Logs têm retenção curta e não são consultáveis pela instituição; auditoria precisa ser dado de negócio |

## Consequências

- Mais trabalho antes do piloto (estimativa: 1,5–2 semanas para escopo, auditoria, sessão e pseudonimização).
- Algumas telas mudam: o hospital privado deixa de ver lista nominal da fila; "Aprovar" vira "Registrar revisão".
- Base documental para o jurídico e para a comprovação da atividade 2 da Etapa 1 ("arquitetura de segurança conforme LGPD").
