# Roadmap do JornadaMS

O roadmap detalhado de produto está na [Product Vision](../vision/ProductVision.md#16-roadmap). Este documento resume as entregas e os critérios para avançar de versão.

## 1.0 — MVP

**Objetivo:** substituir o processo manual de registro de jornada em dois incrementos controlados.

### MVP-1 — Registro básico

**Entregas:** login, logout, sessões, cadastro de colaboradores, jornada simples, entrada, saída, validação de sequência, cálculo diário básico, histórico, RBAC mínimo, auditoria básica e separação visual entre área administrativa e registro do colaborador.

**Critérios de saída:** usuário autenticado consegue registrar entrada e saída uma única vez por operação, consultar o resumo diário e obter resultado consistente sob reenvio e concorrência.

### MVP-2 — Gestão administrativa

**Entregas:** intervalo e tolerâncias (antecipados para a validação técnica atual), atrasos, justificativas, ajustes, aprovação, banco de horas, horas extras, relatórios, exportações, dashboard e auditoria avançada.

**Critérios de saída:** regras administrativas validadas por RH, relatórios conferidos, operações críticas auditáveis, testes essenciais aprovados e validação com usuários representativos.

## 1.5 — Expansão operacional

**Objetivo:** reduzir ainda mais o trabalho administrativo.

**Entregas previstas:** integrações com ERP/folha, APIs para parceiros, notificações, alertas, aprovações ampliadas, Redis e dashboards avançados.

**Critérios de saída:** integrações com contratos versionados, observabilidade das sincronizações, reprocessamento seguro e indicadores de adoção.

## 2.0 — Inteligência operacional

**Objetivo:** transformar dados de jornada em apoio à decisão.

**Entregas previstas:** aplicativo mobile, dispositivos de registro, geolocalização, BI em tempo real, analytics e detecção assistida de inconsistências.

**Critérios de saída:** métricas de precisão, privacidade e desempenho definidas para cada capacidade antes da liberação.

## 3.0 — Workforce Management

**Objetivo:** consolidar a plataforma como solução ampla de gestão da força de trabalho.

**Entregas previstas:** férias, benefícios, documentos, workflows, escalas avançadas, turnos, compliance, multiempresa e marketplace de integrações.

**Critérios de saída:** fronteiras de domínio maduras e revisão da arquitetura conforme volume, equipes e requisitos de isolamento.

## Governança do roadmap

- A prioridade deve combinar valor para usuário, risco, dependências e esforço.
- Uma funcionalidade futura não entra no MVP sem alteração explícita da Product Vision.
- Mudança arquitetural relevante deve atualizar o ADR correspondente.
- Cada release deve ter métricas de sucesso, plano de rollback e evidência de teste.
