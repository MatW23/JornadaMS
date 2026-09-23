# ADR-002 — Divisão do MVP em dois incrementos

- **Status:** Aceito
- **Data:** 2026-08-07
- **Escopo:** Planejamento do MVP do JornadaMS

## Contexto

O escopo original agrupava autenticação, cadastro, registro, intervalos, cálculos avançados, banco de horas, justificativas, aprovações, relatórios, exportações, dashboard e auditoria avançada. Esse conjunto é grande demais para validar rapidamente o principal risco do produto: registrar uma jornada e gerar um resumo confiável.

## Decisão

Dividir a primeira versão em dois incrementos:

- **MVP-1:** login, colaboradores, jornada simples, entrada, saída, histórico, cálculo diário básico, RBAC mínimo, idempotência, concorrência e auditoria básica.
- **MVP-2:** intervalo, tolerâncias, atrasos, justificativas, ajustes, aprovação, banco de horas, horas extras, relatórios, exportações, dashboard e auditoria administrativa avançada.

O MVP-1 será validado em uma instalação para uma única organização. Empresas e filiais permanecem no modelo como estrutura organizacional, mas não haverá isolamento SaaS entre clientes.

### Evolução posterior

Durante a implementação, o fluxo de intervalo e tolerância básica foi antecipado para validar a modelagem de eventos e o cálculo antes do trabalho de ajustes e relatórios. Essa antecipação não altera o critério de entrada do MVP-2: as capacidades administrativas avançadas continuam condicionadas à validação do núcleo.

## Alternativas consideradas

### Entregar todo o MVP original de uma vez

Rejeitada porque aumenta o tempo até a primeira validação, mistura regras de baixa e alta complexidade e dificulta identificar qual parte causou um erro operacional.

### Começar apenas com uma prova técnica de registro

Rejeitada porque um registro isolado não valida autenticação, colaborador, jornada, persistência, cálculo e consulta como fluxo de produto.

## Consequências

- feedback real chega mais cedo;
- o motor de cálculo começa com regras explícitas e pequenas;
- relatórios e banco de horas não bloqueiam a validação do núcleo;
- o modelo de dados continua preparado para MVP-2;
- será necessário preservar compatibilidade entre os incrementos;
- o termo “MVP” deve ser sempre qualificado como MVP-1 ou MVP-2 nos requisitos e no backlog.

## Critério para iniciar o MVP-2

O MVP-2 só deve começar quando o MVP-1 tiver testes essenciais aprovados, registro concorrente validado, auditoria básica funcionando e feedback de usuários sobre o fluxo de entrada/saída.
