# Regras de negócio

## 1. Objetivo

Este documento concentra as regras do domínio de jornada que devem ser aplicadas independentemente da tela ou do cliente utilizado. Parâmetros legais ou de convenção coletiva não devem ser codificados como constantes: precisam ser configuráveis e validados pelo responsável de RH.

## 2. Vocabulário do domínio

| Termo | Definição operacional |
| --- | --- |
| Evento | Marcação de jornada com tipo, data/hora, autor e origem. |
| Jornada prevista | Horário esperado para o colaborador no dia. |
| Jornada realizada | Tempo entre os eventos válidos, descontados os intervalos. |
| Resumo diário | Resultado calculado para um colaborador em uma data. |
| Saldo | Diferença entre jornada realizada e jornada prevista, após regras configuradas. |
| Inconsistência | Situação que impede ou reduz a confiabilidade do cálculo. |
| Ajuste | Alteração administrativa proposta para um evento ou resumo, preservando o original. |

### Perfil do MVP-1

Para o primeiro incremento, as regras são deliberadamente menores:

- jornada no mesmo dia, sem cruzar a meia-noite;
- uma jornada simples vigente por colaborador;
- somente `ENTRADA` e `SAIDA` no cálculo;
- um fuso horário configurado por filial;
- sem feriados, folgas, afastamentos ou fechamento automático;
- nenhuma alteração retroativa sem uma solicitação explícita.

## 3. Eventos e sequência

| BR | Regra |
| --- | --- |
| BR-001 | O sistema reconhece `ENTRADA`, `INICIO_INTERVALO`, `FIM_INTERVALO` e `SAIDA`. |
| BR-002 | A sequência normal pode ser `ENTRADA → SAIDA` ou `ENTRADA → INICIO_INTERVALO → FIM_INTERVALO → SAIDA`, conforme a jornada configurada e a operação do colaborador. |
| BR-003 | Um evento fora da sequência esperada deve ser rejeitado ou marcado como inconsistência, conforme o contexto definido pela política de RH; não pode ser silenciosamente aceito. |
| BR-004 | O colaborador só pode registrar a própria jornada; registros em nome de outra pessoa exigem permissão administrativa e fluxo de ajuste. |
| BR-005 | O mesmo comando não pode criar eventos duplicados. A API deve exigir uma chave de idempotência para o registro de ponto. |
| BR-006 | Cada evento deve registrar data/hora, tipo, colaborador, autor, origem e identificador de correlação quando disponível. |
| BR-007 | Colaborador inativo não pode criar novos eventos, mas seus registros históricos permanecem consultáveis conforme permissão. |

## 4. Cálculo

| BR | Regra |
| --- | --- |
| BR-008 | Horas trabalhadas são a soma dos períodos `ENTRADA → INICIO_INTERVALO` e `FIM_INTERVALO → SAIDA`, ou `ENTRADA → SAIDA` quando não houver intervalo registrado. |
| BR-009 | O resumo diário do MVP-1 deve indicar jornada prevista, jornada realizada, saldo básico e inconsistências. Atrasos, horas extras e banco de horas entram no MVP-2. |
| BR-010 | No MVP-1, o saldo básico é `jornada realizada - jornada prevista`, sem arredondamento ou tolerância. Parâmetros adicionais entram no MVP-2. |
| BR-011 | Horas extras são o saldo positivo elegível após tolerância e demais parâmetros configurados. Percentuais, limites e aprovação devem ser parametrizáveis. |
| BR-012 | Atrasos são diferenças negativas entre o início realizado e o início previsto, após a tolerância configurada. |
| BR-013 | Banco de horas acumula saldos conforme a política da organização e deve manter o detalhamento dos lançamentos que compõem o total. |
| BR-014 | Toda alteração relevante em evento, configuração ou aprovação deve disparar recálculo do resumo afetado. |
| BR-015 | Se não houver dados suficientes para um cálculo confiável, o sistema deve marcar a inconsistência e explicar o motivo. |

## 5. Justificativas e ajustes

| BR | Regra |
| --- | --- |
| BR-016 | Uma justificativa deve conter colaborador, data/período, motivo, autor, data de criação e status. |
| BR-017 | Ajuste não apaga o registro original; deve manter valor anterior, valor proposto, justificativa e responsável. |
| BR-018 | Ajuste pendente não altera o cálculo oficial. Somente ajuste aprovado pode gerar recálculo. |
| BR-019 | O aprovador não deve aprovar sua própria solicitação quando houver separação de funções configurada. |
| BR-020 | Rejeição exige motivo e mantém o evento original como fonte do cálculo. |
| BR-021 | Depois de aprovado, o ajuste não deve ser alterado diretamente; nova correção deve gerar nova solicitação e nova trilha. |

## 6. Acesso e auditoria

| BR | Regra |
| --- | --- |
| BR-022 | O acesso a dados deve respeitar o papel e o escopo organizacional do usuário. |
| BR-023 | Colaborador consulta apenas a própria jornada; gestor consulta a equipe autorizada; RH e administrador consultam o escopo concedido. |
| BR-024 | Login, falha de login, alteração de cadastro, evento de ponto, ajuste, aprovação, exportação e mudança de configuração devem ser auditados. |
| BR-025 | Evento de auditoria deve conter ator, ação, entidade, identificador, data/hora, resultado e correlação. |
| BR-026 | Auditoria é somente de acréscimo para usuários da aplicação; correções técnicas devem possuir procedimento administrativo próprio. |

## 7. Idempotência e concorrência

| BR | Regra |
| --- | --- |
| BR-027 | A primeira requisição com uma chave de idempotência válida persiste o evento e guarda o resultado associado à chave. |
| BR-028 | Reenvio com a mesma chave e payload equivalente retorna o resultado original e não cria novo evento. A resposta pode ser `200` para indicar repetição idempotente. |
| BR-029 | Reenvio com a mesma chave e payload diferente retorna `409 Conflict` com o código `IDEMPOTENCY_KEY_REUSED`. |
| BR-030 | A gravação deve ocorrer em transação com bloqueio lógico por `employee_id + work_date`, usando bloqueio de linha (`SELECT ... FOR UPDATE`) ou mecanismo equivalente do PostgreSQL. |
| BR-031 | A validação da sequência deve ocorrer depois da aquisição do bloqueio e antes da inserção do evento. |
| BR-032 | Uma falha em persistência, cálculo ou auditoria desfaz a operação inteira; não pode existir evento sem resumo/auditoria correspondente quando ambos forem obrigatórios. |

## 8. Decisões fechadas para o MVP-1

- jornada no mesmo dia;
- entrada e saída como ciclo direto, ou entrada, intervalo e saída quando o intervalo for usado;
- um fuso por filial;
- cálculo em minutos, sem arredondamento;
- nenhuma regra de feriado, folga ou afastamento;
- nenhum fechamento automático;
- nenhuma alteração retroativa sem fluxo específico.

## 9. Parâmetros que precisam de decisão para o MVP-2

As regras abaixo continuam adiadas e não devem ser implementadas como comportamento implícito:

- quantidade de intervalos permitidos por jornada;
- jornadas que atravessam a meia-noite;
- fuso horário por filial e horário de verão;
- arredondamento e tolerância por evento;
- percentuais, limites e aprovação de hora extra;
- tratamento de feriados, folgas, faltas e afastamentos;
- política de fechamento e reabertura de períodos;
- retenção e descarte de registros e auditoria.

Até a decisão, a implementação do MVP-2 deve modelar esses itens como configuração ou extensão, sem fixar um comportamento irreversível.
