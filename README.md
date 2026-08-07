# JornadaMS

Plataforma corporativa para registro, cálculo e gestão da jornada de trabalho.

> Estado atual: documentação funcional e técnica em elaboração; a implementação ainda está em fase de preparação.

## Objetivo

O JornadaMS substitui controles manuais de ponto por uma solução centralizada, auditável e preparada para apoiar o RH, gestores operacionais e colaboradores. O MVP concentra-se no registro eletrônico de jornada, cálculos básicos, ajustes justificados, relatórios e controle de acesso.

## Documentação

| Documento | Finalidade |
| --- | --- |
| [Product Vision](docs/vision/ProductVision.md) | Contexto, objetivos, personas, escopo do MVP, roadmap e glossário |
| [Arquitetura](docs/architecture/architecture.md) | Componentes, camadas, fluxos, segurança e evolução arquitetural |
| [ADR-001](docs/architecture/adr/ADR-001-modular-monolith.md) | Decisão pelo monólito modular no início do produto |
| [ADR-002](docs/architecture/adr/ADR-002-mvp-em-incrementos.md) | Decisão de dividir o MVP em dois incrementos |
| [Requisitos funcionais](docs/requirements/functional-requirements.md) | Capacidades que o sistema deve oferecer |
| [Requisitos não funcionais](docs/requirements/non-functional-requirements.md) | Metas de qualidade, segurança, desempenho e operação |
| [Regras de negócio](docs/requirements/business-rules.md) | Regras de jornada, cálculos, ajustes e auditoria |
| [Casos de uso](docs/requirements/use-cases.md) | Interações esperadas entre usuários e sistema |
| [Modelo de dados](docs/database/model.md) | Entidades, relacionamentos, integridade e índices |
| [Contrato da API](docs/api/openapi.md) | Convenções e endpoints da API privada do MVP |
| [Diretrizes de UI](docs/ui/figma.md) | Arquitetura de informação, telas e critérios para o Figma |
| [Roadmap](docs/roadmap/roadmap.md) | Entregas por versão e critérios de saída |
| [Backlog do MVP-1](docs/roadmap/mvp-1-backlog.md) | Tarefas técnicas e critérios de aceite da primeira fatia vertical |

## Escopo incremental

O [MVP-1](docs/vision/ProductVision.md#10-escopo-do-mvp) entrega login, cadastro de colaboradores, jornada simples, entrada, saída, histórico, validação de sequência, cálculo diário básico e auditoria mínima.

O MVP-2 adiciona intervalo, justificativas, ajustes, aprovações, banco de horas, relatórios, exportações, dashboard e auditoria administrativa avançada.

O MVP será implantado para uma única organização. Empresas e filiais permanecem no modelo como estrutura organizacional, mas não existe isolamento SaaS entre clientes. Reconhecimento facial, dispositivos biométricos, RFID, QR Code, integrações externas, API pública, aplicativo mobile, notificações em tempo real e multiidioma continuam fora do escopo.

## Arquitetura resumida

O produto será iniciado como um monólito modular, com Clean Architecture, modelagem orientada ao domínio e API REST privada para a aplicação web. A stack prevista é Python/FastAPI no back-end, React/TypeScript no front-end e PostgreSQL como banco principal. Redis, mensageria, observabilidade avançada e microsserviços são evoluções condicionadas à necessidade real.

## Organização do repositório

```text
docs/
├── api/             Contrato da API
├── architecture/    Arquitetura e ADRs
├── database/        Modelo de dados e ERD
├── requirements/    Requisitos, regras e casos de uso
├── roadmap/         Planejamento por versão
├── ui/              Diretrizes de interface
└── vision/          Product Vision
src/jornada_ms/      Código da aplicação
tests/               Testes automatizados
```

## Como usar esta documentação

1. Leia a [Product Vision](docs/vision/ProductVision.md) para entender o problema e o escopo.
2. Consulte os [requisitos funcionais](docs/requirements/functional-requirements.md) e [casos de uso](docs/requirements/use-cases.md) para definir comportamento.
3. Use as [regras de negócio](docs/requirements/business-rules.md) como fonte para o domínio.
4. Consulte a [arquitetura](docs/architecture/architecture.md), o [modelo de dados](docs/database/model.md) e o [contrato da API](docs/api/openapi.md) durante a implementação.

## Convenções de documentação

- Requisitos, regras e casos de uso possuem identificadores estáveis (`FR`, `NFR`, `BR` e `UC`).
- Itens classificados como “a confirmar” não devem ser implementados como decisão definitiva.
- Alterações que afetem a arquitetura devem gerar ou atualizar um ADR.
- Exemplos de API são contratos de referência; a implementação deve manter compatibilidade ou registrar uma nova versão.

## Próximo passo

Com a documentação refinada, o próximo incremento recomendado é transformar o MVP-1 em backlog técnico e implementar a fatia vertical `login → colaborador → entrada/saída → resumo diário → testes`.
