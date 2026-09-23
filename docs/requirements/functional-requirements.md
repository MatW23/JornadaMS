# Requisitos funcionais

## 1. Convenções

Os requisitos abaixo descrevem o comportamento esperado do MVP. `Must` é necessário para a primeira versão; `Should` é importante, mas pode ser priorizado após o núcleo; `Future` pertence a uma evolução posterior.

Neste documento, “primeira versão” significa o MVP-1. Requisitos `Should` formam o MVP-2 e só devem entrar depois que a fatia de registro básico estiver validada.

## 2. Atores

| Ator | Descrição |
| --- | --- |
| Colaborador | Registra e consulta a própria jornada |
| Gestor operacional | Acompanha a equipe e participa de aprovações |
| Analista de RH | Administra jornadas, ajustes, justificativas e relatórios |
| Administrador | Configura usuários, papéis e parâmetros do sistema |
| Diretoria | Consulta indicadores e relatórios consolidados |
| Sistema | Executa validações, cálculos, auditoria e exportações |

## 3. Autenticação e acesso

| ID | Prioridade | Requisito | Critério de aceite |
| --- | --- | --- | --- |
| FR-001 | Must | O sistema deve permitir login com credenciais válidas. | Credenciais válidas iniciam sessão; inválidas retornam erro sem revelar qual campo falhou. |
| FR-002 | Must | O sistema deve permitir encerrar e renovar sessões conforme política configurada. | Sessão encerrada não autoriza novas operações; token expirado exige renovação ou novo login. |
| FR-003 | Must | O sistema deve aplicar acesso baseado em papéis (RBAC). | Usuário sem permissão recebe `403` e nenhuma alteração é realizada. |
| FR-004 | Must | O sistema deve disponibilizar o perfil e o contexto organizacional do usuário autenticado. | A API retorna usuário, papel, empresa/filial e permissões efetivas. |

## 4. Cadastros e configuração

| ID | Prioridade | Requisito | Critério de aceite |
| --- | --- | --- | --- |
| FR-005 | Must | RH/admin deve cadastrar, consultar, editar, ativar e desativar colaboradores. | Colaborador inativo não pode registrar ponto; histórico permanece preservado. |
| FR-006 | Should | RH/admin deve manter empresas, filiais, departamentos e cargos. | Cada cadastro possui identificador, nome, status e histórico de criação/alteração. No MVP-1, uma organização e uma estrutura mínima podem ser provisionadas. |
| FR-007 | Must | RH deve definir uma jornada simples no mesmo dia, com entrada e saída e intervalo opcional. | Uma configuração ativa pode ser vinculada ao colaborador e usada pelo cálculo; início e fim do intervalo são opcionais, mas devem ser informados em conjunto. |
| FR-008 | Must | O sistema deve validar campos obrigatórios e unicidade dos cadastros. | Duplicidades e dados inválidos são rejeitados com mensagem acionável. |

## 5. Registro e cálculo da jornada

| ID | Prioridade | Requisito | Critério de aceite |
| --- | --- | --- | --- |
| FR-009 | Must | Colaborador deve registrar entrada, início/fim do intervalo e saída conforme a sequência aplicável. | Cada evento válido é persistido com data/hora, usuário e metadados disponíveis; a sequência direta entrada/saída continua válida para jornadas sem intervalo. |
| FR-010 | Must | O sistema deve validar a sequência dos eventos. | Evento fora de ordem é recusado ou marcado como inconsistência conforme a regra aplicável. |
| FR-011 | Must | O sistema deve impedir duplicidade acidental de um mesmo registro. | Reenvio da mesma operação não cria um segundo evento. |
| FR-012 | Must | O sistema deve calcular as horas trabalhadas e o saldo diário básico a partir dos períodos abertos e fechados. | O resumo do dia é atualizado após evento válido, descontando o intervalo registrado. Horas extras e banco de horas entram no MVP-2. |
| FR-013 | Must | O sistema deve identificar inconsistências de jornada. | O colaborador/RH consegue visualizar o motivo e o status da inconsistência. |
| FR-014 | Must | O colaborador deve consultar a própria jornada e o resumo diário. | A consulta mostra entrada, saída, horas trabalhadas e status no período selecionado. Banco de horas entra no MVP-2. |
| FR-015 | Should | Gestor/RH deve consultar a jornada dos colaboradores permitidos. | O resultado respeita o escopo organizacional e as permissões do solicitante. |

## 6. Justificativas, ajustes e aprovação

| ID | Prioridade | Requisito | Critério de aceite |
| --- | --- | --- | --- |
| FR-016 | Should | Colaborador ou RH deve registrar justificativa para atraso, ausência ou inconsistência. | Justificativa contém motivo, data, autor, status e histórico de decisão. |
| FR-017 | Should | Usuário autorizado deve solicitar ajuste sem apagar o registro original. | A solicitação mantém valor anterior, novo valor proposto e justificativa. |
| FR-018 | Should | Gestor/RH autorizado deve aprovar ou rejeitar ajustes. | Decisão exige autor e data; aprovação dispara recálculo; rejeição mantém o valor original. |
| FR-019 | Should | O sistema deve exibir histórico de alterações de uma jornada. | Cada versão mostra antes, depois, motivo, autor e decisão. |

## 7. Consultas, relatórios e indicadores

| ID | Prioridade | Requisito | Critério de aceite |
| --- | --- | --- | --- |
| FR-020 | Should | O sistema deve gerar relatório diário, semanal e mensal. | Relatórios permitem filtrar período e escopo autorizado. |
| FR-021 | Should | O sistema deve exportar relatórios para Excel e PDF. | Arquivo exportado contém período, filtros aplicados, geração e dados exibidos na consulta. |
| FR-022 | Should | O sistema deve apresentar dashboard básico de jornada. | Dashboard exibe horas extras, banco de horas, atrasos e absenteísmo conforme período. |
| FR-023 | Should | O sistema deve permitir busca e ordenação em listas administrativas. | Filtros podem ser combinados e são refletidos no resultado. |

## 8. Auditoria e operação

| ID | Prioridade | Requisito | Critério de aceite |
| --- | --- | --- | --- |
| FR-024 | Must | O sistema deve auditar operações críticas do MVP-1 e, depois, operações administrativas. | No MVP-1, login, cadastro de colaborador e registro de ponto geram evento de auditoria; o restante entra no MVP-2. |
| FR-025 | Should | Administrador deve consultar logs e eventos de auditoria autorizados. | Consulta permite filtrar por usuário, tipo, entidade e período. |
| FR-026 | Must | O sistema deve informar falhas de forma compreensível. | Erros possuem código, mensagem segura e correlação para suporte. |
| FR-027 | Future | O sistema poderá integrar ERP, folha, dispositivos e APIs públicas. | A integração será especificada em versão própria, fora do MVP. |

## 9. Rastreabilidade

| Objetivo da visão | Requisitos relacionados |
| --- | --- |
| Centralizar registros | FR-005, FR-009, FR-014, FR-015 |
| Automatizar cálculos | FR-010 a FR-013 |
| Facilitar auditorias | FR-017 a FR-019, FR-024 e FR-025 |
| Apoiar decisões | FR-020 a FR-023 |
| Proteger acesso e dados | FR-001 a FR-004, FR-024 a FR-026 |
