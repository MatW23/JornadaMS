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

## 3. Eventos e sequência

| BR | Regra |
| --- | --- |
| BR-001 | O MVP reconhece os tipos `ENTRADA`, `INICIO_INTERVALO`, `FIM_INTERVALO` e `SAIDA`. |
| BR-002 | A sequência normal do dia é `ENTRADA → INICIO_INTERVALO → FIM_INTERVALO → SAIDA`. |
| BR-003 | Um evento fora da sequência esperada deve ser rejeitado ou marcado como inconsistência, conforme o contexto definido pela política de RH; não pode ser silenciosamente aceito. |
| BR-004 | O colaborador só pode registrar a própria jornada; registros em nome de outra pessoa exigem permissão administrativa e fluxo de ajuste. |
| BR-005 | O mesmo comando não pode criar eventos duplicados. A API deve aceitar uma chave de idempotência para reenvios. |
| BR-006 | Cada evento deve registrar data/hora, tipo, colaborador, autor, origem e identificador de correlação quando disponível. |
| BR-007 | Colaborador inativo não pode criar novos eventos, mas seus registros históricos permanecem consultáveis conforme permissão. |

## 4. Cálculo

| BR | Regra |
| --- | --- |
| BR-008 | Horas trabalhadas correspondem ao tempo dos períodos de trabalho válidos, descontando intervalos configurados. |
| BR-009 | O resumo diário deve indicar jornada prevista, jornada realizada, atrasos, horas extras, saldo e inconsistências. |
| BR-010 | O saldo é calculado como jornada realizada menos jornada prevista, aplicando tolerâncias e compensações configuradas. |
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

## 7. Parâmetros que precisam de decisão

As regras abaixo foram identificadas, mas não estão fechadas na visão do produto:

- quantidade de intervalos permitidos por jornada;
- jornadas que atravessam a meia-noite;
- fuso horário por filial e horário de verão;
- arredondamento e tolerância por evento;
- percentuais, limites e aprovação de hora extra;
- tratamento de feriados, folgas, faltas e afastamentos;
- política de fechamento e reabertura de períodos;
- retenção e descarte de registros e auditoria.

Até a decisão, a implementação deve modelar esses itens como configuração ou extensão, sem fixar um comportamento irreversível.
