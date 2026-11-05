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

> _Em construção._

---

## C) Resultados

> _Em construção — preenchido após a execução da skill nos 3 projetos._

---

## D) Como Executar

> _Em construção._
