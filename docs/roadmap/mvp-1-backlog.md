# Backlog técnico — MVP-1

## Objetivo

Entregar o fluxo vertical:

```text
Login
→ Cadastro de colaborador
→ Configuração de jornada simples
→ Registro de entrada/saída
→ Resumo diário
→ Histórico
→ Auditoria básica
```

O MVP-1 é para uma única organização, com jornada no mesmo dia, entrada/saída, cálculo em minutos e sem tolerância, intervalo, feriado, fechamento automático ou alteração retroativa.

## Definition of Done

- aplicação executa localmente com configuração documentada;
- migrations criam o banco do zero;
- endpoints possuem schemas, autorização e erros definidos;
- testes unitários cobrem as regras do domínio;
- testes de integração cobrem persistência e transação;
- teste concorrente confirma que duas marcações não criam estado duplicado;
- login, logout e refresh revogável funcionam;
- registro de entrada/saída retorna resumo diário;
- auditoria básica registra sucesso, falha e negação;
- documentação da API permanece sincronizada.

## Épico 0 — Fundação

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T0.1 | Criar estrutura do monólito modular em `src/jornada_ms`. | Módulos e camadas não dependem diretamente de framework no domínio. |
| T0.2 | Configurar `pyproject.toml`, lint, testes e variáveis de ambiente. | Projeto instala, roda lint e executa um teste vazio em ambiente limpo. |
| T0.3 | Configurar PostgreSQL, SQLAlchemy e Alembic. | Banco sobe localmente e migrations aplicam/revertem sem erro. |
| T0.4 | Implementar `/health/live` e `/health/ready`. | Live não depende do banco; ready verifica dependências mínimas. |
| T0.5 | Criar middleware de correlação e tratamento de erros. | Toda resposta de erro possui `correlation_id` e não expõe stack trace. |

## Épico 1 — Identidade e sessões

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T1.1 | Criar `users`, `roles`, `user_roles` e `sessions`. | Migrations e constraints refletem o modelo documentado. |
| T1.2 | Implementar hash de senha e login. | Senha nunca aparece em logs ou respostas; credencial inválida retorna erro seguro. |
| T1.3 | Implementar JWT curto e refresh token opaco rotativo. | Refresh token é armazenado somente como hash e pode ser revogado. |
| T1.4 | Implementar logout e `GET /me`. | Logout invalida a sessão; `/me` retorna apenas o contexto autorizado. |
| T1.5 | Aplicar RBAC no servidor. | Endpoint protegido sem papel recebe `403`, independentemente da UI. |

## Épico 2 — Organização e colaborador

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T2.1 | Criar empresa e filial de provisionamento único. | CNPJ normalizado, fuso da filial e unicidade validados. |
| T2.2 | Criar entidade de colaborador. | `registration_code` é matrícula interna única por organização (`company_id`) e `user_id` pode ser nulo. |
| T2.3 | Implementar criação, consulta, edição, ativação e desativação. | Colaborador inativo não registra ponto; histórico não é apagado. |
| T2.4 | Vincular usuário ativo ao colaborador quando necessário. | Relação é opcional e única; apenas colaborador com usuário registra ponto. |

## Épico 3 — Jornada simples

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T3.1 | Criar `work_schedules` e `employee_schedules`. | Jornada exige início/fim no mesmo dia e vigência válida. |
| T3.2 | Validar fuso da filial e horários. | Horários inválidos ou jornada que cruza a meia-noite são rejeitados no MVP-1. |
| T3.3 | Vincular uma jornada vigente ao colaborador. | Não existem duas jornadas vigentes conflitantes para a mesma data. |

## Épico 4 — Registro de ponto

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T4.1 | Criar `time_events` com `work_date`, origem e correlação. | Data de negócio é calculada no fuso da filial e persistida explicitamente. |
| T4.2 | Implementar `POST /time-events` para entrada/saída. | Tipo é validado contra o próximo estado esperado. |
| T4.3 | Implementar `Idempotency-Key`. | Mesma chave/payload retorna o resultado original; chave/payload diferente retorna `409`. |
| T4.4 | Serializar concorrência por colaborador e data. | Teste paralelo não cria duas entradas ou duas saídas válidas. |
| T4.5 | Auditar registro aceito, rejeitado e falho. | Auditoria contém ator lógico, ação, resultado, correlação e metadados permitidos. |

## Épico 5 — Resumo diário

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T5.1 | Criar `daily_summaries`. | Existe no máximo um resumo por colaborador/data. |
| T5.2 | Implementar cálculo de minutos trabalhados. | Com entrada e saída válidas, `worked_minutes = saída - entrada`. |
| T5.3 | Implementar saldo básico. | `balance_minutes = worked_minutes - scheduled_minutes`, sem arredondamento. |
| T5.4 | Marcar jornada incompleta ou inválida. | Falta de saída produz status `IN_PROGRESS` ou `INCONSISTENT`, sem cálculo falso. |
| T5.5 | Implementar `GET /attendance/days`. | Colaborador consulta apenas os próprios dias; admin consulta o escopo permitido. |

## Épico 6 — Histórico e auditoria

| ID | Tarefa | Critério de aceite |
| --- | --- | --- |
| T6.1 | Implementar histórico do colaborador. | Eventos e resumos aparecem em ordem cronológica, com status. |
| T6.2 | Implementar consulta administrativa mínima de auditoria. | Administrador pode filtrar por período, ação e correlação. |
| T6.3 | Adicionar testes de autorização. | Não há acesso cruzado entre colaboradores por alteração de parâmetros na URL. |

## Ordem recomendada de implementação

1. T0.1–T0.5
2. T1.1–T1.5
3. T2.1–T2.4
4. T3.1–T3.3
5. T4.1–T4.5
6. T5.1–T5.5
7. T6.1–T6.3

## Fora deste backlog

Intervalos, tolerâncias efetivas, atrasos, banco de horas, horas extras, justificativas, ajustes, aprovações, relatórios, PDF, Excel, dashboard, notificações e integrações pertencem ao MVP-2.
