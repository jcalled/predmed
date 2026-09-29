# Minuta — Solicitação de remanejamento da rubrica "Consultoria UX/UI"

Versão: 28/09/2026. Item B08 do `backlog.md`. Redigida pelo gerente de projetos (agente); **revisão, escolha do destino, assinatura e envio são do proponente**.

## Antes de enviar (checklist do proponente)

- [ ] Ler o Termo de Outorga (B09) e conferir: **(a)** se há procedimento, formulário ou sistema próprio para remanejamento — se houver, usar o formato oficial e aproveitar apenas o texto desta minuta; **(b)** limites de remanejamento (percentual, mesma natureza de despesa, entre custeio e capital); **(c)** a quem endereçar e por qual canal; **(d)** prazo de antecedência e prazo de resposta; **(e)** se a mudança de executor (consultoria → equipe interna) exige anuência separada.
- [ ] Confirmar o valor e a descrição da rubrica no plano de trabalho vigente. Esta minuta usa a planilha atualizada (R$ 6.288,00). O PDF da proposta original trazia R$ 10.000,00 para a mesma consultoria — usar o valor que constar no Termo.
- [ ] Escolher **uma** alternativa de destino (seção "Alternativas") ou combinar duas com valores que somem R$ 6.288,00; apagar as demais do texto.
- [ ] Confirmar se a consultoria de integração de sistemas (alternativa A) ainda é permitida no plano vigente, já que ela saiu da planilha.
- [ ] **Não executar nenhum gasto com o valor antes da resposta formal da FUNCAP.**
- [ ] Após o envio: registrar data e protocolo em `decisoes.md` (D02) e em `prestacao-contas.md` (seção de acompanhamento orçamentário).

---

## Texto da minuta

[Local], [dia] de [mês] de [ano].

À
Fundação Cearense de Apoio ao Desenvolvimento Científico e Tecnológico — FUNCAP
[Diretoria / setor responsável — conferir no Termo de Outorga]
[Endereço ou canal eletrônico indicado no Termo]

**Assunto:** Solicitação de remanejamento de recursos entre itens de despesa — Termo de Outorga nº [número] — Edital FUNCAP/FINEP nº 08/2025 — Programa Centelha 3 CE — Projeto "PREDMED – Plataforma de IA para Previsão e Otimização de Filas Médicas"

Prezados(as) Senhores(as),

A empresa **JOSE MARCAL DOMINGOS JUNIOR LTDA**, inscrita no CNPJ sob o nº [CNPJ], executora do projeto em epígrafe, por meio de seu representante legal, [nome do representante legal], vem, respeitosamente, solicitar autorização para o remanejamento do item de despesa descrito a seguir, nos termos [da cláusula / do item] [nº da cláusula] do Termo de Outorga [conferir a cláusula aplicável].

**1. Item a ser remanejado**

| Natureza de despesa | Item | Valor aprovado |
|---|---|---|
| Custeio — Serviços de Terceiros Pessoa Jurídica | Consultoria PJ de UX/UI (criação da interface web responsiva, wireframes, testes de usabilidade com gestores e refinamento do dashboard, meta de score SUS acima de 70) | R$ 6.288,00 |

Até a presente data, nenhum valor deste item foi comprometido ou executado.

**2. Justificativa**

As atividades previstas para a consultoria de UX/UI — elaboração de wireframes a partir das entrevistas com gestores, desenvolvimento da interface web responsiva, teste de usabilidade com 5 gestores reais e refinamento do dashboard com meta de score SUS acima de 70 — serão executadas pela equipe interna do projeto, sob coordenação do proponente, que já conduz o desenvolvimento técnico central da solução.

A mudança **não altera as metas nem os indicadores** aprovados:

| Atividade do plano | Indicador aprovado | Como será cumprido |
|---|---|---|
| Validação do roadmap com gestores (M2–M3) | Wireframes aprovados | Wireframes elaborados pela equipe interna e submetidos à aprovação de gestores entrevistados |
| Interface e dashboard de gestão (M4–M6) | Interface aprovada em teste de usabilidade com 5 gestores reais; score SUS acima de 70 | Teste de usabilidade conduzido pela equipe interna, com aplicação do questionário SUS e registro do método e dos resultados agregados no relatório técnico |

Os resultados serão comprovados nos relatórios do projeto da mesma forma prevista para a consultoria, com as evidências listadas acima.

**3. Destino proposto**

Solicita-se que o valor de **R$ 6.288,00** seja destinado a [**alternativa escolhida — ver abaixo**], dentro da natureza de despesa Serviços de Terceiros Pessoa Jurídica, pelos motivos a seguir: [colar a justificativa da alternativa escolhida].

[Se a alternativa escolhida mudar de natureza de despesa, conferir no Termo se isso é admitido e ajustar este parágrafo.]

**4. Impacto no cronograma e nas metas**

O remanejamento não altera o cronograma das atividades nem os indicadores de aceite do plano de trabalho. [Se a alternativa escolhida antecipar ou reforçar alguma entrega, mencionar aqui.]

Colocamo-nos à disposição para os esclarecimentos que se fizerem necessários e, caso a FUNCAP disponha de formulário próprio para esta solicitação, pedimos a gentileza de indicá-lo.

Atenciosamente,

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
[Nome do representante legal]
[Cargo] — JOSE MARCAL DOMINGOS JUNIOR LTDA
CNPJ: [CNPJ]
Coordenador(a) do projeto: [nome]
Contato: [e-mail institucional] | [telefone]

Anexos (se aplicável): [plano de trabalho com a alteração destacada] [outros exigidos pelo Termo]

---

## Alternativas de destino (escolha do proponente)

Todas ficam na mesma natureza de despesa (Serviços de Terceiros PJ) do item de origem, o que tende a simplificar a análise — **mas só o Termo de Outorga define o que é permitido**.

### Alternativa A — Consultoria PJ de integração de sistemas

- **O que é:** apoio especializado para implementar a coleta automatizada dos dados públicos do IntegraSUS, a configuração dos ambientes em nuvem e o pipeline de CI/CD.
- **Ligação com as metas:** atividade 1 (ambientes dev/homologação/produção separados; CI/CD funcional; documentação de arquitetura), atividade 3 (coleta automatizada IntegraSUS configurada) e atividade 9 (integração em produção, atualização sem intervenção manual). A atividade 9 hoje é a mais atrasada tecnicamente (só há importação manual).
- **A favor:** **constava da proposta original** ("Consultoria PJ de integração de sistemas"), o que facilita a justificativa perante a FUNCAP.
- **Atenção:** a proposta descrevia essa consultoria com infraestrutura AWS (EC2, RDS, S3); o texto deve ser adaptado à arquitetura portável decidida (D03, e D06 se aprovada). Com R$ 6.288,00, o escopo precisa ser menor que os R$ 10.000,00 originais — sugerir foco na integração IntegraSUS e no CI/CD.
- **Texto sugerido para o item 3:** "…destinado à contratação de consultoria PJ de integração de sistemas, prevista na proposta original do projeto, para apoio à implementação da coleta automatizada dos dados públicos do IntegraSUS e do pipeline de integração e entrega contínuas, contribuindo diretamente para os indicadores das atividades de infraestrutura em nuvem, coleta de dados e integração automatizada IntegraSUS."

### Alternativa B — Consultoria PJ de segurança da informação e adequação técnica à LGPD

- **O que é:** avaliação de segurança da arquitetura e da aplicação (revisão de controle de acesso por perfil, criptografia em trânsito e em repouso, gestão de segredos, backup, trilha de auditoria), teste de intrusão antes do piloto e apoio técnico à anonimização de dados.
- **Ligação com as metas:** atividade 1 (documentação de arquitetura), atividade 10 (sistema em produção no hospital piloto — hospitais públicos tendem a exigir garantias de segurança para dados de pacientes) e o compromisso de conformidade com a LGPD e anonimização declarado na proposta.
- **A favor:** a proposta original cita "segurança da informação" entre as áreas de apoio especializado das consultorias PJ; ataca o principal risco do projeto (dados sensíveis de pacientes).
- **Atenção:** não duplicar o escopo da consultoria jurídica (R$ 10.000,00, que cobre LGPD no aspecto jurídico). Aqui o foco é **técnico**; explicitar a divisão no pedido.
- **Texto sugerido para o item 3:** "…destinado à contratação de consultoria PJ de segurança da informação, área prevista entre os apoios especializados da proposta, para avaliação técnica de segurança e de proteção de dados da plataforma antes do piloto hospitalar, complementar à consultoria jurídica já prevista."

### Alternativa C — Reforço do item de infraestrutura em nuvem e consumo de APIs

- **O que é:** somar o valor ao item existente de infraestrutura em nuvem e APIs (R$ 9.552,00 na planilha), passando a R$ 15.840,00.
- **Ligação com as metas:** atividade 1 (três ambientes separados), atividade 9 (integração em produção) e atividade 10 (sistema em produção no hospital piloto por 90 dias, com relatórios quinzenais). Se o arranjo híbrido (D06) for aprovado, a hospedagem de API, banco e arquivos em região de São Paulo tende a custar mais que a borda Cloudflare; também cobre backup e ambiente de homologação durante o piloto.
- **A favor:** não depende de contratar e gerir novo fornecedor; o gasto é sob demanda e fácil de comprovar.
- **Atenção:** exige estimativa de custo mensal que mostre a necessidade (a produzir no ADR, B11); verificar no Termo se reforçar item existente segue o mesmo procedimento de remanejamento.
- **Texto sugerido para o item 3:** "…destinado ao reforço do item de infraestrutura em nuvem e consumo de APIs, para garantir ambientes separados de desenvolvimento, homologação e produção e a operação do sistema durante o piloto em hospital público, com hospedagem dos dados pessoais em território nacional."

### Comparação rápida

| Critério | A — Integração | B — Segurança/LGPD técnica | C — Reforço nuvem |
|---|---|---|---|
| Consta da proposta original | Sim (item próprio) | Citada como área de apoio | Item existe na planilha |
| Atividades beneficiadas | 1, 3, 9 | 1, 10 (e LGPD transversal) | 1, 9, 10 |
| Novo contrato a gerir | Sim | Sim | Não |
| Risco principal que reduz | Atraso da integração IntegraSUS | Incidente/objeção de segurança no piloto | Falta de recursos para produção/piloto |
| Depende de outra decisão | D03/D06 (adaptar texto AWS) | Divisão de escopo com a jurídica | D06 e estimativa de custos (B11) |

Recomendação do gerente de projetos (não vinculante): **A** tem a justificativa mais fácil por já estar na proposta e atacar a atividade 9, que está tecnicamente mais distante do indicador; **B** é a melhor opção se o proponente avaliar que o piloto hospitalar vai exigir laudo de segurança. A decisão é do proponente.
