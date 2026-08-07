# Contrato da API

## 1. Status

Este documento define o contrato de referência da API REST privada usada pela aplicação web do MVP. Ele não representa uma API pública para terceiros. Quando a implementação começar, o contrato deverá ser publicado também em OpenAPI YAML/JSON e validado automaticamente no pipeline.

## 2. Convenções

- Base URL: `/api/v1`.
- JSON UTF-8 em requisições e respostas.
- Autenticação: `Authorization: Bearer <jwt>`.
- Datas: ISO 8601; persistência em UTC e apresentação no fuso da organização.
- Recursos pagináveis usam `page`, `page_size`, `sort` e filtros explícitos.
- Escritas críticas aceitam `Idempotency-Key`.
- Respostas de erro possuem `code`, `message`, `details` e `correlation_id`.

## 3. Resposta de erro

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

## 4. Autenticação

| Método | Endpoint | Acesso | Descrição |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Público | Inicia sessão |
| `POST` | `/auth/refresh` | Refresh token | Renova sessão |
| `POST` | `/auth/logout` | Autenticado | Encerra sessão |
| `GET` | `/me` | Autenticado | Retorna usuário, papel e escopo |

Exemplo de login:

```json
{
  "email": "mariana@empresa.example",
  "password": "senha-do-usuario"
}
```

## 5. Cadastros

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET/POST` | `/companies` | Admin/RH | Listar/criar empresas |
| `GET/PATCH` | `/companies/{company_id}` | Admin/RH | Consultar/alterar empresa |
| `GET/POST` | `/branches` | Admin/RH | Listar/criar filiais |
| `GET/POST` | `/departments` | Admin/RH | Listar/criar departamentos |
| `GET/POST` | `/positions` | Admin/RH | Listar/criar cargos |
| `GET/POST` | `/employees` | Admin/RH | Listar/criar colaboradores |
| `GET/PATCH` | `/employees/{employee_id}` | Admin/RH | Consultar/alterar colaborador |
| `POST` | `/employees/{employee_id}/activate` | Admin/RH | Ativar colaborador |
| `POST` | `/employees/{employee_id}/deactivate` | Admin/RH | Desativar colaborador |

## 6. Jornadas e eventos

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET/POST` | `/work-schedules` | Admin/RH | Listar/criar jornadas |
| `GET/PATCH` | `/work-schedules/{schedule_id}` | Admin/RH | Consultar/alterar jornada |
| `POST` | `/employees/{employee_id}/schedules` | Admin/RH | Vincular jornada com vigência |
| `POST` | `/time-events` | Colaborador | Registrar evento de ponto |
| `GET` | `/time-events` | Escopo autorizado | Consultar eventos |
| `GET` | `/attendance/days` | Escopo autorizado | Consultar resumo diário |
| `GET` | `/attendance/summary` | Escopo autorizado | Consolidar período |

Exemplo de registro:

```json
{
  "event_type": "ENTRADA",
  "occurred_at": "2026-08-07T08:00:00-03:00",
  "source": "WEB"
}
```

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

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET/POST` | `/justifications` | Colaborador/RH | Consultar/criar justificativa |
| `GET/POST` | `/adjustment-requests` | Colaborador/RH | Consultar/criar solicitação |
| `GET` | `/adjustment-requests/{id}` | Escopo autorizado | Consultar detalhe |
| `POST` | `/adjustment-requests/{id}/approve` | Gestor/RH | Aprovar |
| `POST` | `/adjustment-requests/{id}/reject` | Gestor/RH | Rejeitar |
| `GET` | `/employees/{id}/attendance-history` | Escopo autorizado | Consultar histórico e versões |

## 8. Relatórios, dashboard e auditoria

| Método | Endpoint | Papel mínimo | Descrição |
| --- | --- | --- | --- |
| `GET` | `/reports/attendance` | Gestor/RH/Diretoria | Prévia do relatório por período |
| `GET` | `/reports/attendance/export?format=xlsx` | Gestor/RH/Diretoria | Exportar Excel |
| `GET` | `/reports/attendance/export?format=pdf` | Gestor/RH/Diretoria | Exportar PDF |
| `GET` | `/dashboards/attendance` | Gestor/RH/Diretoria | Indicadores básicos |
| `GET` | `/audit-events` | Admin/RH autorizado | Consultar auditoria |

Exportações devem aplicar exatamente o mesmo escopo da consulta que as originou e registrar um evento de auditoria.

## 9. Paginação e filtros

Exemplo:

```text
GET /api/v1/attendance/days?from=2026-08-01&to=2026-08-31&branch_id=...&page=1&page_size=50
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
