# ADR-001 — Monólito modular como arquitetura inicial

- **Status:** Aceito
- **Data:** 2026-08-07
- **Escopo:** MVP do JornadaMS

## Contexto

O JornadaMS precisa centralizar regras de jornada, cálculos, auditoria e consultas para organizações em crescimento. O produto deve evoluir para integrações, BI e funcionalidades de Workforce Management, mas o MVP ainda possui uma equipe e um domínio em consolidação.

## Decisão

Iniciar o sistema como um monólito modular, organizado por domínios de negócio e implementado com Clean Architecture. A aplicação terá módulos com fronteiras explícitas, baixo acoplamento e contratos internos claros. A API REST será a interface de entrada da aplicação web.

## Alternativas consideradas

### Microsserviços desde o início

Rejeitada para o MVP por introduzir complexidade de deploy, observabilidade, comunicação distribuída, consistência e operação antes de haver necessidade comprovada.

### Monólito sem modularização

Rejeitada porque facilitaria acoplamento entre cadastro, jornada, cálculo e relatórios, dificultando testes e futuras extrações.

### Serverless como arquitetura principal

Adiada porque não há, no momento, uma necessidade de escala variável ou integração que compense a maior dependência de plataforma.

## Consequências positivas

- desenvolvimento e implantação mais simples;
- transações locais para registro, cálculo e auditoria;
- menor custo operacional inicial;
- possibilidade de testar módulos com rapidez;
- caminho de evolução para serviços independentes.

## Consequências e cuidados

- os limites de módulo precisam ser respeitados desde o primeiro commit;
- consultas compartilhadas não devem criar dependências ocultas;
- um monólito ainda pode exigir otimização e escalabilidade horizontal;
- a extração futura só será segura se contratos e ownership estiverem documentados.

## Critérios para reavaliar a decisão

Revisar este ADR somente quando houver evidência de pelo menos um destes fatores: necessidade de escala independente, domínio suficientemente estável, times autônomos por módulo, requisito de disponibilidade isolada ou gargalo que não possa ser resolvido dentro do monólito.
