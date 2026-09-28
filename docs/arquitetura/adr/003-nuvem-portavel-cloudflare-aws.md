# ADR-003 — Nuvem portátil: Cloudflare preferencial, compatível com AWS

- **Status:** Proposto. Requer decisão do responsável e, possivelmente, comunicação à FUNCAP.
- **Data:** 28/09/2026
- **Fontes consultadas:** documentação da Cloudflare em developers.cloudflare.com, lida em 28/09/2026: Python Workers e pacotes, Workers limits, Containers (visão geral, limits, pricing, architecture), Hyperdrive, Workflows limits, R2 data location, Data Localization Suite (visão geral e region support). Preços da AWS **não** foram consultados nesta rodada; os valores são estimativas a confirmar na AWS Pricing Calculator.

## Contexto

- A proposta aprovada descreve "Infraestrutura AWS (EC2, RDS PostgreSQL, S3)" e CI/CD no GitHub Actions (Etapa 1, atividade 2). A rubrica de material de consumo prevê **R$ 796/mês × 12 = R$ 9.552**, que cobre "infraestrutura AWS (...), licenças de software, ferramentas de desenvolvimento e APIs de terceiros". Ou seja, **não é tudo para nuvem**.
- O responsável prefere **Cloudflare Workers**, mantendo compatibilidade com AWS.
- Stack real: FastAPI + SQLAlchemy + **pandas, numpy, statsmodels**. Hoje também torch/NeuralProphet e Prophet, que podem ser retirados da API. O ETL do SIH lida com arquivos `.dbc` (218 MB) e com um banco de GBs.
- Os dados incluem fila com **iniciais + nº de solicitação** (dado pessoal) e AIH com quase-identificadores. Clientes são órgãos públicos de saúde do Ceará.

## O que a documentação da Cloudflare diz (set/2026)

| Tema | Achado | Implicação para o PREDMED |
|---|---|---|
| **Python Workers** | Rodam sobre Pyodide (WebAssembly). Suportam pacotes "pure Python" e wheels PyEmscripten/incluídos no Pyodide; a própria doc diz que o suporte WebAssembly a pacotes "ainda está em estágio inicial". Exigem a flag `python_workers`. FastAPI aparece como exemplo. | pandas/numpy existem no ecossistema Pyodide, mas **statsmodels, prophet, torch e drivers Postgres nativos (psycopg) não têm suporte garantido**. SQLAlchemy síncrono com driver TCP não é o modelo do runtime. |
| **Limites de Workers (Paid)** | 128 MB de memória por isolate; CPU até 5 min por requisição (padrão 30 s); 64 MiB de tamanho do Worker; 1 s de inicialização do escopo global; Cron: 30 s de CPU (intervalo < 1 h) ou 15 min (≥ 1 h). | pandas + statsmodels + dados de fila não cabem com folga em 128 MB. O import de pandas no escopo global compromete o limite de 1 s. **Veredito: a API Python/ML atual não é viável em Workers.** |
| **Containers** | Disponível no plano Workers Paid. Tipos: lite (1/16 vCPU, 256 MiB), basic (1/4, 1 GiB), standard-1 (1/2, 4 GiB), standard-2 (1, 6 GiB), standard-3 (2, 8 GiB), standard-4 (4, 12 GiB, 20 GB de disco). Imagem até o tamanho do disco. Controlado por Worker via Durable Object. | **Roda a imagem Docker da API e dos jobs sem mudar código.** É o caminho Cloudflare realista. |
| **Containers — disco e ciclo de vida** | "All disk is ephemeral"; o contêiner hiberna após `sleepAfter` (padrão 10 min); cold start "often 1–3 seconds", dependente do tamanho da imagem. | A API precisa ser sem estado (hoje não é: cache em memória, `/tmp`, `lightning_logs`). Com pandas, as imagens ficam grandes e o cold start maior; manter 1 instância "quente" em produção. |
| **Containers — localização** | Implantação em "Region:Earth". A plataforma escolhe "the nearest location with a pre-fetched image" e pode iniciar instâncias "farther away from the end-user". A página de arquitetura **não documenta restrição por jurisdição ou região**. | Não há garantia de que o processamento ocorra no Brasil. Um contêiner fora da América do Sul acessando Postgres em São Paulo paga latência por consulta (dezenas a centenas de ms). **Risco de latência e de transferência internacional.** |
| **Containers — preço** | Paid US$ 5/mês inclui 25 GiB-h de memória, 375 vCPU-min e 200 GB-h de disco. Excedente: US$ 0,0000025/GiB-s, US$ 0,000020/vCPU-s (CPU cobrada por uso), US$ 0,00000007/GB-s. Cobrança só enquanto ativo. Egress para "outras regiões": US$ 0,04/GB, com 500 GB incluídos. | Barato para homologação e jobs curtos (seção de custos). |
| **Hyperdrive** | Pooling/aceleração de Postgres/MySQL para **Workers**; cita AWS, GCP, Azure, Neon, PlanetScale. Free e Paid. | Útil se algum endpoint for escrito em Worker TS. Para o contêiner Python, a conexão é direta ao Postgres (pool do SQLAlchemy); Hyperdrive não é necessário e não é documentado para contêineres. |
| **R2** | API compatível com S3. Jurisdições: `eu`, `fedramp`, `us`. Location hints: wnam, enam, weur, eeur, apac, oc. **Nenhuma opção de América do Sul ou Brasil.** | Adequado para artefatos **sem dado pessoal** (modelos, `.dbc` públicos do SIH, builds). Arquivos com dado pessoal (CSV da fila) não devem ficar em R2 se o requisito for residência no Brasil. |
| **Cron Triggers / Queues / Workflows** | Cron: até 250 por conta. Workflows: até 10.000 passos (Paid), CPU por passo de 30 s a 5 min, estado de 1 GB por instância, retenção de 30 dias. A doc de Workflows só mostra JS/TS. | O **agendador** pode ser Cron + Workflow em TypeScript, que só **aciona** o contêiner de job (Python) e registra retries. O processamento pesado fica no contêiner. |
| **Localização de dados** | Data Localization Suite é **add-on Enterprise**. Regional Services tem região **Brasil** ("somente data centers fisicamente no Brasil para descriptografar e servir HTTPS"); Geo Key Manager não tem Brasil. | Garantir terminação TLS no Brasil exige plano Enterprise, fora da rubrica. Sem ele, a borda Cloudflare pode processar tráfego fora do Brasil (o armazenamento dos dados continua onde estiver o banco). |

**Nota jurídica, não é parecer.** A LGPD não impõe residência de dados no Brasil. Transferência internacional (art. 33) exige mecanismo válido, por exemplo as cláusulas-padrão da Resolução CD/ANPD nº 19/2024. Contratos e termos com SESA e secretarias podem exigir hospedagem no país. Confirmar com o consultor jurídico previsto no plano **antes** de colocar dado real fora da AWS sa-east-1 ou equivalente.

## Decisão

1. **Artefatos portáveis como regra:**
   - API e jobs em **uma imagem OCI** (Dockerfile), configurados só por variáveis de ambiente;
   - **PostgreSQL padrão** via `DATABASE_URL` (ADR-002);
   - **armazenamento de objetos via API S3** (`boto3` com `S3_ENDPOINT_URL`), atendendo R2 e S3;
   - jobs de ETL e treino como **CLI**, com o agendador trocável;
   - frontend Next.js padrão, com adaptador de hospedagem só em `infra/`.
2. **Não usar Python Workers para a API.** Workers ficam para o **frontend** (OpenNext), um eventual **gateway fino** (roteamento, rate limit, headers de segurança) e o **agendador** (Cron/Workflow em TS).
3. **Homologação na Cloudflare** (Opção A de [visao-geral.md](../visao-geral.md)): Workers (web + gateway), Containers (API e jobs), Postgres gerenciado em **São Paulo** e R2 para artefatos. Só com dados **sintéticos ou pseudonimizados**.
4. **Produção do piloto em arranjo híbrido:** Cloudflare para DNS, WAF, TLS e frontend; **API, jobs, Postgres e objetos com dado pessoal na AWS `sa-east-1`** (EC2/ECS, RDS, S3). Esse arranjo cumpre o texto aprovado (AWS EC2/RDS/S3) e a preferência por Cloudflare na borda.
5. **Critérios para mover a produção inteira para Cloudflare Containers** (revisar a cada trimestre):
   - Cloudflare documentar controle de região para Containers que inclua Brasil ou América do Sul, **ou** o jurídico aprovar processamento fora do país com mecanismo do art. 33;
   - teste de latência p95 da API em Containers → Postgres São Paulo abaixo de 300 ms nas telas principais;
   - aceite contratual do cliente.
6. **Isolar o específico de provedor** em `infra/cloudflare/` e `infra/aws/`. O código em `apps/` e `pipelines/` não importa SDK de provedor, exceto `boto3` genérico em `core/storage.py`.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| **Tudo em Python Workers** | Inviável para pandas/statsmodels/ML dentro de 128 MB e com drivers nativos; exigiria reescrever o backend. Rejeitada. |
| **Reescrever a API em TypeScript (Workers + Hyperdrive + D1)** | Mais barato em escala, mas reescreve 3.600+ linhas de regras e analytics e duplica a lógica com o ML em Python. Não cabe no cronograma. Rejeitada para o MVP. |
| **Tudo em Cloudflare (Containers + R2 + Postgres externo)** | Tecnicamente viável e barato; fica bloqueada para dado real até se resolver localização e latência (critérios do item 5). Adotada para homolog. |
| **Tudo em AWS sa-east-1** | Aderente à proposta e à residência de dados; custo maior (ALB, RDS, logs, NAT se usar sub-redes privadas). É o plano B completo. |
| **Tudo em AWS us-east-1** | Mais barata que sa-east-1, mas cria transferência internacional sem ganho relevante. Rejeitada para dado pessoal. |

## Custos estimados (ordem de grandeza)

Premissas: câmbio de planejamento **R$ 5,50/US$** (ajustar), mais IOF de cartão internacional. Uso de piloto: dezenas de usuários, poucas requisições por minuto, SIH de poucos GB. Valores da Cloudflare calculados com a tabela de preço citada acima. **Valores da AWS e dos Postgres gerenciados são estimativas a validar nas calculadoras oficiais antes de qualquer compromisso.**

| Item | A — Cloudflare + Postgres SP | B — AWS sa-east-1 | Híbrido recomendado |
|---|---|---|---|
| Workers Paid (web, gateway, cron) | US$ 5 | — | US$ 5 |
| API prod, sempre ativa | Container basic–standard-1: US$ 9–30 | EC2 t4g.small com Docker + Cloudflare Tunnel: US$ 15–25, **ou** Fargate 0,5 vCPU/1 GB: US$ 25–35 | EC2/Fargate: US$ 15–35 |
| Load balancer | não precisa | ALB US$ 20–25 (evitável com Tunnel) | US$ 0 com Tunnel |
| Jobs ETL/treino (~2 h/dia) | Container standard-2: ≈ US$ 8 | Fargate/EC2: US$ 5–10 | US$ 5–10 |
| Homolog (API + jobs, hibernando) | US$ 3–8 | US$ 15–30 | Cloudflare: US$ 3–8 |
| Postgres prod (SP, backups/PITR) | Neon/Supabase SP: US$ 25–60 | RDS db.t4g.small + 50 GB gp3: US$ 45–70 | US$ 25–70 |
| Postgres homolog | camada gratuita ou mínima: US$ 0–20 | RDS micro: US$ 15–25 | US$ 0–20 |
| Objetos | R2: US$ 0–2 | S3: US$ 1–3 | US$ 1–5 |
| Logs, segredos e monitoramento | US$ 0–5 | CloudWatch + Secrets Manager: US$ 5–15 | US$ 5–10 |
| **Total mensal (US$)** | **≈ 50–140** | **≈ 120–230** | **≈ 60–165** |
| **Total mensal (R$)** | **≈ 275–770** | **≈ 660–1.265** | **≈ 330–905** |

Leitura:

- Todas as opções só cabem na rubrica de R$ 796/mês se o banco for dimensionado com cuidado. **A rubrica também paga licenças e APIs**, então a meta prática para nuvem é ficar **abaixo de ~R$ 600/mês**.
- A opção B pura tende a estourar a rubrica, principalmente com ALB, RDS multi-AZ ou NAT Gateway. Evitar NAT Gateway (sub-rede pública com security group restrito, ou Tunnel).
- O híbrido fica dentro da rubrica usando Postgres gerenciado em São Paulo mais barato (Neon/Supabase) ou RDS single-AZ pequeno, e uma instância EC2 pequena atrás de Cloudflare Tunnel.
- Registrar o custo **real** mensal (faturas) como evidência da rubrica; manter alertas de orçamento (AWS Budgets e alertas de uso da Cloudflare).

## Consequências

- **Positivas:** uma imagem roda em qualquer lugar; homolog barata na Cloudflare; produção aderente ao texto aprovado (AWS) e à residência de dados; borda Cloudflare melhora desempenho em conexões lentas (cache, compressão, HTTP/3) e segurança (WAF).
- **Negativas:** dois provedores para operar (contas, faturas, IaC); é preciso eliminar o estado local da API antes de conteinerizar (D11).
- **Administrativo:** a descrição da rubrica menciona AWS. Usar Cloudflare para parte da infraestrutura **pode exigir comunicação ou aprovação da FUNCAP**. Registrar esta ADR como justificativa técnica e de custo e confirmar com a gestão do Centelha **antes** de pagar faturas da Cloudflare com recurso da subvenção.

## Pendências de verificação

- [ ] Confirmar disponibilidade de região São Paulo e preço atual de Neon, Supabase e RDS (single-AZ, PITR).
- [ ] Confirmar disponibilidade regional do serviço escolhido na AWS (App Runner, ECS Fargate) em `sa-east-1`.
- [ ] Teste de latência: Container Cloudflare (homolog) → Postgres São Paulo, p50/p95.
- [ ] Parecer jurídico sobre transferência internacional e exigências contratuais da SESA.
- [ ] Resposta da FUNCAP sobre uso de fornecedor diferente do descrito na rubrica.
