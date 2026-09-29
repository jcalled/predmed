# Arquitetura de telas do PREDMED — consolidação por perfil

Versão: 29/09/2026. Aprovada pelo responsável, com a condição de **não juntar o que muda por tipo de usuário**.
Objetivo: de 14 para 7 entradas de menu, sem perder nenhuma função que um perfil use e **sem alterar nenhuma regra de acesso do backend**. A mudança é só de organização de telas: endpoints e permissões continuam os mesmos.

## Perfis

| Perfil (role) | Quem é | Papel no produto |
|---|---|---|
| `sesa` | Secretaria Estadual | Gestor da rede: vê o estado, **aprova** redistribuições, importa dados |
| `sms` | Secretaria Municipal | Gestor: vê o estado (decisão de 28/09) e **aprova redistribuições dentro da própria CIR** (decisão de 29/09) |
| `hospital_publico` | Hospital público | Opera a própria fila; vê priorização/judicializados de todos sem iniciais alheias |
| `hospital_particular` | Hospital privado conveniado | Lado "oferta" do marketplace: vê só agregados de outras instituições, informa **vagas SUS**, vê oportunidades de receita |

Regras de dados por perfil: README, seção "Multi-tenant — Quem vê o quê" (continua valendo).

## Menu final e o que cada perfil vê

| # | Tela | SESA | SMS | Hosp. público | Hosp. particular | Absorve |
|---|---|:-:|:-:|:-:|:-:|---|
| 1 | **Painel** | ✅ | ✅ | ✅ | ✅ | Dashboard |
| 2 | **Fila cirúrgica** | ✅ estado | ✅ estado | ✅ só o seu | ✅ agregados | — |
| 3 | **Priorização** | ✅ | ✅ | ✅ | ✅ agregados | Judicializados (vira filtro "Somente judicializados") |
| 4 | **Previsão de demanda** | ✅ | ✅ | ✅ | ✅ | Previsões + Previsões ML + Validação (aba) + sazonalidade do Analytics (aba) |
| 5 | **Redistribuição** | ✅ + aprovar (estado) | ✅ + aprovar (sua CIR) | ✅ leitura | ✅ leitura | Hospitais (aba "Pressão por hospital"); Prog. Zerar Filas (aba "Simulação de mutirão", só SESA/SMS) |
| 6 | **Oportunidades SUS** | — | — | — | ✅ | Simulador de receita (só particular; números rotulados "simulado") |
| 7 | **Relatórios** | ✅ estado | ✅ estado | ✅ seu hosp. | ✅ seu hosp. | — |
| 8 | **Configurações** | ✅ Importação/coleta | ✅ status da coleta | — | ✅ Vagas SUS | — |

Contagem por perfil: gestores (SESA/SMS) veem 7 itens; hospital público, 6; hospital particular, 8 (inclui Oportunidades SUS e Configurações → Vagas).

## O que NÃO se junta (e por quê)

- **Oportunidades SUS (simulador de receita) fica separada e só para o hospital particular.** É a proposta de valor do lado "oferta" do marketplace (plano: hospital conveniado aumenta receita via AIH). Não faz sentido para gestores nem para hospital público.
- **Configurações tem conteúdo diferente por perfil:** SESA importa/acompanha a coleta; particular informa vagas SUS; hospital público não tem a tela. As abas aparecem conforme o perfil, nunca todas para todos.
- **Aprovação de redistribuição:** SESA em todo o estado; SMS só entre hospitais da própria CIR (o backend valida; `pode_aprovar` e `escopo_aprovacao` vêm da API). A aba de mutirão (ex-Zerar Filas) só aparece para SESA/SMS, como antes.
- **Aba "Pressão por hospital"** mantém o escopo por perfil que o endpoint `/hospitais` já aplica (SESA/SMS todos; público a sua CIR; particular os públicos da CIR).

## O que sai do produto

- **Analytics SIH — mortalidade e valor pago SUS:** fora do escopo do plano e sujeitos a interpretação equivocada. A sazonalidade segue na Previsão.
- As rotas antigas (`/dashboard/previsoes-ml`, `/validacao`, `/judicializados`, `/hospitais`, `/zerarfilas`, `/analytics`, `/simulador`) redirecionam para o novo lugar, para não quebrar links salvos.
- O código removido fica no histórico do git.

## Pendências registradas

- Resolvida em 29/09/2026: a SMS aprova redistribuições dentro da própria CIR (texto do login e backend alinhados).
