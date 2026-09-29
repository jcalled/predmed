# Regras de priorização clínica — v0.1 (proposta)

Versão: 28/09/2026. Código: `backend/services/priorizacao.py`. Testes: `backend/tests/test_priorizacao.py`.
**Status: proposta para revisão clínica e jurídica (B34). Não usar no piloto antes dessa revisão.**

O score é **apoio à decisão**: ordena e explica, não substitui a regulação nem o julgamento clínico.
Cada paciente mostra na tela de onde vem cada ponto e quais alertas exigem revisão.

## Critérios (máximo 100)

| Critério | Pontos | Regra |
|---|---|---|
| Classificação SWALIS | até 40 | A1 = 40, A2 = 32, B = 24, C = 12, D = 4; ausente = 12 (neutro) + alerta |
| Tempo de espera | até 30 | Proporcional aos dias desde a solicitação; satura em 730 dias (2 anos) |
| Mandado judicial | +15 | Pedido com ordem judicial |
| Oncologia | +10 | Especialidade ONCOLOGIA, ou procedimento "em oncologia" / "maligno" |
| Cardiovascular grave | +5 | Especialidade CARDIOVASCULAR com SWALIS A1 ou A2 |

Desempate: maior tempo de espera primeiro.

## Alertas (não mudam o score; pedem revisão humana)

- SWALIS não informada.
- Sem data de solicitação.
- Data de solicitação a confirmar (numeração antiga da regulação, 3 a 6 dígitos).
- Oncologia com mais de 60 dias de espera. Referência: Lei 12.732/2012. O prazo legal conta do diagnóstico, não da solicitação cirúrgica; aqui é só um sinal.

## Resultado na fila de 28/09/2026 (61.756 pedidos)

| Faixa de score | Pedidos |
|---|---|
| ≥ 70 | 3.516 |
| 50–69 | 8.007 |
| < 50 | 50.233 |
| Oncologia > 60 dias (alerta) | 1.491 |

## Perguntas para a revisão clínica

1. Os pesos relativos (SWALIS 40 × espera 30 × judicial 15 × oncologia 10) refletem a prática da regulação?
2. O tempo de espera deve ser medido contra o **tempo-alvo de cada categoria SWALIS** em vez de uma escala única de 2 anos?
3. Mandado judicial deve somar pontos ou ser tratado como obrigação à parte (fila separada)?
4. Quais procedimentos cardiológicos e oncológicos devem receber prioridade adicional além da especialidade?
5. Como tratar SWALIS "Não Informada" (1.741 pedidos)?
6. Há critérios de equidade a monitorar (por CIR, município, hospital)? A proposta prevê auditoria de disparidades regionais.
