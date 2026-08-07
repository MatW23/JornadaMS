# Roadmap do JornadaMS

O roadmap detalhado de produto está na [Product Vision](../vision/ProductVision.md#16-roadmap). Este documento resume as entregas e os critérios para avançar de versão.

## 1.0 — MVP

**Objetivo:** substituir o processo manual de registro de jornada.

**Entregas:** cadastro organizacional e de colaboradores, jornadas simples, registro de ponto, motor de cálculo, justificativas, ajustes com aprovação, relatórios básicos, dashboard, login, RBAC e auditoria.

**Critérios de saída:** registros funcionais em ambiente real, cálculos essenciais aprovados, relatórios gerados, operações críticas auditáveis, testes essenciais aprovados e validação com usuários representativos.

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
