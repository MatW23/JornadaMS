# Contrato da API

## 1. Status

Este documento explica o contrato da API REST privada usada pela aplicação web. A especificação executável do MVP-1 está em [openapi.yaml](openapi.yaml). Este Markdown documenta decisões, permissões e regras que complementam o arquivo OpenAPI. A API não é pública para terceiros.

As operações marcadas como MVP-1 nas seções abaixo devem estar refletidas no `openapi.yaml`. Operações marcadas como MVP-2 são referências de roadmap e só entrarão na especificação executável quando o respectivo épico começar.

Implementado no servidor neste incremento: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` e `GET /api/v1/me`. As demais operações MVP-1 continuam como contrato de implementação futura.

## 2. Convenções

- Base URL: `/api/v1`.
- Health checks operacionais ficam fora da versão da API: `/health/live` e `/health/ready`.
- JSON UTF-8 em requisições e respostas.
- Autenticação web: cookies `HttpOnly`, `SameSite=Lax` (`jornada_access` e `jornada_refresh`); integrações podem usar `Authorization: Bearer <jwt>`.
- Datas: ISO 8601; persistência em UTC e apresentação no fuso da organização.
- Recursos pagináveis usam `page`, `page_size`, `sort` e filtros explícitos.
- `page_size` padrão é `50` e o limite máximo é `100`.
- Escritas críticas aceitam `Idempotency-Key`; no registro de ponto, o header é obrigatório.
- Respostas de erro possuem `code`, `message`, `details` e `correlation_id`.
- O login aplica limitação configurável de tentativas e retorna `429` com `Retry-After` quando o limite é excedido.

## 3.1 Enums e schemas mínimos do MVP-1

```text
TimeEventType = ENTRADA | INICIO_INTERVALO | FIM_INTERVALO | SAIDA
TimeEventSource = WEB
TimeEventStatus = VALID | SUPERSEDED | INVALID | REJECTED
DailySummaryStatus = IN_PROGRESS | COMPLETE | INCONSISTENT
EmployeeStatus = ACTIVE | INACTIVE
ScheduleStatus = ACTIVE | INACTIVE
```

`POST /employees` recebe `name`, `registration_code`, `punch_identifier` opcional, `branch_id`, `department_id` opcional, `position_id` opcional e `user_id` opcional. `registration_code` é matrícula interna única por organização; a organização é derivada da filial e não é enviada pelo cliente. Não é CPF.

`POST /work-schedules` no MVP-1 recebe `name`, `start_time`, `end_time`, `same_day_only=true` e `tolerance_minutes=0`. `break_start` e `break_end` são opcionais, mas devem ser enviados juntos e ficar estritamente dentro da jornada. O fuso é herdado da filial do colaborador; não há fuso independente por jornada no MVP-1.

`POST /time-events` recebe `event_type`, `occurred_at` e `source`. O `employee_id` é derivado do usuário autenticado para o papel Colaborador; um administrador só pode informar outro colaborador mediante permissão explícita.

`GET /attendance/days` retorna `work_date`, `scheduled_minutes`, `worked_minutes`, `balance_minutes`, `status` e os eventos daquele dia.

## 3.2 Resposta de erro

```json
{
  "error": {
    "code": "TIME_EVENT_OUT_OF_ORDER",
    "message": "O próximo evento esperado é o início do intervalo.",
    "details": [],
    "correlation_id": "01J..."
  }
}
```

| HTTP | Uso |
| --- | --- |
| `400` | Dados malformados ou regra de entrada inválida |
| `401` | Token ausente, inválido ou expirado |
| `403` | Usuário autenticado sem permissão |
| `404` | Recurso inexistente ou fora do escopo |
| `409` | Conflito de estado, duplicidade ou idempotência |
| `422` | Campos semanticamente inválidos |
| `429` | Limite de tentativas/requisições excedido |
| `500` | Falha interna; detalhes ficam apenas nos logs |

## 4. Autenticação e sessões

| Método | Endpoint | Acesso | Descrição |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Público | Inicia sessão (MVP-1) |
| `POST` | `/auth/refresh` | Refresh token | Renova sessão (MVP-1) |
| `POST` | `/auth/logout` | Autenticado | Revoga a sessão atual (MVP-1) |
| `GET` | `/me` | Autenticado | Retorna usuário, papel e escopo (MVP-1) |

O access token é um JWT curto. O refresh token é opaco, rotativo e persistido somente como hash em `sessions`. No navegador, ambos são enviados em cookies `HttpOnly`; em produção os cookies também usam `Secure`. Logout revoga a sessão e remove os cookies; refresh inválido, expirado ou revogado retorna `401`.

O corpo de login ainda retorna os tokens para compatibilidade com clientes não-browser. O cliente web oficial não os persiste nem os lê: usa exclusivamente os cookies. Requisições de alteração dependem de `SameSite=Lax` e de origem same-origin; uma futura exposição cross-origin deverá adicionar proteção CSRF explícita.

Exemplo de login:

```json
{
  "email": "mariana@empresa.example",
  "password": "senha-do-usuario"
}
```

## 5. Cadastros

As operações de empresas, filiais, colaboradores e ativação/desativação do MVP-1 já fazem parte do contrato executável. Detalhes de empresa, departamentos e cargos permanecem planejados para o MVP-2.

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET/POST` | `/companies` | Admin/RH | Listar/criar empresas (provisionamento; MVP-1) |
| `GET/PATCH` | `/companies/{company_id}` | Admin/RH | Consultar/alterar empresa (MVP-2) |
| `GET/POST` | `/branches` | Admin/RH | Listar/criar filiais (provisionamento; MVP-1) |
| `GET/POST` | `/departments` | Admin/RH | Listar/criar departamentos (MVP-2) |
| `GET/POST` | `/positions` | Admin/RH | Listar/criar cargos (MVP-2) |
| `GET/POST` | `/employees` | Admin/RH | Listar/criar colaboradores (MVP-1) |
| `GET/PATCH` | `/employees/{employee_id}` | Admin/RH | Consultar/alterar colaborador (MVP-1) |
| `POST` | `/employees/{employee_id}/activate` | Admin/RH | Ativar colaborador (MVP-1) |
| `POST` | `/employees/{employee_id}/deactivate` | Admin/RH | Desativar colaborador (MVP-1) |

## 6. Jornadas e eventos

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET/POST` | `/work-schedules` | Admin/RH | Listar/criar jornada simples (MVP-1) |
| `GET/PATCH` | `/work-schedules/{schedule_id}` | Admin/RH | Consultar/alterar jornada (MVP-1) |
| `POST` | `/employees/{employee_id}/schedules` | Admin/RH | Vincular jornada com vigência (MVP-1) |
| `POST` | `/time-events` | Colaborador | Registrar entrada, intervalo e saída (MVP-1) |
| `GET` | `/time-events` | Escopo autorizado | Consultar eventos (MVP-1) |
| `GET` | `/attendance/days` | Escopo autorizado | Consultar resumo diário (MVP-1) |
| `GET` | `/attendance/summary` | Escopo autorizado | Consolidar período (MVP-2) |

`GET /reports/attendance` gera uma prévia administrativa dos resumos diários existentes, com filtro opcional por colaborador/status, paginação e totais do período. `GET /reports/attendance/export?format=csv` (o parâmetro `format` é opcional nesta primeira versão) exporta o mesmo conjunto em CSV compatível com Excel e registra a exportação na auditoria. O período máximo é de 366 dias.

Exemplo de registro do MVP-1:

```json
{
  "event_type": "ENTRADA",
  "occurred_at": "2026-08-07T08:00:00-03:00",
  "source": "WEB"
}
```

O header `Idempotency-Key` é obrigatório. Na primeira gravação, a resposta é `201 Created`; reenvio com a mesma chave e payload equivalente retorna `200 OK` com o mesmo resultado; reuso da chave com payload diferente retorna `409 Conflict` e `IDEMPOTENCY_KEY_REUSED`. O servidor serializa gravações concorrentes por colaborador e data antes de validar a sequência.

A sequência aceita é `ENTRADA -> SAIDA` para jornadas sem intervalo ou `ENTRADA -> INICIO_INTERVALO -> FIM_INTERVALO -> SAIDA` quando o colaborador registra o intervalo. O par de intervalo é indivisível: não é permitido finalizar um intervalo que não foi iniciado nem sair enquanto ele estiver aberto.

Resposta de referência:

```json
{
  "event": {
    "id": "7b2f...",
    "employee_id": "9a11...",
    "event_type": "ENTRADA",
    "occurred_at": "2026-08-07T11:00:00Z",
    "status": "VALID"
  },
  "daily_summary": {
    "work_date": "2026-08-07",
    "worked_minutes": 0,
    "balance_minutes": 0,
    "status": "IN_PROGRESS"
  }
}
```

## 7. Justificativas e ajustes

As solicitações de ajuste abaixo já fazem parte do `openapi.yaml` executável. A aprovação cria um evento substituto, mantém o evento anterior com status `SUPERSEDED`, recalcula o resumo diário e registra a decisão na auditoria.

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET/POST` | `/justifications` | Colaborador/RH | Consultar/criar justificativa (MVP-2) |
| `GET/POST` | `/adjustment-requests` | Colaborador/RH | Consultar/criar solicitação (MVP-2) |
| `POST` | `/adjustment-requests/{id}/approve` | RH/Admin | Aprovar e recalcular |
| `POST` | `/adjustment-requests/{id}/reject` | RH/Admin | Rejeitar |
| `GET` | `/employees/{id}/attendance-history` | Escopo autorizado | Consultar histórico e versões (MVP-2) |

## 8. Relatórios, dashboard e auditoria

As rotas desta seção ainda estão em evolução no MVP-2.

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET` | `/reports/attendance` | Gestor/RH/Diretoria | Prévia do relatório por período (MVP-2) |
| `GET` | `/reports/attendance/export?format=xlsx` | Gestor/RH/Diretoria | Exportar Excel |
| `GET` | `/reports/attendance/export?format=pdf` | Gestor/RH/Diretoria | Exportar PDF |
| `GET` | `/dashboards/attendance` | Gestor/RH/Diretoria | Indicadores básicos (MVP-2) |
| `GET` | `/audit-events` | Admin/RH autorizado | Consultar auditoria (MVP-2) |

Exportações devem aplicar exatamente o mesmo escopo da consulta que as originou e registrar um evento de auditoria.

## 9. Paginação e filtros

Exemplo:

```text
GET /api/v1/attendance/days?from=2026-08-01&to=2026-08-31&employee_id=...&page=1&page_size=50
```

Resposta paginada:

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total_items": 0,
  "total_pages": 0
}
```

## 10. Saúde e versionamento

- `GET /health/live`: processo está em execução.
- `GET /health/ready`: dependências mínimas estão disponíveis.
- Mudanças incompatíveis devem criar `/api/v2`; mudanças aditivas podem permanecer em v1.
- A especificação OpenAPI gerada pela aplicação deve ser a fonte técnica final quando os endpoints forem implementados.

## 11. Matriz de permissões do MVP-1

| Recurso | Colaborador | Administrador |
| --- | --- | --- |
| Login, refresh e logout | Própria sessão | Própria sessão |
| Consultar próprio perfil | Sim | Sim |
| Criar/alterar colaborador | Não | Sim |
| Criar jornada simples | Não | Sim |
| Registrar entrada/saída | Próprio colaborador | Com permissão explícita |
| Consultar resumo diário | Próprio colaborador | Escopo da organização |
| Consultar auditoria | Não | MVP-2 / permissão específica |
