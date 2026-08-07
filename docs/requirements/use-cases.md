# Casos de uso

## 1. Atores e permissões resumidas

| Ator | Pode fazer no MVP |
| --- | --- |
| Colaborador | Autenticar, registrar ponto, consultar a própria jornada e solicitar justificativa |
| Gestor | Consultar equipe, analisar e aprovar ajustes dentro do escopo |
| RH | Administrar cadastros, jornadas, ajustes, justificativas, relatórios e indicadores |
| Administrador | Administrar usuários, papéis, parâmetros e auditoria técnica |
| Diretoria | Consultar dashboards e relatórios autorizados |

## 2. Distribuição por incremento

| Incremento | Casos de uso |
| --- | --- |
| MVP-1 | UC-001, UC-002, UC-003 em jornada simples, UC-004 para entrada/saída, UC-005 para consulta própria e UC-011 para papéis/parâmetros mínimos |
| MVP-2 | UC-004 com intervalo, UC-005 para gestores/RH, UC-006, UC-007, UC-008, UC-009 e UC-010 |

## UC-001 — Autenticar usuário

**Atores:** qualquer usuário ativo.  
**Pré-condições:** credencial cadastrada e usuário ativo.

**Fluxo principal:**

1. Usuário informa identificador e senha.
2. Sistema valida a credencial e o status.
3. Sistema cria sessão/token com expiração.
4. Sistema registra o login na auditoria.
5. Usuário acessa a área permitida ao seu papel.

**Exceções:** credencial inválida, usuário inativo, sessão expirada ou excesso de tentativas. Nenhuma exceção deve revelar dados sensíveis.

## UC-002 — Administrar colaborador

**Atores:** RH, administrador.

1. Ator abre o cadastro e informa dados obrigatórios, vínculo e jornada.
2. Sistema valida unicidade e referências organizacionais.
3. Sistema grava o colaborador e registra auditoria.
4. Ator pode editar ou desativar sem apagar o histórico.

**Alternativa:** ao desativar, o sistema bloqueia novos registros de ponto e mantém consultas históricas autorizadas.

## UC-003 — Configurar jornada

**Atores:** RH, administrador.

1. Ator cria uma jornada simples com início, fim, fuso e vigência. Tolerâncias, intervalo e escalas entram no MVP-2.
2. Sistema valida intervalos e vigência.
3. Ator vincula a jornada a colaboradores ou grupo autorizado.
4. Sistema registra a versão da configuração.

**Resultado:** a configuração ativa é usada pelos próximos cálculos; alterações retroativas exigem permissão e recálculo controlado.

## UC-004 — Registrar evento de ponto

**Ator:** colaborador.

**Pré-condições:** sessão válida, colaborador ativo e jornada disponível.

1. Colaborador solicita o registro.
2. Sistema identifica o próximo tipo esperado (`ENTRADA` ou `SAIDA` no MVP-1).
3. Sistema valida sequência, idempotência e horário.
4. Sistema grava o evento e os metadados.
5. Sistema recalcula o resumo diário.
6. Sistema audita a operação e retorna a confirmação.

**Exceções:** evento fora de ordem, duplicidade, colaborador inativo, jornada inexistente ou falha de persistência. O usuário recebe uma mensagem acionável e o sistema não cria um evento parcial.

## UC-005 — Consultar jornada

**Atores:** colaborador, gestor, RH, diretoria.

1. Ator informa período e filtros permitidos.
2. Sistema valida o escopo de acesso.
3. Sistema retorna eventos, resumo diário, saldo e inconsistências.
4. Ator pode abrir os detalhes de um dia.

**Regra de acesso:** colaborador vê apenas seus dados; demais perfis dependem de papel e escopo organizacional.

## UC-006 — Solicitar justificativa ou ajuste

**Atores:** colaborador, gestor, RH.

1. Ator seleciona a data ou evento.
2. Informa motivo e, quando aplicável, o novo horário proposto.
3. Sistema valida permissão e dados obrigatórios.
4. Sistema cria solicitação pendente, preservando o original.
5. Sistema notifica o próximo aprovador quando essa capacidade estiver disponível.

**Resultado:** o cálculo oficial permanece inalterado enquanto a solicitação estiver pendente.

## UC-007 — Aprovar ou rejeitar ajuste

**Ator:** gestor ou RH autorizado.

1. Ator consulta solicitações pendentes do seu escopo.
2. Abre o valor original, proposta e justificativa.
3. Aprova ou rejeita e informa observação quando necessário.
4. Sistema registra decisão e auditoria.
5. Se aprovado, aplica a versão autorizada e recalcula o resumo.

**Exceções:** solicitação já decidida, aprovador sem permissão ou conflito de segregação de funções.

## UC-008 — Emitir relatório

**Atores:** RH, gestor, diretoria.

1. Ator escolhe relatório diário, semanal ou mensal.
2. Define período e filtros.
3. Sistema valida o escopo e calcula/consulta os dados.
4. Sistema exibe prévia.
5. Ator exporta para Excel ou PDF.
6. Sistema registra a exportação na auditoria.

## UC-009 — Consultar dashboard

**Atores:** gestor, RH, diretoria.

1. Ator seleciona período e escopo.
2. Sistema consolida horas extras, banco de horas, atrasos e absenteísmo.
3. Sistema apresenta indicadores e permite abrir o detalhamento correspondente.

## UC-010 — Consultar auditoria

**Atores:** RH autorizado, administrador.

1. Ator informa filtros de usuário, ação, entidade e período.
2. Sistema aplica autorização e retorna eventos imutáveis.
3. Ator visualiza detalhes, incluindo antes/depois quando disponível.

## UC-011 — Administrar papéis e parâmetros

**Ator:** administrador.

1. Administrador cria ou altera papéis e permissões permitidos.
2. Configura parâmetros operacionais não legais.
3. Sistema valida impacto e registra a alteração.
4. Novas permissões passam a valer conforme a política de sessão definida.

## 3. Critérios transversais

- Toda operação de escrita deve ser idempotente quando houver risco de reenvio.
- Toda operação crítica deve ser transacional e auditável.
- Toda mensagem de erro deve orientar o usuário sem expor detalhes internos.
- Toda consulta deve respeitar filtros e escopo do ator autenticado.
