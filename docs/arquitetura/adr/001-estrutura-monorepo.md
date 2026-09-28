# ADR-001 — Estrutura de monorepo e backend em camadas

- **Status:** Proposto
- **Data:** 28/09/2026
- **Decisores:** responsável técnico (JOSE MARCAL DOMINGOS JUNIOR LTDA)

## Contexto

- `backend/main.py` concentra 31 rotas, schemas, consultas e regras de negócio (diagnóstico D12). `backend/routers/` está vazio.
- Os serviços têm 700–850 linhas e acessam o ORM diretamente. ETL e treino de ML rodam dentro do processo da API (D11). Scripts ficam soltos em `_SCRIPTS/`, com import quebrado (D15).
- Regras de tenant estão duplicadas por rota, o que causou vazamentos entre instituições (D02).
- A proposta exige CI/CD, ambientes separados e implantação em nuvem. O responsável quer portabilidade Cloudflare/AWS.
- O time é pequeno (proponente e consultorias pontuais).

## Decisão

1. Manter **um repositório (monorepo)** com `apps/api`, `apps/web`, `packages/domain`, `packages/ml`, `pipelines/etl`, `pipelines/treino`, `infra/` e `docs/`, conforme [estrutura-pastas.md](../estrutura-pastas.md).
2. Organizar o backend em camadas: `api/routers` → `services` → `repositories` → `db/models`, com `schemas/` (Pydantic) e `core/` (config, security, tenancy, audit, logging, storage).
3. **Escopo de tenant obrigatório nos repositórios**: toda consulta a dados de fila, transferência ou hospital recebe um `Escopo` derivado do usuário. Não existe método de repositório sem escopo, exceto em jobs.
4. ETL e treino viram **CLIs executados como jobs**, fora do processo da API.
5. Migrar em passos pequenos (M0–M14), sem mudar URLs da API até o fim, mantendo `./start.sh`.
6. Sem ferramenta de monorepo pesada (Nx/Turborepo) por enquanto: `pyproject.toml` por pacote Python (uv ou pip) e `package.json` no web. Reavaliar se surgirem mais apps.

## Alternativas consideradas

| Alternativa | Por que não agora |
|---|---|
| Repositórios separados (api, web, ml) | Multiplica CI, versões e revisões para um time de 1–2 pessoas; dificulta mudanças coordenadas de contrato da API |
| Manter estrutura atual e só criar routers | Resolve D12, mas não separa ETL/ML nem cria ponto único de escopo de tenant |
| Reescrever do zero | Risco alto no meio da Etapa 2; perde o que funciona |
| Microserviços | Custo operacional incompatível com a rubrica e o time |

## Consequências

- **Positivas:** regra de tenant testável em um ponto; API sem estado, pronta para contêiner; jobs agendáveis em qualquer provedor; testes unitários de domínio sem banco.
- **Negativas:** 2–3 semanas de refatoração que concorrem com E2.1–E2.5; PRs de movimentação (`git mv`) dificultam `git blame` (mitigado com `--follow` e `.git-blame-ignore-revs`).
- **Riscos:** regressão silenciosa na movimentação, mitigada pelos testes de caracterização (M4) antes de mover.
