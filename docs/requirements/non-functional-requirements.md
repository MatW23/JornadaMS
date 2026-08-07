# Requisitos não funcionais

## 1. Metas do MVP

As metas abaixo são referências para validação e podem ser revisadas quando houver dados reais de operação. A medição deve ser feita em ambiente equivalente ao de produção e com período representativo.

| ID | Categoria | Requisito / meta | Verificação |
| --- | --- | --- | --- |
| NFR-001 | Disponibilidade | Disponibilidade mínima de 99,5% no período mensal de operação. | Monitoramento e relatório de incidentes. |
| NFR-002 | Desempenho | Tempo médio de resposta da API de até 300 ms para operações críticas, desconsiderando exportações. | Teste de carga e métricas de aplicação. |
| NFR-003 | Desempenho | Confirmação do registro de ponto em até 3 segundos em condições normais. | Teste de jornada ponta a ponta. |
| NFR-004 | Escalabilidade | Suportar o crescimento do volume diário sem alteração nas regras de negócio. | Teste de carga; capacidade inicial a confirmar com a operação. |
| NFR-005 | Integridade | Eventos, cálculos e auditoria de uma operação crítica devem ser consistentes e transacionais. | Testes de concorrência, rollback e integridade referencial. |
| NFR-006 | Segurança | Usar HTTPS/TLS, hash de senha robusto, JWT com expiração e RBAC aplicado no servidor. | Revisão de configuração e testes de segurança. |
| NFR-007 | Segurança | Validar entradas e reduzir riscos do OWASP Top 10. | SAST, DAST, revisão de dependências e testes manuais. |
| NFR-008 | Privacidade | Tratar dados pessoais com finalidade, minimização, controle de acesso, retenção e rastreabilidade compatíveis com a LGPD. | Checklist de privacidade e revisão de fluxos. |
| NFR-009 | Auditoria | Operações críticas devem produzir eventos imutáveis com autor, data/hora, entidade, ação e correlação. | Testes funcionais e inspeção de trilha. |
| NFR-010 | Manutenibilidade | Manter separação de camadas, contratos explícitos e cobertura automatizada mínima de 80% como meta de referência. | Code review, pipeline e relatório de cobertura. |
| NFR-011 | Observabilidade | Disponibilizar logs estruturados, health checks, métricas de erro e latência. | Validação em ambiente de homologação. |
| NFR-012 | Recuperação | Definir e testar backup, restauração, RPO e RTO antes da produção. | Exercício de restauração; valores de RPO/RTO ainda pendentes. |
| NFR-013 | Usabilidade | Permitir o registro de jornada com fluxo curto, mensagens claras e interface responsiva. | Testes com usuários e inspeção de acessibilidade. |
| NFR-014 | Acessibilidade | Atender boas práticas WCAG 2.1 AA para navegação, contraste, foco, formulários e mensagens de erro. | Auditoria automatizada e teste manual por teclado. |
| NFR-015 | Compatibilidade | Funcionar nas versões atuais dos principais navegadores desktop e mobile web suportados pela organização. | Matriz de compatibilidade definida antes do aceite. |
| NFR-016 | Portabilidade | Executar de forma consistente em containers e por configuração externa. | Build reproduzível e execução em ambiente limpo. |

## 2. Requisitos de segurança

1. Nenhum segredo, senha ou token deve ser armazenado no código-fonte ou em logs.
2. Endpoints devem negar acesso por padrão e exigir escopo explícito.
3. Respostas de erro não devem expor SQL, stack trace, credenciais ou dados de outros usuários.
4. Exportações devem respeitar o mesmo escopo de autorização das consultas.
5. Dados de auditoria não devem ser editáveis por usuários comuns.
6. Dependências devem ser avaliadas e atualizadas por processo definido.

## 3. Estratégia de medição

- **Desempenho:** registrar latência média e percentis por endpoint; exportações devem ter métrica separada.
- **Disponibilidade:** medir a partir de health checks externos e descontar apenas janelas de manutenção documentadas.
- **Qualidade:** acompanhar falhas de cálculo, inconsistências e defeitos encontrados após cada release.
- **Experiência:** medir tempo de registro e satisfação em testes com colaboradores.
- **Segurança:** registrar vulnerabilidades abertas por severidade e bloquear release com risco crítico sem tratamento.

## 4. Pontos a confirmar

Antes do go-live, o responsável pelo produto deve definir capacidade máxima esperada, política de retenção, RPO/RTO, navegadores suportados, janela de manutenção e critérios de disponibilidade.
