# Refatoração Arquitetural Automatizada com Skills — `refactor-arch`

Entrega do desafio técnico **"Criação de Skills — Refatoração Arquitetural Automatizada"** (MBA em Engenharia de Software com IA — Full Cycle).

O objetivo é uma Skill do Claude Code (`/refactor-arch`) que, de forma agnóstica de tecnologia:

1. **Analisa** a codebase (linguagem, framework, banco, arquitetura atual);
2. **Audita** contra um catálogo de anti-patterns, gerando um relatório com severidade, arquivo e linha — e **pausa pedindo confirmação**;
3. **Refatora** para o padrão MVC e **valida** que a aplicação continua funcionando.

A skill é aplicada em três projetos legados:

| # | Projeto | Stack | Domínio |
|---|---------|-------|---------|
| 1 | [`code-smells-project/`](code-smells-project/) | Python 3 + Flask 3.1 + sqlite3 (SQL cru) | API de E-commerce (produtos, usuários, pedidos) |
| 2 | [`ecommerce-api-legacy/`](ecommerce-api-legacy/) | Node.js + Express 4 + sqlite3 (in-memory) | LMS com fluxo de checkout (cursos, matrículas, pagamentos) |
| 3 | [`task-manager-api/`](task-manager-api/) | Python 3 + Flask 3.0 + Flask-SQLAlchemy | Task Manager (tasks, usuários, categorias, relatórios) |

---

## A) Análise Manual

Antes de escrever a skill, os três projetos foram lidos integralmente e executados localmente (Python 3.15, Node.js 26) para estabelecer uma linha de base: todos sobem e os endpoints originais respondem `200`. Vários achados abaixo foram **confirmados na prática**, não apenas por leitura.

Escala de severidade utilizada (definida no enunciado):

- **CRITICAL** — falha grave de segurança ou arquitetura (credenciais hardcoded, SQL Injection, God Class).
- **HIGH** — forte violação de MVC/SOLID (regra de negócio no lugar errado, acoplamento, estado global mutável).
- **MEDIUM** — padronização, duplicação, performance moderada (N+1, validação ausente, tratamento de erro inadequado).
- **LOW** — legibilidade, nomenclatura, magic numbers, código morto.

### Projeto 1 — `code-smells-project` (Python/Flask)

Arquitetura atual: monolito em 4 arquivos (`app.py`, `controllers.py`, `models.py`, `database.py`). Apesar dos nomes, não há separação real de camadas: `models.py` mistura acesso a dados, regras de negócio e formatação; `app.py` contém rotas administrativas com SQL direto.

| # | Severidade | Local | Problema | Por que é relevante |
|---|-----------|-------|----------|---------------------|
| 1.1 | **CRITICAL** | `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-166, 174, 188, 192, 279-281, 289-297` | **SQL Injection** — praticamente todas as queries são montadas por concatenação de strings com entrada do usuário. | Permite ler, alterar ou apagar qualquer dado. **Confirmado:** `POST /login` com `email` e `senha` = `x' OR '1'='1` autentica como **Admin** sem conhecer a senha. |
| 1.2 | **CRITICAL** | `app.py:59-78`, `app.py:47-57` | `POST /admin/query` executa **SQL arbitrário** vindo do body; `POST /admin/reset-db` apaga todas as tabelas. Nenhum dos dois exige autenticação. | Qualquer cliente HTTP tem controle total do banco — é um backdoor exposto. |
| 1.3 | **CRITICAL** | `app.py:7-8, 88`; `controllers.py:285-289` | `SECRET_KEY` hardcoded e `DEBUG=True` fixo; o endpoint público `/health` **devolve a secret key**, o caminho do banco e a flag de debug. | Segredo versionado e vazado em resposta HTTP; debug em produção expõe o console interativo do Werkzeug. |
| 1.4 | **CRITICAL** | `database.py:75-83`; `models.py:83, 99, 110, 126-129` | Senhas armazenadas e comparadas em **texto puro**; `GET /usuarios` e `GET /usuarios/<id>` retornam o campo `senha`. | Exposição direta de credenciais de todos os usuários. |
| 1.5 | **HIGH** | `models.py:133-169, 256-262`; `controllers.py:208-210, 247-250` | Regras de negócio espalhadas: cálculo de total/estoque do pedido dentro da camada de dados, faixas de desconto do relatório no model, "envio" de e-mail/SMS/push no controller. | Viola SRP e MVC; impossível testar regras isoladamente ou trocar a forma de notificação. |
| 1.6 | **HIGH** | `database.py:4-11, 14-84` | Conexão global mutável (`global db_connection`) com `check_same_thread=False`, e a mesma função cria schema e popula dados. | Estado compartilhado entre requisições/threads sem controle; acoplamento de toda a app a um singleton implícito. |
| 1.7 | **MEDIUM** | `models.py:171-233` | **N+1**: para cada pedido, uma query de itens; para cada item, uma query de produto. `get_pedidos_usuario` e `get_todos_pedidos` são cópias quase idênticas. | Custo cresce linearmente com o volume de pedidos; duplicação garante divergência futura. |
| 1.8 | **MEDIUM** | `controllers.py:24-62` vs `64-96` | Validação de produto duplicada entre criar e atualizar — e incompleta no update (não valida categoria nem tamanho do nome). | Mesma regra com dois comportamentos diferentes; é possível gravar dados que o create rejeitaria. |
| 1.9 | **MEDIUM** | `controllers.py:237-255`; `models.py:275-283` | Cancelar pedido não devolve o estoque (apenas imprime "Devolver estoque") e não verifica se o pedido existe. | Inconsistência de dados de negócio e `200 OK` para recursos inexistentes. |
| 1.10 | **MEDIUM** | `controllers.py` (todos os handlers, ex.: `10-12`, `21-22`) | `except Exception` genérico repetido em cada handler, devolvendo `str(e)` ao cliente. | Vaza detalhes internos (inclusive SQL) e duplica tratamento que deveria ser centralizado. |
| 1.11 | **LOW** | `models.py:257-262`; `controllers.py:52, 242` | Magic numbers (`10000`, `5000`, `1000`, `0.1`, `0.05`, `0.02`) e listas de categorias/status literais no meio do código. | Regras de negócio sem nome e sem ponto único de alteração. |
| 1.12 | **LOW** | `controllers.py:8, 57, 161, 179, 182`; `controllers.py:56, 160`; `models.py:2` | `print` usado como log, variável `id` sombreando o builtin, import `sqlite3` não utilizado; mapeamento row→dict repetido (`models.py:12-21, 31-40, 304-313`). | Legibilidade e observabilidade ruins; duplicação mecânica. |

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express)

Arquitetura atual: `app.js` instancia uma única classe `AppManager` que concentra conexão, schema, seed, rotas e regras de negócio; `utils.js` guarda configuração com segredos e estado global.

| # | Severidade | Local | Problema | Por que é relevante |
|---|-----------|-------|----------|---------------------|
| 2.1 | **CRITICAL** | `src/utils.js:1-7` | Credenciais hardcoded: senha do banco (`senha_super_secreta_prod_123`) e chave **live** do gateway de pagamento (`pk_live_...`). | Segredos de produção versionados no repositório. |
| 2.2 | **CRITICAL** | `src/AppManager.js:45` | Loga o **número completo do cartão** junto com a chave do gateway. **Confirmado** na saída do servidor durante o checkout. | Violação grave de PCI-DSS; dados de cartão persistem em logs. |
| 2.3 | **CRITICAL** | `src/utils.js:17-23`; `src/AppManager.js:18, 68` | "Hash" de senha caseiro (`badCrypto`: base64 repetido e truncado em 10 caracteres — reversível e com colisões); senha padrão `"123456"` quando não informada; seed com senha em texto puro. | Credenciais efetivamente desprotegidas; contas criadas sem senha escolhida pelo usuário. |
| 2.4 | **CRITICAL** | `src/AppManager.js:1-141` | **God Class** `AppManager`: conexão, DDL, seed, definição de rotas, validação, pagamento, matrícula, auditoria e relatório no mesmo arquivo/classe. | Nenhuma separação de responsabilidades; qualquer mudança toca tudo; impossível testar partes isoladas. |
| 2.5 | **HIGH** | `src/AppManager.js:80, 131` | `GET /api/admin/financial-report` e `DELETE /api/users/:id` sem autenticação/autorização. | Dados financeiros e operação destrutiva abertos a qualquer cliente. |
| 2.6 | **HIGH** | `src/AppManager.js:37-78` | Checkout em *callback hell* (5 níveis) sem transação: matrícula, pagamento e auditoria são gravados em passos independentes; erro do audit log é ignorado (`:57`). | Falha no meio do fluxo deixa o banco inconsistente (matrícula sem pagamento); lógica de pagamento (`cc.startsWith("4")`, `:46`) presa no handler. |
| 2.7 | **HIGH** | `src/utils.js:9-15, 25` | Estado global mutável (`globalCache`) compartilhado via módulo; `totalRevenue` é exportado como primitivo e nunca atualizado (código morto enganoso). | Efeitos colaterais invisíveis e vazamento de memória (cache sem limite). |
| 2.8 | **MEDIUM** | `src/AppManager.js:83-128` | **N+1** no relatório financeiro: por curso, uma query de matrículas; por matrícula, uma de usuário e uma de pagamento. Erros ignorados (`:92, 104, 106`) — se a query falhar, `enrollments.length` lança exceção e derruba a requisição. | Performance degrada com o volume; tratamento de erro inexistente. |
| 2.9 | **MEDIUM** | `src/AppManager.js:131-136` | `DELETE /api/users/:id` não remove matrículas/pagamentos (órfãos), ignora `err` e responde 200 mesmo se o usuário não existir — a própria mensagem admite "ficaram sujos no banco". | Integridade referencial quebrada. |
| 2.10 | **MEDIUM** | `src/AppManager.js:35` | Validação de entrada mínima: `pwd` opcional, nenhum formato validado (e-mail, cartão, `c_id`); respostas de erro em texto puro, sem padrão. | Dados inválidos chegam ao banco; clientes não conseguem tratar erros de forma consistente. |
| 2.11 | **LOW** | `src/AppManager.js:29-33, 46` | Nomes crípticos (`u`, `e`, `p`, `cid`, `cc`), literal mágico `"4"` como regra de aprovação, `let` onde caberia `const`, mistura de `self`/`this`. | Dificulta leitura e revisão. |
| 2.12 | **LOW** | `src/app.js:12`; `package.json:2-4` | Mensagem "Frankenstein LMS" e metadados de boilerplate; porta vinda de objeto com segredos em vez de variável de ambiente. | Configuração e identidade da aplicação misturadas a segredos. |

> **Observação:** os nomes de campo do body (`usr`, `eml`, `pwd`, `c_id`, `card`) fazem parte do **contrato público** da API (ver `api.http`). A refatoração deve preservá-los na borda (rota/controller) e mapeá-los para nomes legíveis internamente.

### Projeto 3 — `task-manager-api` (Python/Flask + SQLAlchemy)

Arquitetura atual: já existe separação parcial (`models/`, `routes/`, `services/`, `utils/`), mas as **rotas fazem papel de controller e de service**, há lógica duplicada, helpers não utilizados e problemas sérios de segurança.

| # | Severidade | Local | Problema | Por que é relevante |
|---|-----------|-------|----------|---------------------|
| 3.1 | **CRITICAL** | `models/user.py:16-25` (campo em `:21`); usado em `routes/user_routes.py:33, 85, 129, 209` | `User.to_dict()` inclui o **hash da senha**, retornado por `GET/POST/PUT /users` e pelo `/login`. **Confirmado:** `GET /users/1` devolve `"password": "81dc9bdb..."` (MD5 de `"1234"`). | Exposição de credenciais a qualquer cliente. |
| 3.2 | **CRITICAL** | `models/user.py:29, 32` | Senhas com **MD5** sem salt. | MD5 é quebrável por rainbow tables em segundos — o hash acima é revertido trivialmente. |
| 3.3 | **CRITICAL** | `app.py:13`; `services/notification_service.py:7-10` | `SECRET_KEY` e credenciais SMTP (`taskmanager@gmail.com` / `senha123`) hardcoded. | Segredos versionados no repositório. |
| 3.4 | **HIGH** | `routes/user_routes.py:52, 71, 210` | Sem autenticação real: o "token" é `fake-jwt-token-<id>`, nenhuma rota é protegida, e qualquer pessoa pode se cadastrar com `role: "admin"`. | Escalada de privilégio trivial; controle de acesso inexistente. |
| 3.5 | **HIGH** | `routes/task_routes.py:30-39, 71-80, 283-287`; `routes/user_routes.py:171-180`; `routes/report_routes.py:33-43, 132-135` | Regra de negócio "task atrasada" **copiada 6 vezes** nas rotas, embora `Task.is_overdue()` exista (`models/task.py:50-60`); validação de task duplicada nas rotas enquanto `utils/helpers.py:57-108` (`process_task_data`) nunca é usado. | Rotas acumulam papel de controller e service; regras divergem com o tempo. |
| 3.6 | **MEDIUM** | `routes/task_routes.py:41-57`; `routes/report_routes.py:55-56, 162-163`; `routes/user_routes.py:22` | **N+1**: uma query por task para buscar usuário e categoria; uma por usuário/categoria nos relatórios. | Performance degrada linearmente com o volume. |
| 3.7 | **MEDIUM** | `routes/task_routes.py:62, 137, 204, 236`; `routes/user_routes.py:130, 149`; `utils/helpers.py:46, 49, 88` | `except:` sem tipo, engolindo qualquer exceção (inclusive `KeyboardInterrupt`/`SystemExit`). | Erros reais ficam invisíveis; tratamento não centralizado. |
| 3.8 | **MEDIUM** | `routes/task_routes.py:113, 182`; `routes/report_routes.py:196-197` | Entrada malformada gera `500`: `priority` enviada como string causa `TypeError`; `PUT /categories/<id>` sem body causa `TypeError` em `'name' in None`. | Validação ausente vira erro de servidor em vez de `400`. |
| 3.9 | **MEDIUM** (deprecated) | `Query.get()` em `routes/*.py` (ex.: `task_routes.py:42, 51, 67, 117`); `datetime.utcnow()` em `models/*.py`, `routes/*.py`, `seed.py` | **APIs deprecated**: `Query.get()` é legado no SQLAlchemy 2.x (usar `db.session.get(Model, id)`); `datetime.utcnow()` está deprecated desde o Python 3.12 (usar `datetime.now(timezone.utc)`). **Confirmado:** `DeprecationWarning` emitido ao rodar o `seed.py`. | Quebrará em versões futuras das dependências. |
| 3.10 | **MEDIUM** | `routes/report_routes.py:157-223` | CRUD de categorias definido dentro do blueprint de **relatórios**. | Baixa coesão; rota difícil de localizar. |
| 3.11 | **LOW** | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `routes/report_routes.py:8`; `utils/helpers.py:2-7` | Imports não utilizados (`os`, `sys`, `json`, `time`, `math`, `hashlib`...). | Ruído e falsa impressão de dependências. |
| 3.12 | **LOW** | `utils/helpers.py:110-116` vs `routes/*.py` | Constantes (`VALID_STATUSES`, `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`...) definidas mas não usadas; rotas repetem os literais (`3`, `200`, `4`, `1..5`). | Magic numbers e fonte de verdade duplicada. |
| 3.13 | **LOW** | `app.py:34`; `models/task.py:38-48`; `models/user.py:34-38`; `routes/task_routes.py:141` | `debug=True` fixo, `if cond: return True else: return False`, `type(x) == list` em vez de `isinstance`. | Legibilidade e configuração por ambiente. |

### Resumo da análise manual

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---------|:-------:|:----:|:------:|:---:|:-----:|
| 1 — code-smells-project | 4 | 2 | 4 | 2 | 12 |
| 2 — ecommerce-api-legacy | 4 | 3 | 3 | 2 | 12 |
| 3 — task-manager-api | 3 | 2 | 5 | 3 | 13 |

Padrões recorrentes que orientaram o catálogo da skill: **segredos hardcoded**, **SQL Injection / queries concatenadas**, **senhas em texto puro ou hash fraco**, **God Class / ausência de camadas**, **regra de negócio no controller/rota**, **estado global mutável**, **N+1**, **tratamento de erro genérico**, **validação ausente/duplicada**, **APIs deprecated** e **magic numbers**.

---

## B) Construção da Skill

A skill está em `.claude/skills/refactor-arch/` (cópia idêntica nos três projetos):

```
.claude/skills/refactor-arch/
├── SKILL.md                              # o "prompt": papel, 3 fases, regras e formatos de saída
└── references/
    ├── project-analysis.md               # Fase 1 — heurísticas de stack, domínio, endpoints e arquitetura
    ├── anti-patterns-catalog.md          # Fase 2 — 22 anti-patterns com sinais de detecção e severidade
    ├── report-template.md                # Fase 2 — formato obrigatório do relatório
    ├── mvc-guidelines.md                 # Fase 3 — arquitetura alvo, regras por camada, estruturas por stack
    ├── refactoring-playbook.md           # Fase 3 — 15 transformações com código antes/depois
    └── validation-protocol.md            # Fase 3 — linha de base, boot, comparação de endpoints
```

### Decisões de design

- **`SKILL.md` orquestra; as referências trazem o conhecimento.** O `SKILL.md` define o papel (arquiteto revisando um legado), a sequência obrigatória das fases, os formatos exatos de saída e as regras invioláveis. Cada arquivo de referência é lido **apenas na fase em que é necessário** (tabela no topo do `SKILL.md`), o que economiza contexto e evita que o agente misture etapas.
- **Portão de confirmação explícito.** A Fase 2 termina com `Proceed with refactoring (Phase 3)? [y/n]` e a instrução de encerrar o turno. O único arquivo escrito antes da confirmação é o relatório, fora do código da aplicação.
- **Rastreabilidade ponta a ponta.** Cada anti-pattern tem um ID (`AP-xx`) que aponta para uma transformação do playbook (`PB-xx`); cada finding do relatório é numerado (`F-xx`) e cita ambos. Assim, o relatório da Fase 2 vira diretamente o plano da Fase 3, e o resumo final da Fase 3 presta contas finding a finding.
- **Evidência antes de afirmação.** Regras como "confirme lendo o trecho antes de registrar", "nunca estime números de linha", "não invente problemas para atingir números" e "use ✗ com honestidade" reduzem falsos positivos e declarações otimistas.
- **Validação comportamental, não só estrutural.** A Fase 3 sobe a aplicação **original** para registrar uma linha de base (status + formato de cada endpoint) e compara com a aplicação refatorada usando o mesmo conjunto de requisições. Mudanças de contrato só são aceitas se forem intencionais, justificadas (segurança) e listadas.
- **Invocação apenas pelo usuário** (`disable-model-invocation: true`) e caminho do relatório por argumento (`/refactor-arch ../reports/audit-project-N.md`), com um padrão baseado na raiz do repositório git.

### Catálogo de anti-patterns

22 entradas com severidade distribuída (6 CRITICAL, 5 HIGH, 6 MEDIUM, 5 LOW), cada uma com **sinais de detecção** (regex + o que confirmar lendo o código), falsos positivos comuns e a transformação que resolve:

| Severidade | Anti-patterns | Por que estão no catálogo |
|---|---|---|
| CRITICAL | AP-01 Segredos hardcoded · AP-02 SQL Injection · AP-03 Senha insegura · AP-04 Exposição de dados sensíveis · AP-05 God Class · AP-06 Endpoint perigoso sem proteção | Apareceram nos três projetos na análise manual e têm impacto direto (vazamento, execução arbitrária) ou impedem qualquer evolução (God Class). |
| HIGH | AP-07 Regra de negócio no controller · AP-08 Estado global mutável · AP-09 Auth ausente/falsa · AP-10 Escrita multi-etapa sem transação / callback hell · AP-11 Acoplamento a infraestrutura | São as violações de MVC/SOLID da definição de severidade do desafio e explicam por que os projetos não são testáveis. |
| MEDIUM | AP-12 N+1 · AP-13 Erro genérico/silencioso · AP-14 Validação ausente/duplicada · **AP-15 APIs deprecated** · AP-16 Config insegura de ambiente · AP-17 Lógica duplicada | Problemas de qualidade e performance; o AP-15 traz uma tabela de APIs deprecated por ecossistema (Python, SQLAlchemy, Flask, Node, Express, npm) e manda confirmar com `python -W default` / `node --trace-deprecation`. |
| LOW | AP-18 Magic numbers · AP-19 Nomenclatura · AP-20 `print` como log · AP-21 Código morto · AP-22 Construções não idiomáticas | Legibilidade; baratos de corrigir junto com a reestruturação. |

### Como a skill se mantém agnóstica de tecnologia

- **Detecção por tabelas de heurísticas**, não por suposições: manifests de 8 ecossistemas, sinais de framework, banco/forma de acesso, classificação de arquitetura em três níveis (monolítica / parcialmente em camadas / em camadas).
- **Sinais de detecção com variantes por linguagem** (ex.: SQL concatenado com `+`, f-string, `%`, `.format` ou template literal; `hashlib.md5` e `createHash('md5')`).
- **MVC interpretado para APIs** (Model = domínio + dados, View = rotas + serialização, Controller = fluxo HTTP), com estruturas alvo para Flask e Express e uma tabela de equivalência para FastAPI, Django, Spring e Go.
- **Exemplos do playbook em Python e Node**, com a regra "traduza o princípio para a linguagem do projeto".
- **Regras que independem da stack:** manter o comando de execução original, preservar o contrato HTTP, não adicionar dependências quando a biblioteca padrão/framework resolve (`werkzeug.security`, `crypto.scrypt`, `itsdangerous`), tratar dados legados quando o formato de armazenamento muda, e **evoluir** a estrutura de projetos parcialmente organizados em vez de reescrevê-los.

### Desafios encontrados e como foram resolvidos

| Desafio | Solução |
|---|---|
| **Encerrar a aplicação com segurança durante a validação.** O modo debug do Flask cria um processo filho (reloader) que sobrevive ao `kill` do pai, e encerrar processos por nome (`taskkill /IM node.exe`) derrubaria processos do usuário. | O protocolo de validação exige subir um único processo, guardar o PID e encerrar só ele; Flask é iniciado com `--no-reload`. |
| **Segurança × contrato.** Corrigir AP-04/AP-06/AP-09 obriga a mudar respostas (remover `senha`/`password`) e a exigir credenciais em rotas antes públicas. | O resumo da Fase 3 tem a seção obrigatória **Intentional Contract Changes**; todo o resto do contrato (caminhos, métodos, nomes de campos — inclusive `usr`/`eml`/`c_id` do projeto 2) é preservado e verificado contra a linha de base. |
| **A skill deixou passar uma regra de negócio no projeto 1.** Cancelar um pedido imprime "Devolver estoque", mas não devolve (item 1.9 da análise manual). | **Iteração da skill:** o AP-07 ganhou o sinal *"ação anunciada mas não executada"* (logs/comentários/respostas que descrevem um efeito que o código não faz) e o protocolo de validação passou a exigir a conferência dos **efeitos de negócio** lendo o dado depois da operação. Nos projetos 2 e 3, o novo sinal encontrou a exclusão de usuário sem cascata (F-07) e o `NotificationService` nunca chamado (F-06). |
| **Afirmação incorreta no relatório do projeto 3.** A auditoria afirmou que excluir uma categoria deixava tasks órfãs; a linha de base em execução mostrou que o SQLAlchemy já anulava o `category_id`. | A skill retirou a afirmação e registrou uma errata no próprio relatório — o efeito pretendido de exigir validação em execução em vez de confiar só na leitura. |
| **Projeto parcialmente organizado** (task-manager-api). Reestruturar do zero geraria um diff enorme sem ganho. | `mvc-guidelines.md` orienta a evoluir a estrutura existente: `routes/` passou a ser só a camada de view, a lógica foi para `controllers/`, `services/` e repositórios. |

---

## C) Resultados

### Resumo dos relatórios de auditoria

| Projeto | Relatório | CRITICAL | HIGH | MEDIUM | LOW | Total | APIs deprecated |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| 1 — code-smells-project | [`reports/audit-project-1.md`](reports/audit-project-1.md) | 6 | 5 | 5 | 5 | **21** | Nenhuma (verificado contra Python 3.15 / Flask 3.1.1) |
| 2 — ecommerce-api-legacy | [`reports/audit-project-2.md`](reports/audit-project-2.md) | 5 | 7 | 2 | 5 | **19** | Nenhuma (verificado com `node --trace-deprecation`) |
| 3 — task-manager-api | [`reports/audit-project-3.md`](reports/audit-project-3.md) | 3 | 5 | 6 | 5 | **19** | `datetime.utcnow()`, `Query.get()`, Query API 1.x |

Em todos os projetos a skill encontrou os problemas da análise manual e foi além. Exemplos que não estavam na análise manual: falta de transação e corrida de estoque em `criar_pedido` (projeto 1); senha nunca verificada no checkout de e-mail existente e `card` numérico que **derruba o processo** (projeto 2); `NotificationService` nunca chamado e dependências declaradas sem uso (projeto 3).

### Antes / depois da estrutura

**Projeto 1 — code-smells-project** (4 arquivos / ~780 linhas → 35 arquivos / ~1.230 linhas)

```
ANTES                         DEPOIS
app.py        (rotas + SQL)   app.py                    composition root (python app.py)
controllers.py (292 linhas)   src/app.py                create_app(): config, DI, rotas, erros
models.py     (314 linhas)    src/config/settings.py    única leitura de variáveis de ambiente
database.py   (conexão global)src/database.py           conexão por request, transações, seed, migração de senhas
                              src/models/               repositórios com SQL parametrizado + constantes
                              src/services/             produto, usuario, pedido, relatorio, token, notification
                              src/controllers/          fluxo HTTP por domínio
                              src/views/                routes.py (blueprint) + serializers.py
                              src/middlewares/          error_handler.py, auth.py
                              src/utils/                validators.py, security.py
```

**Projeto 2 — ecommerce-api-legacy** (3 arquivos / ~180 linhas → 28 arquivos / ~770 linhas)

```
ANTES                         DEPOIS
src/app.js                    src/app.js                composition root (npm start)
src/AppManager.js (God Class) src/config/               process.env
src/utils.js  (segredos,      src/database/             conexão promisificada + transações serializadas, schema, seed
               cache global,  src/models/               user, course, enrollment, payment, auditLog, financialReport
               badCrypto)     src/gateways/             gateway de pagamento simulado e injetável (mascara o cartão)
                              src/services/             checkout, report, user
                              src/controllers/  src/validators/  src/views/  src/routes/
                              src/middlewares/          auth.js (X-Admin-Token), errorHandler.js
                              src/utils/                password.js (crypto.scrypt), logger.js, asyncHandler.js
```

**Projeto 3 — task-manager-api** (15 arquivos / ~1.160 linhas → 44 arquivos / ~1.540 linhas)

```
ANTES                              DEPOIS
app.py  (config + segredos)        app.py               composition root (create_app + python app.py)
database.py                        config/settings.py   variáveis de ambiente (+ .env.example)
models/   (MD5, to_dict c/ senha)  models/              entidades + repositórios + constantes
routes/   (consultas, regras,      routes/              VIEW: só URL + método → controller
           validação, categorias   controllers/         fluxo HTTP por domínio (tasks, users, categories, reports, auth, health)
           dentro de reports)      services/            regras de negócio, notificação injetável
services/ (nunca usado)            views/serializers.py formatos de resposta sem senha
utils/helpers.py (nunca usado)     middlewares/         error_handler.py, auth.py (token assinado)
                                   utils/               validators, clock (utcnow), stats, errors
```

### Checklist de validação

Preenchido com base na saída das execuções (exports em `reports/export-audit-project-*.md`) e em uma **validação independente** feita depois de cada execução (aplicação iniciada com o comando original e endpoints testados novamente).

| Item | P1 | P2 | P3 |
|---|:-:|:-:|:-:|
| **Fase 1 — Análise** | | | |
| Linguagem detectada corretamente | ✅ Python 3.15 | ✅ JavaScript / Node 26 | ✅ Python 3.15 |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.22.1 | ✅ Flask 3.0.0 + Flask-SQLAlchemy |
| Domínio descrito corretamente | ✅ E-commerce | ✅ LMS com checkout | ✅ Task Manager |
| Nº de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 15 |
| **Fase 2 — Auditoria** | | | |
| Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding com arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados CRITICAL → LOW | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 21 | ✅ 19 | ✅ 19 |
| Detecção de APIs deprecated | ✅ verificado, nenhuma | ✅ verificado, nenhuma | ✅ 3 APIs |
| Pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3 — Refatoração** | | | |
| Estrutura de diretórios segue MVC | ✅ | ✅ | ✅ |
| Configuração extraída (sem hardcoded) | ✅ | ✅ | ✅ |
| Models abstraem os dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `python app.py` | ✅ `npm start` | ✅ `python app.py` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 33/33 requisições¹ | ✅ 11/11 requisições¹ | ✅ 56/56 requisições¹ |

¹ Comparação com a linha de base feita pela própria skill; as diferenças são apenas as mudanças intencionais de contrato listadas no resumo da Fase 3.

### Validação independente (amostra)

| Projeto | Verificação | Antes | Depois |
|---|---|---|---|
| 1 | `POST /login` com `' OR '1'='1` | 200 — logado como Admin | **401** |
| 1 | `GET /usuarios` expõe `senha` / `GET /health` expõe a secret key | sim / sim | **não / não** |
| 1 | `POST /admin/query` (SQL arbitrário) | executava | **404 (removido)** |
| 2 | `card` numérico no checkout | **derrubava o processo** | 400, servidor de pé |
| 2 | Checkout com e-mail existente e senha errada | 200 | **401** |
| 2 | Log do checkout | cartão completo + chave `pk_live` | `****4444`, sem chave |
| 2 | `DELETE /api/users/1` | matrículas e pagamentos órfãos | remove em cascata, em transação |
| 3 | `GET /users/1` e login | hash MD5 na resposta | **sem `password`** |
| 3 | Cadastro anônimo com `role: admin` | 201 | **403** |
| 3 | `priority: "x"` | 500 | **400** |
| 3 | Login com hash MD5 legado | — | 200 e hash migrado para `scrypt` |

Screenshots das execuções: [`reports/audit-project-1.png`](reports/audit-project-1.png), [`reports/audit-project-2.png`](reports/audit-project-2.png), [`reports/audit-project-3.png`](reports/audit-project-3.png). Logs completos das sessões: [`reports/export-audit-project-1.md`](reports/export-audit-project-1.md), [`-2`](reports/export-audit-project-2.md), [`-3`](reports/export-audit-project-3.md).

### Comportamento da skill em stacks diferentes

- **Python/Flask monolítico (P1):** reestruturação completa para `src/` por camada; SQL cru mantido, porém 100% parametrizado; conexão por requisição via `flask.g`.
- **Node/Express (P2):** a maior mudança foi de paradigma — callbacks aninhados viraram `async/await` com transações serializadas sobre a conexão única do `sqlite3`; os campos crípticos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) foram mantidos na borda e mapeados para nomes de domínio no controller.
- **Python/Flask + ORM, parcialmente organizado (P3):** a skill classificou corretamente a arquitetura como "parcialmente em camadas" e **evoluiu** a estrutura existente; foi o único projeto com APIs deprecated, todas substituídas.
- **Pendências declaradas pela própria skill** (marcadas com ✗ ou justificadas no resumo da Fase 3): rotas de cliente ainda públicas no P1 (`POST /pedidos`, `GET /pedidos/usuario/<id>`), escrita de tasks/categorias sem autenticação e CORS `*` por padrão no P3, e — no P1, executado antes da iteração do catálogo — cancelar pedido ainda não devolve o estoque.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (usado: v2.1.318).
- Python 3.12+ (usado: 3.15) e Node.js 18+ (usado: 26).
- Dependências de cada projeto:

```bash
cd code-smells-project && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Linux/macOS: .venv/bin/pip
cd ../ecommerce-api-legacy && npm install
cd ../task-manager-api && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && .venv/Scripts/python seed.py
```

### Executar a skill

A partir da raiz de cada projeto (a skill já está em `.claude/skills/refactor-arch/` de cada um):

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch ../reports/audit-project-1.md"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch ../reports/audit-project-2.md"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch ../reports/audit-project-3.md"
```

A skill imprime a análise (Fase 1), imprime e salva o relatório (Fase 2) e **para** em `Proceed with refactoring (Phase 3)? [y/n]`. Responda `y` para refatorar e validar (Fase 3). Para reexecutar sobre o código original, faça checkout do commit inicial (`6d1ce62`) em outro diretório e copie a pasta `.claude/skills/refactor-arch/` de qualquer um dos projetos para dentro do projeto alvo.

### Rodar as aplicações refatoradas

Cada projeto tem um `.env.example` com todas as variáveis. O mínimo:

| Projeto | Comando | Variáveis principais | Rotas protegidas |
|---|---|---|---|
| 1 | `python app.py` (porta 5000) | `SECRET_KEY` | Header `Authorization: Bearer <token>` do `POST /login` de um admin (`admin@loja.com` / `admin123`, apenas dev) |
| 2 | `npm start` (porta 3000) | `ADMIN_TOKEN`, `PAYMENT_GATEWAY_KEY` | Header `X-Admin-Token: <ADMIN_TOKEN>` |
| 3 | `python seed.py && python app.py` (porta 5000) | `SECRET_KEY` | Header `Authorization: Bearer <token>` do `POST /login` |

### Validar que a refatoração funcionou

```bash
# Projeto 1 — SQL Injection bloqueado e rota admin com token
curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d "{\"email\":\"x' OR '1'='1\",\"senha\":\"x\"}"                     # → 401
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s localhost:5000/relatorios/vendas -H "Authorization: Bearer $TOKEN"   # → 200

# Projeto 2 — requisições de exemplo (com X-Admin-Token) em ecommerce-api-legacy/api.http
ADMIN_TOKEN=troque-me npm start
curl -s localhost:3000/api/admin/financial-report -H 'X-Admin-Token: troque-me'   # → 200

# Projeto 3 — senha não aparece mais e role admin exige admin
curl -s localhost:5000/users/1                                                    # sem "password"
curl -s -X POST localhost:5000/users -H 'Content-Type: application/json' \
  -d '{"name":"X","email":"x@x.com","password":"abcd1","role":"admin"}'           # → 403
```

Para conferir APIs deprecated no projeto 3: `python -W default app.py` não emite mais `DeprecationWarning`/`LegacyAPIWarning`.
