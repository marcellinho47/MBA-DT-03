================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v26.13.0) + Express 4.22.1 (SQLite in-memory / SQL cru via sqlite3 5.1.7, API de callbacks)
Files:   3 analyzed | ~180 lines of code (+ package.json, README.md, api.http)
Date:    2026-11-06

## Summary
CRITICAL: 5 | HIGH: 7 | MEDIUM: 2 | LOW: 5

Monolito sem separação de camadas: a classe `AppManager` concentra conexão, DDL, seed, rotas HTTP, regra de pagamento, matrícula, relatório e exclusão, e `utils.js` mistura configuração com segredos, cache global e uma "criptografia" caseira. Os riscos mais graves são segredos de produção no código (incluindo log do número do cartão junto com a chave do gateway), senhas armazenadas de forma reversível/colidente, endpoints administrativos e destrutivos sem autenticação, e um payload malformado que derruba o processo inteiro.

## Findings

### F-01 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
File: src/utils.js:1-7
Description: O objeto `config` contém usuário/senha de banco, chave **live** do gateway de pagamento e usuário SMTP como literais. A porta (`utils.js:6`) e o caminho do banco (`src/AppManager.js:7`, `':memory:'`) também são fixos no código, sem leitura de variáveis de ambiente.
Evidence:
```js
dbPass: "senha_super****",
paymentGatewayKey: "pk_live_1234****",
smtpUser: "no-reply@fullcycle.com.br",
```
Impact: Qualquer pessoa com acesso ao repositório obtém credenciais de produção (gateway de pagamento real); rotação de segredo exige deploy; impossível ter configurações distintas por ambiente.
Recommendation: Criar módulo de configuração que lê `process.env` (com defaults seguros apenas para desenvolvimento), remover os segredos do código e documentar as variáveis em `.env.example` — Playbook PB-02

### F-02 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: src/utils.js:17-23; src/AppManager.js:68-69; src/AppManager.js:18
Description: `badCrypto` repete 10.000 vezes os 2 primeiros caracteres do Base64 da senha e corta em 10 caracteres — o "hash" depende apenas do primeiro byte (e parte do segundo) da senha, não tem salt e é reversível. Quando `pwd` não é enviado, o usuário é criado com a senha padrão `"123456"`. O usuário de seed é gravado com senha em texto puro (`'123'`).
Evidence:
```js
hash += Buffer.from(pwd).toString('base64').substring(0, 2);
...
let hash = badCrypto(p || "123456");
```
Impact: Colisões massivas (qualquer senha que comece com o mesmo caractere gera o mesmo "hash"), vazamento do banco expõe senhas trivialmente; contas criadas sem senha ficam com senha conhecida.
Recommendation: Usar KDF com salt da biblioteca padrão (`crypto.scrypt` + `crypto.timingSafeEqual`), exigir senha no cadastro e migrar/re-semear o usuário legado com hash — Playbook PB-03

### F-03 [CRITICAL] Exposição de dados sensíveis em logs (AP-04)
File: src/AppManager.js:45
Description: A cada checkout o número completo do cartão e a chave do gateway de pagamento são escritos no stdout.
Evidence:
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
Impact: PAN completo e segredo de produção vão parar em agregadores de log (violação de PCI-DSS; vazamento do segredo por qualquer pessoa com acesso aos logs).
Recommendation: Nunca logar cartão nem chave; quando necessário, registrar apenas os 4 últimos dígitos mascarados, via logger com níveis — Playbook PB-04

### F-04 [CRITICAL] God Class / God File (AP-05)
File: src/AppManager.js:4-139; src/utils.js:1-25
Description: `AppManager` cria a conexão (`:7`), executa DDL e seed (`:10-23`), registra todas as rotas (`:25-138`) e implementa no corpo dos handlers as regras de checkout, pagamento, matrícula, auditoria, relatório financeiro e exclusão de usuário — três domínios (usuários, matrículas/pagamentos, relatórios) e todas as camadas na mesma classe. `utils.js` é um "saco de gatos": configuração, cache global, hashing e contador global.
Evidence:
```js
constructor() { this.db = new sqlite3.Database(':memory:'); }
initDb() { ... CREATE TABLE ... INSERT ... }
setupRoutes(app) { app.post('/api/checkout', ...); app.get('/api/admin/...'); app.delete(...) }
```
Impact: Nenhuma parte pode ser testada ou alterada isoladamente; qualquer mudança arrisca regressão em fluxos não relacionados.
Recommendation: Separar em config, conexão/schema, models (acesso a dados), services (regras), controllers, routes e middlewares — Playbook PB-05

### F-05 [CRITICAL] Endpoint perigoso sem proteção (AP-06)
File: src/AppManager.js:80-129; src/AppManager.js:131-137
Description: `GET /api/admin/financial-report` expõe a receita por curso e o nome de todos os alunos com valores pagos, e `DELETE /api/users/:id` apaga qualquer usuário — ambos sem nenhuma autenticação ou autorização (não existe middleware de auth no projeto).
Evidence:
```js
app.get('/api/admin/financial-report', (req, res) => {
app.delete('/api/users/:id', (req, res) => {
```
Impact: Qualquer cliente anônimo lê dados financeiros e pessoais e remove usuários arbitrariamente.
Recommendation: Proteger rotas administrativas com middleware de autorização (ex.: token administrativo vindo de variável de ambiente, comparado em tempo constante) — Playbook PB-14

### F-06 [HIGH] Regra de negócio no controller/rota (AP-07)
File: src/AppManager.js:28-78; src/AppManager.js:46-48; src/AppManager.js:80-129; src/AppManager.js:108-115
Description: O handler de checkout (50 linhas) decide aprovação de pagamento (`cc.startsWith("4")`, um gateway simulado inline apesar da mensagem "Processando cartão ... na chave ..."), cria usuário, matrícula, pagamento, log de auditoria e cache. O handler do relatório calcula receita e monta a estrutura por curso diretamente no corpo da rota.
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
...
if (payment && payment.status === 'PAID') { courseData.revenue += payment.amount; }
```
Impact: Regras de pagamento e faturamento não podem ser reutilizadas nem testadas sem HTTP; trocar o gateway exige mexer na rota.
Recommendation: Mover as regras para `CheckoutService`/`ReportService` (com um `PaymentGateway` injetável) e deixar o controller apenas traduzir request/response — Playbook PB-06

### F-07 [HIGH] Regra de negócio anunciada e não executada: exclusão de usuário sem cascata (AP-07)
File: src/AppManager.js:133-135
Description: A própria resposta do endpoint admite o efeito ausente: o usuário é removido, mas suas matrículas (`enrollments.user_id`) e pagamentos (`payments.enrollment_id`) permanecem órfãos. Não existe código que limpe esses registros, nem FKs com `ON DELETE CASCADE` (`:12-15`).
Evidence:
```js
this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
    res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
```
Impact: Dados inconsistentes: o relatório financeiro passa a listar alunos `'Unknown'` e continua somando receita de matrículas de usuários inexistentes.
Recommendation: Implementar no `UserService` a exclusão em cascata (pagamentos → matrículas → usuário) dentro de uma transação — Playbook PB-06 (+ PB-11)

### F-08 [HIGH] Estado global mutável (AP-08)
File: src/utils.js:9-15; src/utils.js:10; src/utils.js:25; src/AppManager.js:59
Description: `globalCache` é um objeto de módulo exportado e mutado a cada checkout (`last_checkout_<userId>`), sem limite nem leitura em lugar algum; `totalRevenue` é exportado como variável de módulo "global" (por valor, nunca atualizada).
Evidence:
```js
let globalCache = {};
let totalRevenue = 0;
function logAndCache(key, data) { ...; globalCache[key] = data; }
```
Impact: Crescimento de memória sem limite (uma chave por usuário), estado compartilhado entre requisições e impossível de isolar em testes.
Recommendation: Remover o cache global (não é lido por ninguém) e o contador; se houver necessidade real, injetar um cache com escopo e limite — Playbook PB-07

### F-09 [HIGH] Autenticação ausente no checkout de usuário existente (AP-09)
File: src/AppManager.js:40; src/AppManager.js:66-73
Description: O checkout recebe `pwd`, mas quando o e-mail já existe a senha nunca é verificada — a compra é atribuída ao usuário existente apenas pelo e-mail. Verificado: `eml: leonan@fullcycle.com.br` com `pwd: "wrong"` gera matrícula e pagamento para o usuário 1 (HTTP 200).
Evidence:
```js
} else {
    processPaymentAndEnroll(user.id);
}
```
Impact: Qualquer pessoa que conheça o e-mail de um aluno cria matrículas/pagamentos em nome dele.
Recommendation: Validar a senha (hash com `timingSafeEqual`) antes de usar uma conta existente, retornando 401 em caso de falha — Playbook PB-14

### F-10 [HIGH] Escrita multi-etapa sem transação / callback hell (AP-10)
File: src/AppManager.js:37-78; src/AppManager.js:50-62; src/AppManager.js:66-70; src/AppManager.js:83-128
Description: O checkout grava usuário → matrícula → pagamento → audit log em quatro `db.run` independentes, aninhados em até 6 níveis de callback, sem `BEGIN/COMMIT/ROLLBACK`. O usuário é criado antes da decisão de pagamento, então um pagamento recusado deixa o usuário criado; falha no INSERT de pagamento deixa matrícula sem pagamento; o erro do audit log é ignorado (`:57`). O relatório tem outra pirâmide de 5 níveis com contadores manuais (`coursesPending`, `enrPending`).
Evidence:
```js
this.db.run("INSERT INTO enrollments ...", [userId, cid], function(err) {
    self.db.run("INSERT INTO payments ...", [...], function(err) {
        self.db.run("INSERT INTO audit_logs ...", [...], (err) => {
```
Impact: Estado parcial/inconsistente no banco a cada falha intermediária; código difícil de ler e de evoluir.
Recommendation: Promisificar o acesso ao banco (`async/await`) e envolver o checkout em transação única no service — Playbook PB-11

### F-11 [HIGH] Acoplamento rígido a infraestrutura (AP-11)
File: src/AppManager.js:1; src/AppManager.js:7; src/AppManager.js:45-46; src/app.js:8-10
Description: `AppManager` cria a própria conexão SQLite no construtor e implementa o "gateway de pagamento" inline; `app.js` instancia a classe sem nenhuma injeção.
Evidence:
```js
constructor() {
    this.db = new sqlite3.Database(':memory:');
}
```
Impact: Impossível substituir banco ou gateway em testes; troca de banco/gateway exige reescrever regras de negócio.
Recommendation: Criar a conexão no composition root e injetá-la nos models; injetar o `PaymentGateway` no service de checkout — Playbook PB-07

### F-12 [HIGH] Validação de entrada ausente — payload malformado derruba o processo (AP-14)
File: src/AppManager.js:35; src/AppManager.js:46; src/AppManager.js:68; src/AppManager.js:132
Description: Só é verificada a presença de `usr`, `eml`, `c_id` e `card`; nenhum tipo/formato é validado. Com `card` numérico, `cc.startsWith` lança `TypeError` dentro de um callback do sqlite3 — fora do alcance do Express — e o processo termina. `pwd` é opcional (cai no default `"123456"`), `eml` não tem formato validado e o `:id` do DELETE não é validado. **Severidade elevada de MEDIUM para HIGH**: verificado que uma única requisição (`{"usr":"G","eml":"z@x.com","c_id":1,"card":4111}`) derruba o servidor (DoS).
Evidence:
```js
if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");
...
let status = cc.startsWith("4") ? "PAID" : "DENIED";   // TypeError se card for number
```
Impact: Qualquer cliente anônimo derruba a API; dados inválidos são persistidos.
Recommendation: Validar tipos/formato na borda (middleware/validator do checkout e do id), respondendo 400 — Playbook PB-10

### F-13 [MEDIUM] Consultas N+1 (AP-12)
File: src/AppManager.js:83; src/AppManager.js:89-92; src/AppManager.js:102-106
Description: O relatório executa 1 consulta de cursos + 1 de matrículas por curso + 2 (usuário e pagamento) por matrícula: `1 + C + 2E` consultas. Como as respostas chegam em ordem de conclusão dos callbacks, a ordem dos cursos no JSON é não determinística (observado: "Docker" antes de "Clean Architecture").
Evidence:
```js
courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
        enrollments.forEach(enr => { this.db.get("SELECT name, email FROM users ..."
```
Impact: Custo cresce linearmente com matrículas; resposta instável entre chamadas.
Recommendation: Uma única consulta com `LEFT JOIN` courses/enrollments/users/payments, agregada no service (ordenando por curso) — Playbook PB-08

### F-14 [MEDIUM] Tratamento de erro genérico, silencioso ou ausente (AP-13)
File: src/AppManager.js:38; src/AppManager.js:57; src/AppManager.js:92-93; src/AppManager.js:104; src/AppManager.js:106; src/AppManager.js:133-135
Description: Erros de banco são ignorados nos callbacks do audit log, do relatório e do DELETE; em `:92-93` um erro faria `enrollments.length` lançar `TypeError` (crash). Em `:38` erro de banco e curso inexistente viram o mesmo 404. O DELETE responde 200 mesmo para id inexistente (verificado com `/api/users/999`). Não existe handler central de erros; respostas de erro são texto solto.
Evidence:
```js
this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
    res.send("Usuário deletado, ...");
```
Impact: Falhas silenciosas, respostas enganosas e possibilidade de derrubar o processo.
Recommendation: Propagar erros com `async/await` até um middleware central de erros; distinguir 404 de 500; usar `this.changes` para detectar exclusão inexistente — Playbook PB-09

### F-15 [LOW] Magic numbers e strings (AP-18)
File: src/AppManager.js:46; src/AppManager.js:21; src/AppManager.js:48; src/AppManager.js:108; src/AppManager.js:37; src/AppManager.js:68; src/utils.js:6; src/utils.js:19; src/utils.js:22
Description: Regra de aprovação pelo prefixo `"4"`, status `'PAID'`/`'DENIED'` repetidos, `active = 1`, senha padrão `"123456"`, porta `3000`, `10000`/`10` no "hash".
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
Impact: Regras implícitas e espalhadas; risco de divergência ao alterar um valor.
Recommendation: Constantes nomeadas (`PaymentStatus`, `APPROVED_CARD_PREFIX`) no model/gateway; porta via config — Playbook PB-13

### F-16 [LOW] Nomenclatura ruim (AP-19)
File: src/AppManager.js:29-33; src/AppManager.js:4; src/utils.js:17; src/app.js:13
Description: Variáveis de uma letra/abreviadas (`u`, `e`, `p`, `cid`, `cc`), nome enganoso `badCrypto`, classe genérica `AppManager`, módulo `utils`, mensagem "Frankenstein LMS". (Os nomes de campos do request — `usr`, `eml`, `pwd`, `c_id`, `card` — fazem parte do contrato e devem ser mantidos na borda.)
Evidence:
```js
let u = req.body.usr; let e = req.body.eml; let p = req.body.pwd;
```
Impact: Leitura e manutenção dificultadas.
Recommendation: Mapear o payload para nomes de domínio (`name`, `email`, `password`, `courseId`, `cardNumber`) no controller — Playbook PB-13

### F-17 [LOW] `console.log` como mecanismo de log (AP-20)
File: src/AppManager.js:45; src/utils.js:13; src/app.js:13
Description: Logs sem nível, sem estrutura e sem forma de desligar.
Evidence:
```js
console.log(`[LOG] Salvando no cache: ${key}`);
```
Impact: Sem controle de verbosidade; facilita vazamentos como o de F-03.
Recommendation: Logger mínimo com níveis controlado por `LOG_LEVEL` — Playbook PB-15

### F-18 [LOW] Código morto e imports não utilizados (AP-21)
File: src/AppManager.js:2; src/utils.js:2-3; src/utils.js:5; src/utils.js:9-10; src/utils.js:25
Description: `totalRevenue` é importado em `AppManager` e nunca usado (nem atualizado); `config.dbUser`, `config.dbPass` e `config.smtpUser` não são referenciados em nenhum lugar; `globalCache` é escrito mas nunca lido.
Evidence:
```js
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
```
Impact: Ruído e falsa impressão de funcionalidades (cache, SMTP) que não existem.
Recommendation: Remover símbolos e configurações sem uso — Playbook PB-13

### F-19 [LOW] Construções não idiomáticas (AP-22)
File: src/AppManager.js:26; src/AppManager.js:50; src/AppManager.js:54; src/AppManager.js:29-33
Description: `const self = this` misturado com `this` (necessário só porque `function(err)` é usado para ler `this.lastID`); `let` em variáveis nunca reatribuídas; API de callbacks em vez de Promises/`async-await`.
Evidence:
```js
const self = this;
... function(err) { let enrId = this.lastID; self.db.run(...)
```
Impact: Código confuso quanto ao valor de `this`; propenso a erros.
Recommendation: Wrapper Promise para `run/get/all` e `const`/arrow functions — Playbook PB-13

## Deprecated APIs
None detected (checked against Node.js v26.13.0, Express 4.22.1, sqlite3 5.1.7; `node --trace-deprecation --pending-deprecation` não emitiu avisos; nenhuma ocorrência de `new Buffer`, `url.parse`, `createCipher`, `util.is*`, `fs.exists`, `body-parser`, `req.param`, `app.del`).

## Refactoring Plan Preview
- `src/config/` — configuração via variáveis de ambiente + `.env.example` → F-01
- `src/database/` — conexão injetável com wrapper Promise e transações; schema + seed (com hash) → F-02, F-10, F-11, F-19
- `src/models/` — acesso a dados por entidade (users, courses, enrollments, payments, audit_logs) com JOIN no relatório → F-04, F-13
- `src/services/` — `CheckoutService` (+ `PaymentGateway` injetável, verificação de senha, transação), `ReportService`, `UserService` (exclusão em cascata) → F-03, F-06, F-07, F-09, F-10, F-15
- `src/controllers/` + `src/routes/` — handlers finos preservando caminhos/campos do contrato → F-04, F-16
- `src/middlewares/` — autorização admin, validação, handler central de erros → F-05, F-12, F-14
- `src/utils/` (`password.js` com `crypto.scrypt`, `logger.js`) e remoção de `utils.js`/`AppManager.js` → F-02, F-08, F-17, F-18
- `src/app.js` permanece como composition root (`npm start` inalterado)

================================
Total: 19 findings
================================
