# Coleta automática da fila IntegraSUS

Versão: 28/09/2026. Script: `backend/_SCRIPTS/coleta_fila_integrasus.py`. Antecipa B25 e resolve a principal lacuna de B35 (tempo de espera).

## Achado que muda o projeto

O painel público "Consulta da Fila de Espera" (id 214) carrega a fila inteira pelo endpoint JSON
`/api/consulta-fila-espera/consulta-nome-fila-espera`. Diferente do CSV do botão "Baixar Dados", **o JSON traz o campo `data`**.

Verificação em 28/09/2026 (só agregados):

| Item | Resultado |
|---|---|
| Registros | 61.756 (194 estabelecimentos, 15 especialidades) |
| Registros com `data` | 61.756 (100%) |
| Intervalo | 11/10/2006 a 27/09/2026; mediana 03/12/2025 |
| `data` × nº de solicitação (séries de 7 e 11 dígitos, 94% da fila) | Spearman 1,00; 100% dos pares em ordem |
| `data` × posição, dentro de unidade × procedimento × SWALIS | 99% dos pares em ordem |
| Séries legadas (3 a 6 dígitos, ~4,5%) | Coerência menor; tratar com cautela |

**Interpretação:** `data` é a data/hora da solicitação na regulação (criação do pedido). É a data de entrada na fila adotada pelo PREDMED, com a ressalva de que o significado oficial do campo não está documentado pela SESA. Confirmar no ofício à SESA.

Consequência: o tempo de espera do estoque atual passa a ser calculável (`data da coleta − data`), sem depender de reconstrução por snapshots. Os snapshots continuam necessários para observar **saídas** (atendimento, cancelamento) e medir fluxo e redução de espera no piloto.

## Como funciona

1. Uma requisição ao endpoint público, com retentativas. User-Agent identifica o PREDMED.
2. Valida o formato: lista, mínimo de 1.000 registros, chaves esperadas. Se o formato mudar, a coleta falha e não grava.
3. Grava o JSON bruto compactado (xz) e **criptografado** (Fernet) em
   `~/PredmedDados/integrasus/fila/AAAA/MM/fila_AAAAMMDDTHHMMSS.json.xz.enc`, permissão 600, fora do repositório.
4. Acrescenta uma linha a `~/PredmedDados/integrasus/fila/manifesto.jsonl`, só com agregados: total, entradas e saídas desde a coleta anterior, contagem por SWALIS, judicializados, datas mín./mediana/máx., hash e tamanho.

Tamanho: ~1,4 MB por coleta; 2 coletas/dia ≈ 1 GB/ano.

## Chave de criptografia

Gerada na primeira execução em `~/.predmed/coleta.key` (permissão 600), ou lida de `PREDMED_COLETA_KEY`.
**Sem a chave, as coletas não podem ser lidas.** Guardar uma cópia da chave em local seguro (gerenciador de senhas), separada dos arquivos.

## Agendamento no Mac (provisório até a AWS)

Arquivo: `backend/_SCRIPTS/launchd/br.predmed.coleta-integrasus.plist` — roda às 7h e às 19h.
Se o Mac estiver dormindo no horário, o macOS executa ao acordar; se estiver desligado, a coleta daquele horário é perdida.

Instalar:

```bash
mkdir -p ~/PredmedDados/logs
cp backend/_SCRIPTS/launchd/br.predmed.coleta-integrasus.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/br.predmed.coleta-integrasus.plist
```

Conferir / rodar agora / desinstalar:

```bash
launchctl print gui/$(id -u)/br.predmed.coleta-integrasus | grep state
launchctl kickstart gui/$(id -u)/br.predmed.coleta-integrasus
launchctl bootout gui/$(id -u)/br.predmed.coleta-integrasus
```

Log: `~/PredmedDados/logs/coleta-integrasus.log` (sem dados de pacientes).

## Próximos passos

- Ajustar o importador (`services/data_import.py`) para ler a coleta JSON, mantendo `data` (→ `data_insercao`), posição e nº de solicitação **pseudonimizado** (HMAC), e parar de converter SWALIS ausente em "Categoria D" (existe "Não Informada": 1.741 registros).
- Migrar a coleta para a AWS (agendamento + S3 criptografado) quando o ambiente existir (B18).
- Confirmar com a SESA o significado do campo `data` e os termos de uso do portal.
