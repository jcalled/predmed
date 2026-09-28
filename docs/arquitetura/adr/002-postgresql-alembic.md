# ADR-002 — PostgreSQL gerenciado e migrações com Alembic

- **Status:** Proposto
- **Data:** 28/09/2026

## Contexto

- Hoje há SQLite em arquivo (`predmed.db`, 17 MB; `predmed-original.db`, 1,9 GB com 3,18 milhões de AIHs). O esquema é criado por `Base.metadata.create_all` (`backend/database.py:347-348`), sem versionamento (D10).
- A proposta aprovada cita **RDS PostgreSQL**. `DATABASE_URL` já é lida do ambiente (`database.py:14`) e `analytics_sih.py:89` já ramifica por dialeto.
- A API em contêiner precisa ser sem estado, com várias réplicas e disco efêmero (Cloudflare Containers apaga o disco ao hibernar). SQLite em arquivo é incompatível com isso.
- É preciso ter criptografia em repouso, backup com restauração testada e região Brasil.

## Decisão

1. **PostgreSQL 16** como banco de todos os ambientes em nuvem, acessado por `DATABASE_URL` (`postgresql+psycopg://…?sslmode=require`). Sem extensões proprietárias de provedor. `pg_trgm` para busca por nome de hospital é aceitável, porque está disponível em RDS, Neon e Supabase.
2. **Alembic** para todas as mudanças de esquema:
   - migração *baseline* gerada a partir dos modelos atuais;
   - `alembic upgrade head` como passo explícito do deploy, nunca no `startup` da API;
   - `init_db()`/`create_all` restritos a testes.
3. SQLite continua como **opção de dev** em `./start.sh` enquanto as consultas forem compatíveis. O CI roda os testes de integração **em Postgres** (serviço do GitHub Actions).
4. **Esquemas lógicos:** `app` (tenants, usuários, config, auditoria), `fila` (snapshots e fila atual), `sih` (AIH, particionada por `ano_cmpt`), `ml` (resultados e avaliações). Papéis de banco separados: `api_ro` (somente leitura em `fila`, `sih` e `ml`), `api_rw` (apenas em `app`), `etl` (escrita em `fila`, `sih` e `ml`).
5. Correções de modelagem junto com a migração: datas como `DATE`/`TIMESTAMPTZ` (hoje `String`, `database.py:70-71`); `tenant_id`/escopo nas tabelas de dados; `unique` e sequência para protocolo; remoção de `nasc`/`cep` do modelo analítico (ADR-004).
6. **Migração de dados** por script idempotente (SQLite → Postgres) executado sobre **cópia**, com relatório de contagens e competências por tabela (checklist T05).
7. **Provedor:** qualquer Postgres gerenciado com região **São Paulo**, backups automáticos com PITR e criptografia em repouso: RDS `sa-east-1`, ou Neon/Supabase em São Paulo (confirmar disponibilidade da região no momento da contratação). A escolha fica no ADR-003.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Cloudflare D1 | SQLite distribuído, acessível por Workers; não é acessado nativamente por contêiner Python/SQLAlchemy, tem limite de tamanho por banco e não oferece localização no Brasil. Acopla a um provedor. |
| Manter SQLite em volume | Sem concorrência de escrita, sem réplicas, disco efêmero no Cloudflare Containers, sem PITR |
| MySQL | Sem ganho; a proposta cita PostgreSQL |
| Data warehouse separado (BigQuery/Redshift) para o SIH | Custo e complexidade desnecessários no volume atual (poucos GB); reavaliar se passar de dezenas de GB |

## Consequências

- Deploy reproduzível e reversível (`alembic downgrade`), com backup antes de cada migração em produção.
- É preciso revisar consultas específicas de SQLite (`strftime`, comparações de datas em string) e testar em Postgres.
- Custo mensal fixo do banco é o maior item da rubrica (ADR-003).
- O banco de 1,9 GB precisa de janela de carga. O SIH é público e pode ser recarregado a partir dos `.dbc`, e esse é o caminho preferível a copiar o SQLite.
