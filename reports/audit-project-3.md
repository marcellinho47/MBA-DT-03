================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.15.2 + Flask 3.0.0 (SQLite / ORM Flask-SQLAlchemy 3.1.1 + SQLAlchemy 2.1.8)
Files:   15 analyzed | ~1158 lines of code
Date:    2026-11-06

## Summary
CRITICAL: 3 | HIGH: 5 | MEDIUM: 6 | LOW: 5

O projeto é **parcialmente em camadas**: há `models/`, `routes/`, `services/` e `utils/`, mas as rotas concentram consultas, regras de negócio, validação e serialização, enquanto `services/` e `utils/` não são usados por ninguém. Os riscos mais graves são de segurança: senhas com MD5 sem salt, hash da senha devolvido em 4 endpoints (inclusive no login), segredos fixos no código e autenticação falsa — qualquer pessoa pode criar um usuário `admin`.

## Findings

### F-01 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
File: app.py:13; services/notification_service.py:7-10
Description: A `SECRET_KEY` do Flask e as credenciais SMTP (usuário e senha de uma conta Gmail) estão escritas como literais no código-fonte e versionadas no git.
Evidence:
```python
app.config['SECRET_KEY'] = 'super-****'
self.email_user = 'taskmanager@gmail.com'
self.email_password = 'senh****'
```
Impact: Quem tem acesso ao repositório pode forjar sessões/assinaturas do Flask e usar a conta de e-mail; trocar o segredo exige novo deploy de código; o mesmo valor é usado em todos os ambientes.
Recommendation: Criar `config.py` que lê `SECRET_KEY` e `SMTP_*` de variáveis de ambiente (defaults seguros só para desenvolvimento), documentar em `.env.example` — Playbook PB-02

### F-02 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models/user.py:3; models/user.py:27-32; seed.py:19; seed.py:26; seed.py:33; routes/user_routes.py:64; routes/user_routes.py:115
Description: `set_password` grava `hashlib.md5(pwd)` sem salt e `check_password` compara MD5. A política aceita senhas de 4 caracteres e o seed cria usuários com `1234`, `abcd` e `pass`. O fluxo completo (POST /users → `set_password` → POST /login → `check_password`) depende de MD5.
Evidence:
```python
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()
```
Impact: MD5 sem salt é revertido instantaneamente com rainbow tables (ex.: `81dc9bdb52d04dc20036dbd8313ed055` = `1234`); combinado com F-03, qualquer cliente obtém as senhas em texto claro.
Recommendation: Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (já dependência do Flask) e migrar os hashes MD5 legados no próximo login bem-sucedido (ou re-seed) — Playbook PB-03

### F-03 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models/user.py:16-25; routes/user_routes.py:33; routes/user_routes.py:85; routes/user_routes.py:129; routes/user_routes.py:209
Description: `User.to_dict()` inclui o campo `password` (hash MD5) e é usado como resposta em GET /users/<id>, POST /users, PUT /users/<id> e POST /login. Confirmado em execução: o login de `joao@email.com` devolve `"password": "81dc9bdb..."`.
Evidence:
```python
'email': self.email,
'password': self.password,
'role': self.role,
```
Impact: Vazamento do hash de senha de qualquer usuário para qualquer cliente (GET /users/<id> não exige autenticação); com MD5 (F-02), equivale a vazar a senha.
Recommendation: Remover `password` da serialização (view/serializer explícito sem campos sensíveis) — Playbook PB-04

### F-04 [HIGH] God File — rotas misturando camadas e domínios (AP-05)
File: routes/task_routes.py:1-299; routes/report_routes.py:1-223
Description: `task_routes.py` (299 linhas) contém roteamento HTTP, consultas ORM, validação, regras de negócio (atraso, estatísticas) e serialização manual. `report_routes.py` mistura dois domínios distintos: relatórios (12-155) e o CRUD completo de categorias (157-223), além de consultas e agregações.
Evidence:
```python
report_bp = Blueprint('reports', __name__)
@report_bp.route('/categories', methods=['POST'])
def create_category():
```
Impact: Cada mudança em regra de negócio exige mexer em arquivos HTTP; categorias ficam "escondidas" no módulo de relatórios; impossível testar regras sem subir o Flask.
Recommendation: Separar em controllers por domínio (`tasks`, `users`, `categories`, `reports`), services com as regras e repositories com as consultas — Playbook PB-05
Severity note: rebaixado de CRITICAL para HIGH porque os models ORM já estão isolados em `models/` e cada blueprint é limitado a poucos domínios — a separação de camadas é parcial, não inexistente.

### F-05 [HIGH] Regra de negócio no controller/rota (AP-07)
File: routes/task_routes.py:30-39; routes/task_routes.py:71-80; routes/task_routes.py:273-299; routes/user_routes.py:140-142; routes/user_routes.py:171-180; routes/report_routes.py:12-101; routes/report_routes.py:103-155; models/task.py:50-60
Description: A regra "task atrasada" já existe em `Task.is_overdue()` (models/task.py:50-60), mas é reimplementada com `if` aninhados em 5 handlers. Estatísticas, taxa de conclusão, produtividade por usuário e o relatório completo são calculados dentro das rotas. A exclusão em cascata de tasks ao remover um usuário está no handler.
Erratum (Fase 3): a versão inicial deste finding afirmava que remover uma categoria deixava tasks com `category_id` órfão. A linha de base em execução mostrou que isso **não** ocorre — o cascade padrão do relacionamento `Category.tasks` (backref) do SQLAlchemy já anula o `category_id`. A afirmação foi retirada.
Evidence:
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
```
Impact: Regras divergem com facilidade (cada cópia pode evoluir de forma diferente); não há como testar regras isoladamente.
Recommendation: Mover regras para `Task.is_overdue()`/services (`task_service`, `report_service`, `user_service`, `category_service`); rotas só delegam — Playbook PB-06

### F-06 [HIGH] Efeito de negócio anunciado e não executado — notificação de atribuição (AP-07)
File: services/notification_service.py:27-41; routes/task_routes.py:116-132; routes/task_routes.py:186-191
Description: `NotificationService.notify_task_assigned` e `notify_task_overdue` descrevem o efeito "avisar o usuário quando uma task é atribuída a ele", mas o service nunca é importado nem instanciado. POST /tasks e PUT /tasks/<id> atribuem `user_id` sem disparar notificação alguma.
Evidence:
```python
def notify_task_assigned(self, user, task):
    subject = f"Nova task atribuída: {task.title}"
```
Impact: Funcionalidade prevista que silenciosamente não acontece; o código dá a falsa impressão de que usuários são notificados.
Recommendation: Implementar a regra no `task_service` (notificar ao atribuir/reatribuir `user_id`), com o notifier injetado e o envio SMTP desligado por padrão (somente log) até haver configuração — Playbook PB-06 (+ PB-07 para a injeção)

### F-07 [HIGH] Autenticação/autorização ausente ou falsa (AP-09)
File: routes/user_routes.py:207-211; routes/user_routes.py:52; routes/user_routes.py:71-72; routes/user_routes.py:119-122; routes/task_routes.py:85-299; routes/report_routes.py:167-223
Description: O login retorna `'fake-jwt-token-' + str(user.id)` — previsível e nunca verificado. Nenhuma rota exige autenticação. POST /users aceita `role` do corpo, e PUT /users/<id> permite alterar `role` — confirmado em execução: um cliente anônimo criou um usuário `admin` (201).
Evidence:
```python
'token': 'fake-jwt-token-' + str(user.id)
role = data.get('role', 'user')
```
Impact: Escalada de privilégio trivial (qualquer um vira admin) e qualquer cliente pode alterar/excluir usuários, tasks e categorias; o "token" não autentica nada.
Recommendation: Emitir token assinado (ex.: `itsdangerous`, já dependência do Flask), decorator `require_auth`/`require_admin` e exigir admin para atribuir/alterar papéis privilegiados — Playbook PB-14

### F-08 [HIGH] Acoplamento rígido a infraestrutura (AP-11)
File: services/notification_service.py:5-20
Description: `NotificationService` cria a própria configuração SMTP no construtor e instancia `smtplib.SMTP(...)` dentro de `send_email`, sem receber cliente/configuração por injeção.
Evidence:
```python
server = smtplib.SMTP(self.email_host, self.email_port)
server.login(self.email_user, self.email_password)
```
Impact: Impossível testar ou desligar o envio sem rede/SMTP real; troca de provedor exige alterar a classe.
Recommendation: Receber a configuração (de `config.py`) e um "sender" injetável; implementação padrão apenas registra em log quando SMTP não está configurado — Playbook PB-07

### F-09 [MEDIUM] Consultas N+1 (AP-12)
File: routes/task_routes.py:41-57; routes/user_routes.py:22; routes/report_routes.py:53-56; routes/report_routes.py:159-163
Description: GET /tasks faz `User.query.get` e `Category.query.get` para cada task; GET /users acessa `len(u.tasks)` (lazy load) por usuário; o relatório consulta tasks por usuário em loop; GET /categories faz um `count()` por categoria.
Evidence:
```python
for c in categories:
    cat_data['task_count'] = Task.query.filter_by(category_id=c.id).count()
```
Impact: 1 + 2N consultas em GET /tasks; latência cresce linearmente com o volume de dados.
Recommendation: Eager loading (`selectinload`) e agregações com `GROUP BY` nos repositories — Playbook PB-08

### F-10 [MEDIUM] Tratamento de erro genérico/silencioso (AP-13)
File: routes/task_routes.py:62; routes/task_routes.py:137; routes/task_routes.py:151; routes/task_routes.py:204; routes/task_routes.py:221; routes/task_routes.py:236; routes/user_routes.py:87; routes/user_routes.py:130; routes/user_routes.py:149; routes/report_routes.py:186; routes/report_routes.py:207; routes/report_routes.py:221; services/notification_service.py:23; utils/helpers.py:46; utils/helpers.py:49; utils/helpers.py:88
Description: 12 `except:` nus e vários `except Exception` que apenas fazem `print`. GET /tasks embrulha o handler inteiro num `try/except:` que engole qualquer erro (inclusive bugs) e devolve 500 genérico. Não existe handler de erro central.
Evidence:
```python
    except:
        return jsonify({'error': 'Erro interno'}), 500
```
Impact: Bugs ficam invisíveis (sem stack trace em log); `except:` captura até `KeyboardInterrupt`/`SystemExit`; respostas de erro inconsistentes entre endpoints.
Recommendation: Exceções de domínio (`NotFoundError`, `ValidationError`, `ConflictError`) + `errorhandler` central que loga e serializa — Playbook PB-09

### F-11 [MEDIUM] Validação de entrada ausente ou duplicada (AP-14)
File: routes/task_routes.py:92-114; routes/task_routes.py:166-184; routes/task_routes.py:261; routes/task_routes.py:264; routes/user_routes.py:61; routes/user_routes.py:106; routes/user_routes.py:115; routes/report_routes.py:173-180; routes/report_routes.py:196-202; utils/helpers.py:19-23; utils/helpers.py:52-55; utils/helpers.py:57-108
Description: Tipos não são verificados — confirmado em execução, 4 entradas inválidas geram 500 em vez de 400: POST /tasks com `"priority": "x"` (task_routes.py:113), PUT /tasks/1 com `"title": null` (167), GET /tasks/search?priority=abc (261) e PUT /users/2 com `"password": 1234` (115). PUT /categories não checa corpo nulo antes de `'name' in data` (196-197). A validação de task está copiada entre create e update, a de e-mail entre create e update de usuário, e `color` nunca é validada — enquanto `utils/helpers.py` já tem `validate_email`, `is_valid_color` e `process_task_data`, nunca usados.
Evidence:
```python
if priority < 1 or priority > 5:   # TypeError com "x"
tasks = tasks.filter(Task.priority == int(priority))  # ValueError com "abc"
```
Impact: Erros de cliente viram 500; regras de validação divergem entre create/update.
Recommendation: Validators únicos por entidade (tipo, presença e faixa), usados por create e update, levantando `ValidationError` → 400 — Playbook PB-10

### F-12 [MEDIUM] Uso de APIs deprecated (AP-15)
File: models/category.py:11; models/task.py:15-16; models/task.py:52; models/user.py:14; routes/task_routes.py:31; routes/task_routes.py:72; routes/task_routes.py:215; routes/task_routes.py:285; routes/user_routes.py:172; routes/report_routes.py:35; routes/report_routes.py:42; routes/report_routes.py:45; routes/report_routes.py:71; routes/report_routes.py:133; services/notification_service.py:35; utils/helpers.py:38; seed.py:66-74; uso de `Query.get()` e `Model.query` listado na seção Deprecated APIs
Description: `datetime.utcnow()` é deprecated desde Python 3.12 (runtime instalado: 3.15.2) e `Query.get()`/`Model.query` são API legada no SQLAlchemy 2.x (instalado 2.1.8). Confirmado com `python -W default`: `DeprecationWarning` e `LegacyAPIWarning` emitidos.
Evidence:
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)
task = Task.query.get(task_id)
```
Impact: Quebra futura ao atualizar Python/SQLAlchemy; ruído de warnings.
Recommendation: Função `utcnow()` central baseada em `datetime.now(timezone.utc)` (preservando datetimes "naive" em UTC no banco para compatibilidade), `db.session.get(Model, id)` e `db.select(...)` nos repositories — Playbook PB-12

### F-13 [MEDIUM] Configuração insegura de ambiente (AP-16)
File: app.py:11; app.py:15; app.py:34
Description: `app.run(debug=True, host='0.0.0.0')` expõe o debugger interativo do Werkzeug (execução de código) em todas as interfaces; `CORS(app)` libera qualquer origem; a URI do banco é fixa no código.
Evidence:
```python
CORS(app)
app.run(debug=True, host='0.0.0.0', port=5000)
```
Impact: Execução remota de código via debugger se exposto na rede; qualquer site pode chamar a API pelo navegador da vítima.
Recommendation: `DEBUG`, `HOST`, `PORT`, `DATABASE_URL` e `CORS_ORIGINS` vindos de env via `config.py`, com debug desligado por padrão — Playbook PB-02

### F-14 [MEDIUM] Lógica duplicada (AP-17)
File: routes/task_routes.py:17-28; models/task.py:23-36; routes/user_routes.py:15-22; routes/user_routes.py:162-169; routes/task_routes.py:275-279; routes/report_routes.py:19-22; routes/task_routes.py:296; routes/report_routes.py:67; routes/report_routes.py:151; utils/helpers.py:14-17
Description: A serialização de task é reescrita campo a campo em GET /tasks e GET /users/<id>/tasks apesar de `Task.to_dict()`; a de usuário é reescrita em GET /users; a contagem por status aparece em /tasks/stats e /reports/summary; o cálculo de taxa de conclusão aparece 3 vezes, enquanto `calculate_percentage` existe (e é importado em report_routes.py:7 sem uso).
Evidence:
```python
'completion_rate': round((done / total) * 100, 2) if total > 0 else 0
```
Impact: Mudanças no formato ou na regra precisam ser replicadas em vários pontos; alto risco de divergência.
Recommendation: Serializers/views únicos por entidade e funções de estatística no service — Playbook PB-06 / PB-10

### F-15 [LOW] Magic numbers e strings (AP-18)
File: routes/task_routes.py:96; routes/task_routes.py:99; routes/task_routes.py:110; routes/task_routes.py:113; routes/task_routes.py:167-182; models/task.py:39; models/task.py:46; utils/helpers.py:75; routes/user_routes.py:64; routes/user_routes.py:71; routes/user_routes.py:115; routes/user_routes.py:120; routes/report_routes.py:24-28; routes/report_routes.py:129; routes/report_routes.py:180; utils/helpers.py:110-116
Description: Listas de status/papéis, limites de título (3/200), prioridade (1-5), senha mínima (4), "alta prioridade" (`<= 2`) e cor padrão aparecem inline em vários arquivos; as constantes equivalentes em `utils/helpers.py:110-116` existem mas não são usadas.
Evidence:
```python
if status not in ['pending', 'in_progress', 'done', 'cancelled']:
```
Impact: Alterar uma regra (ex.: novo status) exige caçar literais em vários arquivos.
Recommendation: Constantes/enums de domínio em um único módulo usado por models, validators e services — Playbook PB-13

### F-16 [LOW] Nomenclatura ruim (AP-19)
File: routes/report_routes.py:24-28; routes/user_routes.py:14; routes/report_routes.py:160; models/category.py:14; models/user.py:27; models/task.py:45
Description: `p1`…`p5` para contagens por prioridade, `u`, `c`, `t`, `d`, `p`, `pwd` como nomes de variáveis/parâmetros fora de escopos triviais.
Evidence:
```python
p1 = Task.query.filter_by(priority=1).count()
```
Impact: Leitura mais lenta e propensa a erro.
Recommendation: Nomes descritivos (`priority_counts`, `user`, `category`, `password`) — Playbook PB-13

### F-17 [LOW] `print` como mecanismo de log (AP-20)
File: routes/task_routes.py:149; routes/task_routes.py:153; routes/task_routes.py:219; routes/task_routes.py:234; routes/user_routes.py:83; routes/user_routes.py:89; routes/user_routes.py:147; services/notification_service.py:21; services/notification_service.py:24; utils/helpers.py:39-41
Description: Eventos e erros da aplicação são registrados com `print`, sem nível, sem logger e sem stack trace (os prints de `seed.py` são saída de CLI e não entram aqui).
Evidence:
```python
print(f"Erro ao criar task: {str(e)}")
```
Impact: Sem filtragem por nível nem integração com agregadores de log; erros perdem o contexto.
Recommendation: `logging.getLogger(__name__)` com níveis configurados na inicialização — Playbook PB-15

### F-18 [LOW] Código morto e imports/dependências não utilizados (AP-21)
File: app.py:7; routes/task_routes.py:7; routes/user_routes.py:6; routes/report_routes.py:7-8; models/task.py:3; models/task.py:38-48; models/user.py:34-38; utils/helpers.py:1-116; services/notification_service.py:1-48; requirements.txt:4-5
Description: Imports sem uso (`os, sys, json, time, hashlib`…); `Task.validate_status`, `Task.validate_priority`, `Task.is_overdue` e `User.is_admin` nunca chamados; `utils/helpers.py` inteiro não é usado (os dois nomes importados em report_routes.py:7 não são referenciados); `services/notification_service.py` nunca é importado (ver F-06); `marshmallow` e `requests` declarados em requirements.txt sem uso.
Evidence:
```python
import json, os, sys, time
from utils.helpers import format_date, calculate_percentage
```
Impact: Ruído, falsa sensação de que há validação/serviços em uso, dependências instaladas sem necessidade.
Recommendation: Remover o que não é usado; reaproveitar o que tem valor (validators, `is_overdue`) na nova estrutura — Playbook PB-13

### F-19 [LOW] Construções não idiomáticas / verbosas (AP-22)
File: models/task.py:38-43; models/task.py:45-48; models/task.py:50-60; models/user.py:34-38; routes/task_routes.py:141; routes/task_routes.py:210; utils/helpers.py:103; routes/task_routes.py:215
Description: `if cond: return True else: return False`, `if` aninhados em 3 níveis para uma expressão booleana, `type(x) == list` em vez de `isinstance`, e `updated_at` atribuído manualmente apesar do `onupdate` da coluna.
Evidence:
```python
if self.role == 'admin':
    return True
else:
    return False
```
Impact: Código mais longo e frágil do que o necessário.
Recommendation: Expressões booleanas diretas, `isinstance`, confiar no `onupdate` — Playbook PB-13

## Deprecated APIs
| API | Location | Replacement |
|-----|----------|-------------|
| `datetime.utcnow()` (deprecated desde Python 3.12; runtime 3.15.2) | models/category.py:11; models/task.py:15; models/task.py:16; models/task.py:52; models/user.py:14; routes/task_routes.py:31; routes/task_routes.py:72; routes/task_routes.py:215; routes/task_routes.py:285; routes/user_routes.py:172; routes/report_routes.py:35; routes/report_routes.py:42; routes/report_routes.py:45; routes/report_routes.py:71; routes/report_routes.py:133; services/notification_service.py:35; utils/helpers.py:38; seed.py:66; seed.py:67; seed.py:69; seed.py:70; seed.py:74 | `datetime.now(timezone.utc)` |
| `Model.query.get(id)` / `Query.get()` (legado no SQLAlchemy 2.x; instalado 2.1.8) | routes/task_routes.py:42; routes/task_routes.py:51; routes/task_routes.py:67; routes/task_routes.py:117; routes/task_routes.py:122; routes/task_routes.py:158; routes/task_routes.py:188; routes/task_routes.py:195; routes/task_routes.py:227; routes/user_routes.py:29; routes/user_routes.py:94; routes/user_routes.py:136; routes/user_routes.py:155; routes/report_routes.py:105; routes/report_routes.py:192; routes/report_routes.py:213 | `db.session.get(Model, id)` |
| `Model.query.filter/filter_by/all/count/delete` (Query API estilo 1.x, legado) | routes/task_routes.py:14; routes/task_routes.py:247; routes/task_routes.py:275-281; routes/user_routes.py:12; routes/user_routes.py:35; routes/user_routes.py:67; routes/user_routes.py:109; routes/user_routes.py:140; routes/user_routes.py:159; routes/user_routes.py:197; routes/report_routes.py:15-30; routes/report_routes.py:46; routes/report_routes.py:48; routes/report_routes.py:53; routes/report_routes.py:56; routes/report_routes.py:109; routes/report_routes.py:159; routes/report_routes.py:163; seed.py:11-13; seed.py:94-96 | `db.session.execute(db.select(...))` / `db.session.scalars(...)` |

## Refactoring Plan Preview
1. **Config + composition root** — `config.py` (env vars, `.env.example`), `app.py` vira `create_app()` fino mantendo `python app.py`; logging central e `errorhandler` global → F-01, F-13, F-10, F-17.
2. **Models** — só entidades + comportamento de domínio (`is_overdue`, `set_password`/`check_password` com werkzeug + migração de MD5), constantes de domínio → F-02, F-15, F-19, parte de F-05.
3. **Repositories** — consultas com `db.session.get`/`select`, eager loading e agregações → F-09, F-12.
4. **Services** — regras de tasks, usuários, categorias e relatórios; validators únicos; notificação de atribuição com notifier injetável → F-05, F-06, F-08, F-11, F-14.
5. **Views/serializers** — formato de saída único por entidade, sem `password` → F-03, F-14.
6. **Controllers (blueprints) por domínio** — `tasks`, `users`, `categories`, `reports`, `auth`; só HTTP; token assinado e `require_admin` para papéis privilegiados → F-04, F-07.
7. **Limpeza** — remover `utils/helpers.py`, imports e dependências mortos → F-18.

================================
Total: 19 findings
================================
