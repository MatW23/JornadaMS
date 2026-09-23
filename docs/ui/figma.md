# Diretrizes de UI e Figma

## 1. Status

Ainda não há um arquivo ou link Figma definido no repositório. Este documento funciona como briefing de interface e checklist de handoff. O primeiro protótipo funcional está em `frontend/`, servido pela própria API; o link oficial deve ser adicionado quando o projeto visual for criado.

## 2. Princípios de experiência

- **Registro rápido:** a ação principal do colaborador deve ficar visível sem navegação complexa.
- **Separação por perfil:** a área administrativa consulta e configura; somente a experiência do colaborador exibe as ações de bater ponto.
- **Preferências locais:** configurações de tema e cor de destaque devem ser acessíveis pelo ícone de configurações e persistir no navegador do dispositivo.
- **Transparência:** eventos, saldo e inconsistências devem ser apresentados com linguagem clara.
- **Contexto antes da ação:** ações administrativas exibem colaborador, período e impacto antes da confirmação.
- **Segurança sem atrito:** permissões ocultam ações indevidas, mas erros de autorização continuam compreensíveis.
- **Responsividade:** o MVP é web responsivo; aplicativo nativo fica fora do escopo.

## 3. Arquitetura de informação

```text
Aplicação
├── Início / Dashboard
├── Minha jornada
│   ├── Registrar ponto
│   ├── Histórico
│   └── Banco de horas
├── Equipe (gestor)
├── Colaboradores (RH/admin)
├── Jornadas e configurações (RH/admin)
├── Justificativas e ajustes
├── Relatórios
├── Auditoria (RH/admin)
└── Administração (admin)
```

## 4. Telas mínimas do MVP

| Tela | Usuários | Conteúdo e ação principal |
| --- | --- | --- |
| Login | Todos | Credenciais, erro, recuperação conforme política definida |
| Início | Todos | Resumo do dia e atalhos conforme papel |
| Registrar ponto | Colaborador | Próxima ação esperada, confirmação, hora e estado |
| Minha jornada | Colaborador | Linha do tempo, resumo, saldo e justificativas |
| Jornada da equipe | Gestor/RH | Filtros, inconsistências, detalhes e aprovação |
| Colaboradores | RH/Admin | Lista, busca, status e manutenção cadastral |
| Configurar jornada | RH/Admin | Horários, tolerâncias, vigência e vínculo |
| Ajustes | Gestor/RH | Pendências, comparação antes/depois e decisão |
| Relatórios | Gestor/RH/Diretoria | Filtros, prévia e exportação |
| Dashboard | Gestor/RH/Diretoria | Horas extras, banco, atrasos e absenteísmo |
| Auditoria | RH/Admin | Filtros e detalhe imutável da operação |

## 5. Estados obrigatórios

Cada tela deve contemplar pelo menos carregando, vazio, erro, sem permissão, sucesso e validação de formulário. Para o registro de ponto, desenhar também:

- pronto para a próxima marcação;
- registro confirmado;
- evento fora de ordem;
- colaborador inativo;
- indisponibilidade temporária;
- reenvio idempotente.

## 6. Componentes recomendados

- botão primário para a ação única da tela;
- card de resumo diário;
- linha do tempo de eventos;
- tabela com filtros persistentes;
- badge de status com texto e cor;
- modal ou drawer para ajuste e aprovação;
- componente de período;
- toast de confirmação sem substituir mensagem persistente de erro;
- skeleton para carregamento e empty state orientado à ação.

## 7. Responsividade e acessibilidade

- Projetar primeiro o fluxo de registro em telas estreitas e depois expandir para desktop.
- Usar foco visível, ordem de tabulação lógica e controles acionáveis por teclado.
- Não comunicar estado somente por cor; sempre usar texto ou ícone com rótulo.
- Garantir contraste suficiente, labels associados aos campos e mensagens próximas ao erro.
- Manter alvos de toque confortáveis em mobile web.
- Evitar tabelas ilegíveis: em telas estreitas, permitir visualização em cards ou rolagem controlada.

## 8. Tokens de referência

Os valores finais devem ser definidos no Figma, mas o sistema deve centralizar:

- cores de marca, sucesso, aviso, erro e informação;
- escala de espaçamento;
- tipografia e hierarquia de títulos;
- raios, sombras e densidade de tabela;
- estados de foco, hover, disabled e loading.

## 9. Handoff

Antes da implementação, o arquivo Figma deve conter:

1. fluxos por persona;
2. componentes com variantes e estados;
3. medidas e breakpoints;
4. conteúdo de erro, vazio e confirmação;
5. regras de acesso visíveis por papel;
6. especificação de exportação e tabelas;
7. checklist de acessibilidade;
8. link e versão registrados neste documento.
