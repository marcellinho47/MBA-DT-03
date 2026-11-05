# Playbook de Refatoração (Fase 3)

Transformações concretas para cada anti-pattern do catálogo. Cada uma tem **quando aplicar**, **antes/depois** e **cuidados**. Os exemplos usam Python/Flask e Node/Express; o princípio vale para qualquer stack — traduza para a linguagem do projeto.

| ID | Transformação | Resolve |
|---|---|---|
| PB-01 | Queries parametrizadas + repositório | AP-02 |
| PB-02 | Configuração externa (env) em módulo de config | AP-01, AP-16 |
| PB-03 | Hash de senha forte (KDF) + migração de legado | AP-03 |
| PB-04 | Serializer explícito / mascaramento em logs | AP-04 |
| PB-05 | Decompor God Class em camadas MVC | AP-05 |
| PB-06 | Extrair regra de negócio para service/model | AP-07, AP-17 |
| PB-07 | Conexão com escopo + injeção de dependência | AP-08, AP-11 |
| PB-08 | Eliminar N+1 (JOIN / eager loading / IN) | AP-12 |
| PB-09 | Exceções de domínio + error handler central | AP-13 |
| PB-10 | Validação centralizada e tipada | AP-14, AP-17 |
| PB-11 | Callbacks → async/await com transação | AP-10 |
| PB-12 | Substituir APIs deprecated | AP-15 |
| PB-13 | Constantes nomeadas, nomes claros, remoção de código morto | AP-18, AP-19, AP-21, AP-22 |
| PB-14 | Proteger endpoints perigosos / controle de acesso | AP-06, AP-09 |
| PB-15 | Logger estruturado no lugar de print | AP-20 |

---

## PB-01 — Queries parametrizadas + repositório

**Quando:** qualquer SQL montado com `+`, f-string, `%`, `.format` ou template literal contendo valores variáveis.

**Antes (Python):**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```
**Depois:**
```python
# models/usuario_model.py
class UsuarioRepository:
    def __init__(self, db):
        self.db = db

    def find_by_email(self, email):
        return self.db.execute(
            "SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
```
A verificação da senha sai do SQL e vai para o service (ver PB-03).

**Filtros dinâmicos** — monte só os fragmentos fixos; valores sempre como parâmetro:
```python
clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
rows = db.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params).fetchall()
```

**Antes (Node):**
```js
db.all(`SELECT * FROM users WHERE email = '${email}'`, cb);
```
**Depois:**
```js
const user = await db.get('SELECT id, name, email FROM users WHERE email = ?', [email]);
```

**Cuidados:** nomes de tabela/coluna não podem ser parâmetros — se forem dinâmicos, use uma *allowlist*. Placeholders variam por driver (`?`, `%s`, `$1`, `:name`).

---

## PB-02 — Configuração externa em módulo de config

**Quando:** segredos literais, `DEBUG=True` fixo, portas/caminhos de banco espalhados, CORS aberto.

**Antes:**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.run(host="0.0.0.0", port=5000, debug=True)
```
**Depois:**
```python
# src/config/settings.py
import os
import secrets

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)  # efêmera em dev
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
```
```python
# app.py (entry point)
from src.app import create_app
from src.config.settings import Settings

app = create_app()

if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
```

**Node:**
```js
// src/config/index.js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  dbPath: process.env.DB_PATH || ':memory:',
});
```

Crie `.env.example` listando as variáveis **sem valores reais**. Se o projeto já depende de `python-dotenv`/`dotenv`, carregue o `.env` no entry point; não adicione a dependência só para isso.

**Cuidados:** defaults só para desenvolvimento e nunca iguais ao segredo antigo (que deve ser considerado vazado). Se a ausência de um segredo impede uma funcionalidade (ex.: chave do gateway), a funcionalidade deve falhar de forma explícita, não usar um valor inventado.

---

## PB-03 — Hash de senha forte + migração de legado

**Quando:** texto puro, MD5/SHA sem KDF, "hash" caseiro, comparação de senha no SQL.

**Python (sem dependência nova — Werkzeug vem com o Flask):**
```python
# Antes
self.password = hashlib.md5(pwd.encode()).hexdigest()

# Depois
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, raw):
    self.password = generate_password_hash(raw)

def check_password(self, raw):
    return check_password_hash(self.password, raw)
```

**Node (sem dependência nova — `crypto` nativo):**
```js
// Antes
function badCrypto(pwd) { /* base64 repetido */ }

// Depois — src/utils/password.js
const crypto = require('crypto');
const KEY_LEN = 64;

function hashPassword(raw) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(raw, salt, KEY_LEN).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

function verifyPassword(raw, stored) {
  const [scheme, salt, hash] = String(stored).split('$');
  if (scheme !== 'scrypt') return false;
  const candidate = crypto.scryptSync(raw, salt, KEY_LEN);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
module.exports = { hashPassword, verifyPassword };
```

**Login seguro:** busque o usuário pelo identificador (PB-01) e compare com `check_password_hash`/`verifyPassword`; nunca compare senha no `WHERE`.

**Migração de dados legados:** se o banco persistente já contém senhas em texto puro/MD5:
- Seeds: gere os usuários já com hash.
- Banco existente: na inicialização, re-hash de valores que não têm o prefixo do novo formato (texto puro), **ou** no login, aceite o formato antigo uma única vez e regrave com o novo (MD5 → KDF).

**Cuidados:** não exija senha forte de usuários existentes de forma que quebre o seed/fluxo original; não use valor padrão para senha ausente — rejeite com 400.

---

## PB-04 — Serializer explícito / mascaramento em logs

**Quando:** `to_dict()`/`SELECT *` devolvendo senha/hash; segredos ou dados de cartão em respostas ou logs.

**Antes:**
```python
def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email, "password": self.password}
```
**Depois:**
```python
def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}
```
Para SQL cru, selecione colunas explícitas ou use um serializer por entidade (`views/serializers.py`) que define os campos públicos — e reutilize-o em todos os endpoints.

**Logs — antes:**
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**Depois:**
```js
const maskCard = (n) => `**** **** **** ${String(n).slice(-4)}`;
logger.info(`Processando pagamento com cartão ${maskCard(cardNumber)}`);
```

**Health/debug endpoints:** devolva apenas estado (`status`, `database: connected`, contagens). Nunca `secret_key`, `debug`, caminhos internos.

Registre a remoção de campos sensíveis como **mudança intencional de contrato**.

---

## PB-05 — Decompor God Class em camadas MVC

**Quando:** um arquivo/classe concentra conexão, schema, rotas, regras e formatação.

**Antes (Node):**
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + seed */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* validação + SQL + pagamento + auditoria */ });
    app.get('/api/admin/financial-report', (req, res) => { /* SQL em loop + agregação */ });
  }
}
```
**Depois:**
```js
// src/app.js — composition root
const express = require('express');
const config = require('./config');
const { openDatabase } = require('./database/connection');
const { initSchema } = require('./database/schema');
const buildRoutes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');

async function bootstrap() {
  const db = await openDatabase(config.dbPath);
  await initSchema(db);
  const app = express();
  app.use(express.json());
  app.use(buildRoutes({ db, config }));   // monta models → services → controllers
  app.use(errorHandler);
  app.listen(config.port, () => console.log(`LMS API listening on port ${config.port}`));
}
bootstrap();
```
```js
// src/routes/index.js — view: só mapeamento
const { Router } = require('express');
module.exports = function buildRoutes({ db, config }) {
  const userModel = new UserModel(db);
  const checkoutService = new CheckoutService({ db, userModel, /* ... */ config });
  const checkoutController = new CheckoutController(checkoutService);
  const router = Router();
  router.post('/api/checkout', asyncHandler(checkoutController.checkout));
  return router;
};
```

**Passo a passo:**
1. Liste as responsabilidades do arquivo (conexão, schema, seed, cada rota, cada regra).
2. Crie primeiro `config` e `database` (sem mudar comportamento).
3. Extraia models/repositórios com as consultas (já parametrizadas — PB-01).
4. Extraia services com as regras; controllers com o fluxo HTTP; rotas com o mapeamento.
5. Reduza o entry point a composition root. Apague o arquivo antigo quando nada mais o referenciar.

**Python** segue o mesmo roteiro: `models.py` monolítico → `src/models/<entidade>_model.py` (repositórios) + `src/services/` (regras) ; `controllers.py` → `src/controllers/<dominio>_controller.py`; `app.add_url_rule(...)` → `src/views/routes.py` (blueprints).

---

## PB-06 — Extrair regra de negócio para service/model

**Quando:** cálculos, decisões de domínio ou efeitos colaterais dentro de handlers ou de funções de acesso a dados; mesma regra duplicada em vários handlers.

**Antes (regra copiada em várias rotas):**
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
```
**Depois (uma fonte de verdade no model):**
```python
# models/task.py
CLOSED_STATUSES = ("done", "cancelled")

def is_overdue(self, now=None):
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)
```
```python
# controller / serializer
data["overdue"] = task.is_overdue()
```

**Antes (pedido calculado na camada de dados + notificação no controller):**
```python
def criar_pedido(usuario_id, itens):   # models.py
    for item in itens:
        cursor.execute("SELECT * FROM produtos WHERE id = " + str(item["produto_id"]))
        ...
    print("ENVIANDO EMAIL: ...")       # controllers.py
```
**Depois:**
```python
# services/pedido_service.py
class PedidoService:
    def __init__(self, produtos, pedidos, notifier):
        self.produtos, self.pedidos, self.notifier = produtos, pedidos, notifier

    def criar_pedido(self, usuario_id, itens):
        produtos = self.produtos.find_many([i["produto_id"] for i in itens])
        total = 0
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise NotFoundError(f"Produto {item['produto_id']} não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
            total += produto["preco"] * item["quantidade"]
        pedido_id = self.pedidos.create_with_items(usuario_id, itens, produtos, total)  # transação
        self.notifier.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}
```

**Cuidados:** preserve exatamente o resultado observável (valores calculados, mensagens, status). Se a regra original tem um bug de negócio evidente (ex.: cancelar pedido não devolve estoque, apesar de a mensagem dizer que devolve), corrija no service e registre no resumo.

---

## PB-07 — Conexão com escopo + injeção de dependência

**Quando:** `global db_connection`, `check_same_thread=False`, estado/cache mutável no módulo, classes que criam a própria infraestrutura.

**Antes:**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```
**Depois (Flask — conexão por requisição):**
```python
# src/database.py
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())
```

**Node — dependências por construtor:**
```js
// Antes
class AppManager { constructor() { this.db = new sqlite3.Database(':memory:'); } }

// Depois
class CourseModel {
  constructor(db) { this.db = db; }
  findActiveById(id) { return this.db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]); }
}
```

**Cache global:** remova se não tem leitor; se é necessário, encapsule em um objeto injetado com limite de tamanho. Remova exports de estado que nunca é atualizado.

---

## PB-08 — Eliminar N+1

**Quando:** consulta dentro de loop sobre o resultado de outra consulta.

**Antes:**
```python
for row in pedidos:
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()
```
**Depois (uma consulta com JOIN, agrupada em memória):**
```python
rows = db.execute("""
    SELECT p.id AS pedido_id, i.produto_id, i.quantidade, i.preco_unitario,
           COALESCE(pr.nome, 'Desconhecido') AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    WHERE p.usuario_id = ?
    ORDER BY p.id
""", (usuario_id,)).fetchall()
```

**ORM (SQLAlchemy):**
```python
# Antes: User.query.get(t.user_id) dentro do loop
# Depois:
from sqlalchemy.orm import joinedload
tasks = db.session.execute(
    select(Task).options(joinedload(Task.user), joinedload(Task.category))
).scalars().all()
```
**Contagens por grupo:** `SELECT category_id, COUNT(*) FROM tasks GROUP BY category_id` em vez de `count()` por item.

**Cuidados:** mantenha a mesma ordem e o mesmo formato de saída (inclusive itens/listas vazias e valores-padrão como `"Desconhecido"`).

---

## PB-09 — Exceções de domínio + error handler central

**Quando:** `try/except Exception` em cada handler, `except:` vazio, `str(e)` devolvido ao cliente, `err` ignorado em callbacks.

**Antes:**
```python
def buscar_produto(id):
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
```
**Depois (Flask):**
```python
# src/middlewares/error_handler.py
import logging
from flask import jsonify

class AppError(Exception):
    status = 500
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class ValidationError(AppError): status = 400
class NotFoundError(AppError):   status = 404
class ForbiddenError(AppError):  status = 403
class ConflictError(AppError):   status = 409

def register_error_handlers(app, error_key="erro"):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message, "sucesso": False}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logging.getLogger(__name__).exception("Unhandled error")
        return jsonify({error_key: "Erro interno do servidor"}), 500
```
Ajuste `error_key` e campos extras ao formato de erro original da API. Cuidado: o handler genérico de `Exception` também captura `HTTPException` (404/405 do Flask) — trate-as antes (`if isinstance(err, HTTPException): return err`).

**Depois (Express):**
```js
// src/middlewares/errorHandler.js
module.exports = (err, req, res, next) => {
  const status = err.status || 500;
  if (status >= 500) console.error(err);
  res.status(status).json({ error: status >= 500 ? 'Internal server error' : err.message });
};
// src/utils/asyncHandler.js
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
```

**Cuidados:** se a API original respondia erros em texto puro (`res.send("Curso não encontrado")`), mantenha o mesmo tipo de corpo e status nos casos de erro do contrato, ou registre a mudança como intencional.

---

## PB-10 — Validação centralizada e tipada

**Quando:** validação ausente (500 com entrada malformada), duplicada entre create/update, ou helper de validação existente e não usado.

**Antes (duplicado e frágil):**
```python
if priority < 1 or priority > 5:          # TypeError se priority for "alta"
    return jsonify({'error': 'Prioridade deve ser entre 1 e 5'}), 400
```
**Depois:**
```python
# src/utils/validators.py
def parse_priority(value):
    try:
        p = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Prioridade inválida")
    if not MIN_PRIORITY <= p <= MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return p

def validate_produto(dados, parcial=False):
    """Mesma regra para criar e atualizar; `parcial` só relaxa obrigatoriedade."""
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    ...
```
Use a biblioteca de validação **se ela já estiver nas dependências** (ex.: `marshmallow` declarado no `requirements.txt`); caso contrário, funções simples bastam.

**Cuidados:** mantenha as mensagens de erro originais quando elas fazem parte do contrato.

---

## PB-11 — Callbacks → async/await com transação

**Quando:** callbacks aninhados, várias escritas relacionadas sem transação, `err` ignorado.

**Antes:**
```js
db.run("INSERT INTO enrollments ...", [userId, cid], function (err) {
  let enrId = this.lastID;
  self.db.run("INSERT INTO payments ...", [enrId, price, status], function (err) {
    self.db.run("INSERT INTO audit_logs ...", [...], (err) => { res.json(...) });
  });
});
```
**Depois:**
```js
// src/database/connection.js — driver promisificado + transação serializada
function promisify(raw) {
  let queue = Promise.resolve();
  const db = {
    run: (sql, params = []) => new Promise((resolve, reject) =>
      raw.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); })),
    get: (sql, params = []) => new Promise((resolve, reject) =>
      raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)))),
    all: (sql, params = []) => new Promise((resolve, reject) =>
      raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)))),
    // Uma única conexão: serializa transações para que não se intercalem.
    transaction(work) {
      const run = queue.then(async () => {
        await db.run('BEGIN');
        try { const result = await work(db); await db.run('COMMIT'); return result; }
        catch (e) { await db.run('ROLLBACK'); throw e; }
      });
      queue = run.catch(() => {});
      return run;
    },
  };
  return db;
}
```
```js
// src/services/checkout.service.js
async checkout({ name, email, password, courseId, cardNumber }) {
  const course = await this.courses.findActiveById(courseId);
  if (!course) throw new NotFoundError('Curso não encontrado');
  if (!this.paymentGateway.approve(cardNumber)) throw new PaymentDeniedError('Pagamento recusado');
  return this.db.transaction(async (tx) => {
    const userId = await this.users.findOrCreate(tx, { name, email, password });
    const enrollmentId = await this.enrollments.create(tx, userId, courseId);
    await this.payments.create(tx, enrollmentId, course.price, 'PAID');
    await this.audit.log(tx, `Checkout curso ${courseId} por ${userId}`);
    return enrollmentId;
  });
}
```

**Cuidados:** Python com `sqlite3`: use `with conn:` (commit/rollback automáticos) ou `BEGIN`/`commit()`/`rollback()` explícitos. SQLAlchemy: um único `db.session.commit()` no fim do caso de uso, `rollback()` no erro.

---

## PB-12 — Substituir APIs deprecated

**Quando:** qualquer item da tabela do AP-15.

```python
# Antes
from datetime import datetime
created_at = db.Column(db.DateTime, default=datetime.utcnow)
task = Task.query.get(task_id)

# Depois
from datetime import datetime, timezone

def utcnow():
    """UTC 'naive', compatível com colunas DateTime sem timezone já existentes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

created_at = db.Column(db.DateTime, default=utcnow)
task = db.session.get(Task, task_id)
```
```js
// Antes
const buf = new Buffer(str);
const { pathname } = url.parse(req.url);
// Depois
const buf = Buffer.from(str);
const { pathname } = new URL(req.url, `http://${req.headers.host}`);
```
**Cuidados:** ao trocar `utcnow()` por `now(timezone.utc)`, não misture datetimes *aware* e *naive* em comparações com dados já gravados — por isso o helper acima mantém o valor *naive* em UTC. `Query.get` → `db.session.get` retorna `None` igual; para `get_or_404`, use `db.get_or_404(Model, id)`.

---

## PB-13 — Constantes nomeadas, nomes claros, remoção de código morto

**Antes:**
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
elif faturamento > 5000:
    desconto = faturamento * 0.05
```
**Depois:**
```python
# src/models/constants.py (ou no service do domínio)
FAIXAS_DESCONTO = (   # (faturamento mínimo exclusivo, percentual)
    (10_000, 0.10),
    (5_000, 0.05),
    (1_000, 0.02),
)
STATUS_PEDIDO = ("pendente", "aprovado", "enviado", "entregue", "cancelado")

def calcular_desconto(faturamento):
    for minimo, percentual in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * percentual
    return 0
```
**Nomes:** `let u = req.body.usr` → `const { usr: name, eml: email, pwd: password, c_id: courseId, card: cardNumber } = req.body;` (o contrato externo é preservado; o código interno fica legível). Evite sombrear builtins (`id` → `produto_id`).

**Código morto / idioms:**
```python
# Antes
import os, sys, json, time          # não usados
def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
if type(tags) == list: ...
# Depois
def is_admin(self):
    return self.role == "admin"
if isinstance(tags, list): ...
```
Antes de remover um símbolo, confirme que não há referências (busca no projeto todo).

---

## PB-14 — Proteger endpoints perigosos / controle de acesso

**Quando:** endpoints admin/destrutivos sem autenticação; execução de SQL/código arbitrário; usuário que se autoatribui papel privilegiado; token falso.

**Execução arbitrária (ex.: `POST /admin/query` que roda SQL do body):** não há forma segura de manter essa capacidade exposta. Opções, em ordem de preferência:
1. Remover o endpoint (registrar como mudança intencional de contrato).
2. Mantê-lo **desabilitado por padrão** (`ENABLE_ADMIN_SQL=false` → 404/403) **e** protegido por token administrativo — somente se o usuário pedir para preservá-lo.

**Endpoints administrativos legítimos (reset, relatórios, delete):** guard com token vindo da config.

```python
# src/middlewares/auth.py
import hmac
from functools import wraps
from flask import current_app, request

def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        provided = request.headers.get("X-Admin-Token", "")
        if not expected or not hmac.compare_digest(provided, expected):
            raise ForbiddenError("Acesso negado")
        return fn(*args, **kwargs)
    return wrapper
```
```js
// src/middlewares/auth.js
const crypto = require('crypto');
module.exports = (config) => (req, res, next) => {
  const expected = Buffer.from(config.adminToken || '');
  const provided = Buffer.from(req.get('X-Admin-Token') || '');
  const ok = expected.length > 0 && expected.length === provided.length && crypto.timingSafeEqual(expected, provided);
  return ok ? next() : res.status(403).json({ error: 'Forbidden' });
};
```

**Token falso no login:** se o framework já traz assinatura (Flask/`itsdangerous`), emita um token assinado com a `SECRET_KEY` e valide-o no guard; sem biblioteca disponível, não invente criptografia — documente como pendência.

**Autoatribuição de papel:** cadastro público sempre cria com o papel padrão (`user`/`cliente`); alteração de papel só por rota protegida.

**Cuidados:** proteger um endpoint muda o contrato (passa a exigir header). Registre em "Intentional Contract Changes" e documente a variável (`ADMIN_TOKEN`) no `.env.example` e no "How to run". Na validação, teste com e sem o header.

---

## PB-15 — Logger no lugar de print

**Antes:**
```python
print("Produto criado com ID: " + str(id))
print("ERRO: " + str(e))
```
**Depois:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Produto criado com ID %s", produto_id)
logger.exception("Erro ao criar produto")   # dentro do handler de erro central
```
Configure o logging uma vez no composition root (`logging.basicConfig(level=...)` com nível vindo da config). Em Node, um wrapper mínimo (`src/utils/logger.js` com `info/warn/error` sobre `console`) é suficiente se não houver biblioteca de log nas dependências. Nunca logue segredos, senhas ou dados de cartão (PB-04). Notificações simuladas (`print("ENVIANDO EMAIL")`) viram um `NotificationService` com logger — ponto único para a futura integração real.
