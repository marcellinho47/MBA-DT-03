 ▐▛███▛█   Claude Code v2.1.319
▝▜██████▀  Opus 5.5 · Claude Pro
 ▝▝   ▝▝   C:\Dev\Projects\MBA-DT-03\ecommerce-api-legacy


❯ /refactor-arch ../reports/audit-project-2.md                                  

  Ran 5 shell commands (ctrl+o to expand)

● Phase 1 is done and I'm partway through the Phase 2 audit. Next I'll check
  whether a malformed payload (card sent as a number) crashes the original app,
  so the validation finding is backed by a test.

  Ran 1 shell command (ctrl+o to expand)

● Testing confirmed three bugs: a JSON-number card crashes the process, an
  existing user's email gets enrolled under a wrong password, and deleting a
  nonexistent id returns 200. I'm writing up the report now.

● Write(C:\Dev\Projects\MBA-DT-03\reports\audit-project-2.md)
  ⎿  Wrote 245 lines to
     C:\Dev\Projects\MBA-DT-03\reports\audit-project-2.md
       1 ================================
       2 ARCHITECTURE AUDIT REPORT
       3 ================================
       4 Project: ecommerce-api-legacy
       5 Stack:   JavaScript (Node.js v26.13.0) + Express 4.22.1 (SQLite 
         in-memory / SQL cru via sqlite3 5.1.7, API de callbacks)
       6 Files:   3 analyzed | ~180 lines of code (+ package.json, README
         .md, api.http)
       7 Date:    2026-11-06
       8 
     … +237 lines (ctrl+o to expand)

● ================================
  PHASE 1: PROJECT ANALYSIS
  ================================
  Language:      JavaScript (Node.js, runtime v26.13.0; no engines declared)
  Framework:     Express 4.22.1 (package.json "^4.18.2")
  Dependencies:  express, sqlite3 5.1.7
  Database:      SQLite in-memory (':memory:') — raw SQL via sqlite3 driver 
  (callback API), seeded on boot
  Domain:        LMS with checkout (users, courses, enrollments, payments, 
  audit_logs)
  Architecture:  Monolithic, no layer separation — AppManager holds the 
  connection, DDL/seed, routes and all business rules in one class
  Entry point:   src/app.js — npm start (node src/app.js), port 3000
  Source files:  3 files analyzed (~180 lines) + package.json, README.md, 
  api.http
  DB tables:     users, courses, enrollments, payments, audit_logs
  Endpoints:     3 (POST /api/checkout [AppManager.js:28], GET 
  /api/admin/financial-report [AppManager.js:80], DELETE /api/users/:id 
  [AppManager.js:131])
  ================================

  ================================
  ARCHITECTURE AUDIT REPORT
  ================================
  Project: ecommerce-api-legacy
  Stack:   JavaScript (Node.js v26.13.0) + Express 4.22.1 (SQLite in-memory / 
  SQL cru via sqlite3 5.1.7, API de callbacks)
  Files:   3 analyzed | ~180 lines of code (+ package.json, README.md, api.http)
  Date:    2026-11-06

  ## Summary
  CRITICAL: 5 | HIGH: 7 | MEDIUM: 2 | LOW: 5
  Monolito sem separação de camadas: a classe AppManager concentra conexão, DDL,
  seed, rotas HTTP, regras de pagamento, matrícula, relatório e exclusão.
  utils.js mistura configuração com segredos, cache global e uma "criptografia"
  caseira. Os riscos mais graves:
  - segredos de produção no código, e o número do cartão é logado junto com a
    chave do gateway;
  - senhas armazenadas de forma reversível e com colisões;
  - endpoints administrativos e destrutivos sem autenticação;
  - um payload malformado derruba o processo inteiro.

  Findings

  #: F-01
  Sev: CRITICAL
  Anti-pattern: AP-01 Segredos hardcoded
  Location: src/utils.js:1-7
  Essence: dbPass, paymentGatewayKey: "pk_live_1234****", smtpUser; porta e
    ':memory:' também fixos → PB-02
  ────────────────────────────────────────
  #: F-02
  Sev: CRITICAL
  Anti-pattern: AP-03 Senha insegura
  Location: src/utils.js:17-23; AppManager.js:68-69; :18
  Essence: badCrypto só depende do 1º caractere (sem salt, colide); default
    "123456"; seed em texto puro → PB-03
  ────────────────────────────────────────
  #: F-03
  Sev: CRITICAL
  Anti-pattern: AP-04 Dados sensíveis em log
  Location: AppManager.js:45
  Essence: Loga o número completo do cartão e a chave do gateway → PB-04
  ────────────────────────────────────────
  #: F-04
  Sev: CRITICAL
  Anti-pattern: AP-05 God Class
  Location: AppManager.js:4-139; utils.js:1-25
  Essence: Conexão + DDL + seed + rotas + todas as regras numa classe → PB-05
  ────────────────────────────────────────
  #: F-05
  Sev: CRITICAL
  Anti-pattern: AP-06 Endpoint perigoso
  Location: AppManager.js:80-129; :131-137
  Essence: Relatório financeiro (nomes/valores) e DELETE de usuário sem auth →
    PB-14
  ────────────────────────────────────────
  #: F-06
  Sev: HIGH
  Anti-pattern: AP-07 Fat Controller
  Location: AppManager.js:28-78; :46-48; :80-129; :108-115
  Essence: Aprovação de pagamento (startsWith("4")), criação de
    usuário/matrícula/pagamento e cálculo de receita dentro dos handlers → PB-06
  ────────────────────────────────────────
  #: F-07
  Sev: HIGH
  Anti-pattern: AP-07 Efeito anunciado e não executado
  Location: AppManager.js:133-135
  Essence: "Usuário deletado, mas as matrículas e pagamentos ficaram sujos" —
  sem
    cascata; o relatório passa a mostrar 'Unknown' → PB-06 (+PB-11)
  ────────────────────────────────────────
  #: F-08
  Sev: HIGH
  Anti-pattern: AP-08 Estado global
  Location: utils.js:9-15; :25; AppManager.js:59
  Essence: globalCache mutado a cada checkout, nunca lido, cresce sem limite →
    PB-07
  ────────────────────────────────────────
  #: F-09
  Sev: HIGH
  Anti-pattern: AP-09 Auth ausente
  Location: AppManager.js:40; :66-73
  Essence: E-mail existente + senha errada → matrícula criada em nome da vítima
    (verificado, 200) → PB-14
  ────────────────────────────────────────
  #: F-10
  Sev: HIGH
  Anti-pattern: AP-10 Sem transação / callback hell
  Location: AppManager.js:37-78; :50-62; :66-70; :83-128
  Essence: 4 escritas sem transação; usuário criado mesmo com pagamento
  recusado;
    aninhamento de até 6 níveis → PB-11
  ────────────────────────────────────────
  #: F-11
  Sev: HIGH
  Anti-pattern: AP-11 Acoplamento
  Location: AppManager.js:1; :7; :45-46; app.js:8-10
  Essence: new sqlite3.Database no construtor; gateway embutido no código →
  PB-07
  ────────────────────────────────────────
  #: F-12
  Sev: HIGH ↑
  Anti-pattern: AP-14 Validação ausente
  Location: AppManager.js:35; :46; :68; :132
  Essence: card numérico → TypeError em callback → processo cai (verificado).
    Elevado de MEDIUM para HIGH por ser DoS → PB-10
  ────────────────────────────────────────
  #: F-13
  Sev: MEDIUM
  Anti-pattern: AP-12 N+1
  Location: AppManager.js:83; :89-92; :102-106
  Essence: 1 + C + 2E consultas; ordem do JSON não determinística → PB-08
  ────────────────────────────────────────
  #: F-14
  Sev: MEDIUM
  Anti-pattern: AP-13 Erros ignorados
  Location: AppManager.js:38; :57; :92-93; :104; :106; :133-135
  Essence: err ignorado; DELETE responde 200 para id inexistente (verificado);
    sem handler central → PB-09
  ────────────────────────────────────────
  #: F-15
  Sev: LOW
  Anti-pattern: AP-18 Magic values
  Location: AppManager.js:21,37,46,48,68,108; utils.js:6,19,22
  Essence: "4", 'PAID'/'DENIED', active = 1, 3000, 10000 → PB-13
  ────────────────────────────────────────
  #: F-16
  Sev: LOW
  Anti-pattern: AP-19 Nomenclatura
  Location: AppManager.js:4; :29-33; utils.js:17; app.js:13
  Essence: u/e/p/cc, badCrypto, AppManager → PB-13
  ────────────────────────────────────────
  #: F-17
  Sev: LOW
  Anti-pattern: AP-20 console.log
  Location: AppManager.js:45; utils.js:13; app.js:13
  Essence: Sem níveis de log → PB-15
  ────────────────────────────────────────
  #: F-18
  Sev: LOW
  Anti-pattern: AP-21 Código morto
  Location: AppManager.js:2; utils.js:2-3,5,9-10,25
  Essence: totalRevenue, dbUser/dbPass/smtpUser, globalCache sem uso → PB-13
  ────────────────────────────────────────
  #: F-19
  Sev: LOW
  Anti-pattern: AP-22 Não idiomático
  Location: AppManager.js:26; :29-33; :50; :54
  Essence: self = this misturado com this; callbacks em vez de async/await →
    PB-13

  O arquivo salvo traz cada finding completo (Description / Evidence / Impact /
  Recommendation), no formato do template.

  Deprecated APIs

  None detected (checked against Node.js v26.13.0, Express 4.22.1, sqlite3
  5.1.7). node --trace-deprecation --pending-deprecation não emitiu avisos.

  Refactoring Plan Preview

  - src/config/: configuração via variáveis de ambiente + .env.example → F-01
  - src/database/: conexão injetável, wrapper Promise, transações, schema + seed
    com hash → F-02, F-10, F-11, F-19
  - src/models/: acesso a dados por entidade; JOIN no relatório → F-04, F-13
  - src/services/: Checkout (gateway injetável, verificação de senha,
    transação), Report, User (exclusão em cascata) → F-03, F-06, F-07, F-09,
    F-10, F-15
  - src/controllers/ + src/routes/: handlers finos; contrato preservado → F-04,
    F-16
  - src/middlewares/: autorização admin, validação, handler central de erros →
    F-05, F-12, F-14
  - src/utils/password.js (crypto.scrypt) e logger.js; remoção de utils.js e
    AppManager.js → F-02, F-08, F-17, F-18
  - src/app.js continua como composition root (npm start inalterado)

  ================================
  Total: 19 findings
  ================================

  Nenhum SQL Injection (AP-02) foi encontrado: todas as queries já usam
  parâmetros ?. Na Fase 3, F-05 e F-09 exigem mudanças intencionais de contrato:
  401/403 nas rotas admin e 401 para senha errada no checkout de um usuário
  existente. O resto do contrato HTTP fica preservado.

  Phase 2 complete. Report saved to
  C:\Dev\Projects\MBA-DT-03\reports\audit-project-2.md.
  Proceed with refactoring (Phase 3)? [y/n]

✻ Cooked for 2m 54s · done 10:32

※ recap: I'm auditing ecommerce-api-legacy so it can be refactored to MVC; the audit is done, with 19 findings saved to reports/audit-project-2.md. Next step: reply y to start the Phase 3 refactor, or n to stop here. (disable recaps in /config)

❯ y                                                                             

  Read 1 file, ran 1 shell command (ctrl+o to expand)

● Starting Phase 3. Git status was clean at session start; I'll confirm, then
  record the baseline against the original app.

  Ran 2 shell commands (ctrl+o to expand)

● Project directory is clean. Writing the baseline script (outside the project).

  Made 1 scratchpad edit +69, ran 1 shell command (ctrl+o to expand)

● Baseline is recorded and the Node/Express restructuring plan is set, with the
  infrastructure layer (config, database, errors, utils) being implemented next.

  Ran 1 shell command (ctrl+o to expand)

● Write(src\config\index.js)
  ⎿  Wrote 28 lines to src\config\index.js
       1 // Único módulo que lê variáveis de ambiente. Nenhum segredo lit
         eral aqui:
       2 // os defaults servem apenas para desenvolvimento local.
       3 const DEFAULT_PORT = 3000;
       4 const DEFAULT_DB_PATH = ':memory:';
       5 const LOG_LEVELS = ['error', 'warn', 'info', 'debug'];
       6 const DEFAULT_LOG_LEVEL = 'info';
       7 
       8 function readPort(raw) {
       9     if (raw === undefined || raw === '') return DEFAULT_PORT;
     … +19 lines (ctrl+o to expand)

● Write(src\database\connection.js)
  ⎿  Wrote 67 lines to src\database\connection.js
       1 const sqlite3 = require('sqlite3');
       2 
       3 // Envolve o driver de callbacks do sqlite3 em uma API baseada e
         m Promises
       4 // (run/get/all) e oferece transações serializadas sobre a conex
         ão única.
       5 function wrapConnection(raw) {
       6     let transactionQueue = Promise.resolve();
       7 
       8     const db = {
     … +59 lines (ctrl+o to expand)

● Write(src\database\schema.js)
  ⎿  Wrote 15 lines to src\database\schema.js
       1 const SCHEMA = [
       2     'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, n
         ame TEXT, email TEXT, pass TEXT)',
       3     'CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY,
          title TEXT, price REAL, active INTEGER)',
       4     'CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY 
         KEY, user_id INTEGER, course_id INTEGER)',
       5     'CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY
         , enrollment_id INTEGER, amount REAL, status TEXT)',
       6     'CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY K
     … +10 lines (ctrl+o to expand)

● Write(src\database\seed.js)
  ⎿  Wrote 55 lines to src\database\seed.js
       1 const { hashPassword, isPasswordHash } = require('../utils/passw
         ord');
       2 const { PAYMENT_STATUS } = require('../models/payment.model');
       3 const { COURSE_ACTIVE } = require('../models/course.model');
       4 
       5 // Dados de desenvolvimento (mesmos do projeto original). A senh
         a do usuário
       6 // de seed continua sendo "123", mas agora é gravada com hash.
       7 const SEED_USER = { name: 'Leonan', email: 'leonan@fullcycle.com
         .br', password: '123' };
     … +48 lines (ctrl+o to expand)

● Write(src\errors\index.js)
  ⎿  Wrote 38 lines to src\errors\index.js
      1 // Exceções de domínio. O error handler central converte cada uma
         em status HTTP;
      2 // as mensagens são as mesmas que a API original devolvia em text
        o puro.
      3 class AppError extends Error {
      4     constructor(message, status) {
      5         super(message);
      6         this.name = this.constructor.name;
      7         this.status = status;
      8     }
     … +30 lines (ctrl+o to expand)

● Write(src\utils\password.js)
  ⎿  Wrote 29 lines to src\utils\password.js
       1 const crypto = require('crypto');
       2 const { promisify } = require('util');
       3 
       4 const scrypt = promisify(crypto.scrypt);
       5 const SCHEME = 'scrypt';
       6 const SALT_BYTES = 16;
       7 const KEY_LENGTH = 64;
       8 
       9 async function hashPassword(raw) {
      10     const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
     … +19 lines (ctrl+o to expand)

● Write(src\utils\logger.js)
  ⎿  Wrote 21 lines to src\utils\logger.js
       1 // Logger mínimo com níveis (o projeto não tem biblioteca de log
          nas dependências).
       2 // Nunca registre senhas, segredos ou números de cartão completo
         s.
       3 const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };
       4 
       5 function createLogger(level = 'info') {
       6     const threshold = LEVELS[level] ?? LEVELS.info;
       7 
       8     const write = (name, sink) => (message, ...meta) => {
     … +13 lines (ctrl+o to expand)

● Write(src\utils\asyncHandler.js)
  ⎿  Wrote 4 lines to src\utils\asyncHandler.js
      1 // Express 4 não encaminha rejeições de handlers async: envia-as 
        ao error handler central.
      2 module.exports = (handler) => (req, res, next) => {
      3     Promise.resolve(handler(req, res, next)).catch(next);
      4 };

● Infrastructure in place. Now the models and the payment gateway.

● Write(src\models\user.model.js)
  ⎿  Wrote 27 lines to src\models\user.model.js
       1 class UserModel {
       2     constructor(db) {
       3         this.db = db;
       4     }
       5 
       6     findByEmail(email) {
       7         return this.db.get(
       8             'SELECT id, name, email, pass AS passwordHash FROM u
         sers WHERE email = ?',
       9             [email],
     … +18 lines (ctrl+o to expand)

● Write(src\models\course.model.js)  ⎿  Wrote 16 lines to src\models\course.model.js
       1 const COURSE_ACTIVE = 1;
       2 
       3 class CourseModel {
       4     constructor(db) {
       5         this.db = db;
       6     }
       7 
       8     findActiveById(courseId) {
       9         return this.db.get(
      10             'SELECT id, title, price FROM courses WHERE id = ? A
     … +7 lines (ctrl+o to expand)

● Write(src\models\enrollment.model.js)
  ⎿  Wrote 20 lines to src\models\enrollment.model.js
       1 class EnrollmentModel {
       2     constructor(db) {
       3         this.db = db;
       4     }
       5 
       6     async create(userId, courseId) {
       7         const { lastID } = await this.db.run(
       8             'INSERT INTO enrollments (user_id, course_id) VALUES
          (?, ?)',
       9             [userId, courseId],
     … +11 lines (ctrl+o to expand)

● Write(src\models\payment.model.js)
  ⎿  Wrote 25 lines to src\models\payment.model.js
       1 const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DE
         NIED' });
       2 
       3 class PaymentModel {
       4     constructor(db) {
       5         this.db = db;
       6     }
       7 
       8     async create({ enrollmentId, amount, status }) {
       9         const { lastID } = await this.db.run(
     … +16 lines (ctrl+o to expand)

● Write(src\models\auditLog.model.js)
  ⎿  Wrote 14 lines to src\models\auditLog.model.js
       1 class AuditLogModel {
       2     constructor(db) {
       3         this.db = db;
       4     }
       5 
       6     async record(action) {
       7         await this.db.run(
       8             "INSERT INTO audit_logs (action, created_at) VALUES 
         (?, datetime('now'))",
       9             [action],
     … +5 lines (ctrl+o to expand)

● Write(src\models\financialReport.model.js)
  ⎿  Wrote 26 lines to src\models\financialReport.model.js
       1 // Leitura agregada para o relatório financeiro: uma única consu
         lta com JOINs
       2 // (substitui as 1 + C + 2E consultas em loop do código original
         ).
       3 // Cada matrícula tem no máximo um pagamento (garantido pelo Che
         ckoutService).
       4 class FinancialReportModel {
       5     constructor(db) {
       6         this.db = db;
       7     }
     … +19 lines (ctrl+o to expand)

● Write(src\gateways\payment.gateway.js)
  ⎿  Wrote 26 lines to src\gateways\payment.gateway.js
       1 const { PAYMENT_STATUS } = require('../models/payment.model');
       2 
       3 // Regra do gateway simulado herdada do código original: cartões
          iniciados em "4" são aprovados.
       4 const APPROVED_CARD_PREFIX = '4';
       5 const VISIBLE_CARD_DIGITS = 4;
       6 
       7 const maskCard = (cardNumber) => `****${String(cardNumber).slice
         (-VISIBLE_CARD_DIGITS)}`;
       8 
     … +18 lines (ctrl+o to expand)

● Now services, validators, controllers, views, routes and middlewares.

● Write(src\services\checkout.service.js)
  ⎿  Wrote 48 lines to src\services\checkout.service.js
       1 const { hashPassword, verifyPassword } = require('../utils/passw
         ord');
       2 const { PAYMENT_STATUS } = require('../models/payment.model');
       3 const { NotFoundError, UnauthorizedError, PaymentDeniedError } =
          require('../errors');
       4 
       5 class CheckoutService {
       6     constructor({ db, users, courses, enrollments, payments, aud
         itLogs, paymentGateway, logger }) {
       7         this.db = db;
     … +41 lines (ctrl+o to expand)

● Write(src\services\report.service.js)
  ⎿  Wrote 34 lines to src\services\report.service.js
       1 const { PAYMENT_STATUS } = require('../models/payment.model');
       2 
       3 const UNKNOWN_STUDENT = 'Unknown';
       4 
       5 class ReportService {
       6     constructor({ financialReports }) {
       7         this.financialReports = financialReports;
       8     }
       9 
      10     // Receita por curso (somente pagamentos PAID) e lista de al
     … +25 lines (ctrl+o to expand)

● Write(src\services\user.service.js)
  ⎿  Wrote 27 lines to src\services\user.service.js
       1 const { NotFoundError } = require('../errors');
       2 
       3 class UserService {
       4     constructor({ db, users, enrollments, payments, logger }) {
       5         this.db = db;
       6         this.users = users;
       7         this.enrollments = enrollments;
       8         this.payments = payments;
       9         this.logger = logger;
      10     }
     … +17 lines (ctrl+o to expand)

● Write(src\validators\common.validator.js)
  ⎿  Wrote 17 lines to src\validators\common.validator.js
       1 const { ValidationError } = require('../errors');
       2 
       3 const POSITIVE_INTEGER = /^[1-9]\d*$/;
       4 
       5 const isNonEmptyString = (value) => typeof value === 'string' &&
          value.trim() !== '';
       6 
       7 // Aceita inteiro positivo como número JSON ou string numérica (
         "2"), como o original.
       8 function parsePositiveInt(value) {
     … +9 lines (ctrl+o to expand)

● Write(src\validators\checkout.validator.js)
  ⎿  Wrote 26 lines to src\validators\checkout.validator.js
       1 const { ValidationError } = require('../errors');
       2 const { isNonEmptyString, parsePositiveInt } = require('./common
         .validator');
       3 
       4 const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
       5 const CARD_PATTERN = /^\d{1,19}$/;
       6 
       7 // Mantém os nomes de campos do contrato (usr, eml, pwd, c_id, c
         ard) apenas na borda
       8 // e devolve o comando com nomes de domínio. Qualquer entrada in
     … +19 lines (ctrl+o to expand)

● Write(src\views\serializers.js)
  ⎿  Wrote 16 lines to src\views\serializers.js
       1 // Camada de view: define exatamente os campos expostos no contr
         ato HTTP.
       2 const CHECKOUT_SUCCESS_MESSAGE = 'Sucesso';
       3 const USER_DELETED_MESSAGE = 'Usuário deletado, junto com suas m
         atrículas e pagamentos.';
       4 
       5 const serializeCheckout = ({ enrollmentId }) => ({
       6     msg: CHECKOUT_SUCCESS_MESSAGE,
       7     enrollment_id: enrollmentId,
       8 });
     … +8 lines (ctrl+o to expand)

● Write(src\controllers\checkout.controller.js)
  ⎿  Wrote 16 lines to src\controllers\checkout.controller.js
       1 const { validateCheckoutInput } = require('../validators/checkou
         t.validator');
       2 const { serializeCheckout } = require('../views/serializers');
       3 
       4 class CheckoutController {
       5     constructor(checkoutService) {
       6         this.checkoutService = checkoutService;
       7     }
       8 
       9     checkout = async (req, res) => {
     … +7 lines (ctrl+o to expand)

● Write(src\controllers\report.controller.js)
  ⎿  Wrote 14 lines to src\controllers\report.controller.js
       1 const { serializeFinancialReport } = require('../views/serialize
         rs');
       2 
       3 class ReportController {
       4     constructor(reportService) {
       5         this.reportService = reportService;
       6     }
       7 
       8     financialReport = async (req, res) => {
       9         const report = await this.reportService.getFinancialRepo
     … +6 lines (ctrl+o to expand)

● Write(src\controllers\user.controller.js)
  ⎿  Wrote 16 lines to src\controllers\user.controller.js
       1 const { parsePositiveInt } = require('../validators/common.valid
         ator');
       2 const { USER_DELETED_MESSAGE } = require('../views/serializers')
         ;
       3 
       4 class UserController {
       5     constructor(userService) {
       6         this.userService = userService;
       7     }
       8 
     … +8 lines (ctrl+o to expand)

● Write(src\middlewares\auth.js)
  ⎿  Wrote 21 lines to src\middlewares\auth.js
       1 const crypto = require('crypto');
       2 const { ForbiddenError } = require('../errors');
       3 
       4 const ADMIN_TOKEN_HEADER = 'X-Admin-Token';
       5 
       6 const digest = (value) => crypto.createHash('sha256').update(Str
         ing(value)).digest();
       7 
       8 // Guarda das rotas administrativas: compara o header com ADMIN_
         TOKEN em tempo constante.
     … +13 lines (ctrl+o to expand)

● Write(src\middlewares\errorHandler.js)
  ⎿  Wrote 26 lines to src\middlewares\errorHandler.js
       1 const { AppError } = require('../errors');
       2 
       3 const BAD_REQUEST_MESSAGE = 'Bad Request';
       4 const INTERNAL_ERROR_MESSAGE = 'Erro interno do servidor';
       5 
       6 // Error handler central: exceções de domínio → status + mensage
         m em texto puro
       7 // (mesmo formato de corpo de erro da API original). Detalhes in
         ternos só vão para o log.
       8 function errorHandler(logger) {
     … +18 lines (ctrl+o to expand)

● Write(src\routes\index.js)
  ⎿  Wrote 15 lines to src\routes\index.js
       1 const { Router } = require('express');
       2 const asyncHandler = require('../utils/asyncHandler');
       3 
       4 // Camada de view: apenas o mapeamento URL + método → controller
          (+ middlewares).
       5 function buildRouter({ checkoutController, reportController, use
         rController, requireAdmin }) {
       6     const router = Router();
       7 
       8     router.post('/api/checkout', asyncHandler(checkoutController
     … +8 lines (ctrl+o to expand)

● Now the composition root, replacing the old app.js, and removing AppManager.js
  / utils.js.

● Update(src\middlewares\errorHandler.js)
  ⎿  Removed 1 line
       6  // Error handler central: exceções de domínio → status + mensag
          em em texto puro
       7  // (mesmo formato de corpo de erro da API original). Detalhes i
          nternos só vão para o log.
       8  function errorHandler(logger) {
       9 -    // eslint-disable-next-line no-unused-vars                 
       9      return (err, req, res, next) => {
      10          if (res.headersSent) return next(err);
      11  

  Read 1 file (ctrl+o to expand)
● Write(src\app.js)
  ⎿  Added 80 lines, removed 10 lines
       1 +// Composition root: carrega config, abre o banco, monta models
         + → services → controllers,                                     
       2 +// registra rotas e middlewares e sobe o servidor. Sem regra de
         + negócio.                                                      
       3  const express = require('express');
       2 -const AppManager = require('./AppManager');                    
       3 -const { config } = require('./utils');                         
       4 +const config = require('./config');                            
       5 +const { createLogger } = require('./utils/logger');            
       6 +const { openDatabase } = require('./database/connection');     
       7 +const { initSchema } = require('./database/schema');           
       8 +const { seedDatabase, migrateLegacyPasswords } = require('./dat
         +abase/seed');                                                  
       9 +const { UserModel } = require('./models/user.model');          
      10 +const { CourseModel } = require('./models/course.model');      
      11 +const { EnrollmentModel } = require('./models/enrollment.model'
         +);                                                             
      12 +const { PaymentModel } = require('./models/payment.model');    
      13 +const { AuditLogModel } = require('./models/auditLog.model');  
      14 +const { FinancialReportModel } = require('./models/financialRep
         +ort.model');                                                   
      15 +const { SimulatedPaymentGateway } = require('./gateways/payment
         +.gateway');                                                    
      16 +const { CheckoutService } = require('./services/checkout.servic
         +e');                                                           
      17 +const { ReportService } = require('./services/report.service');
      18 +const { UserService } = require('./services/user.service');    
      19 +const { CheckoutController } = require('./controllers/checkout.
         +controller');                                                  
      20 +const { ReportController } = require('./controllers/report.cont
         +roller');                                                      
      21 +const { UserController } = require('./controllers/user.controll
         +er');                                                          
      22 +const { requireAdmin } = require('./middlewares/auth');        
      23 +const { errorHandler } = require('./middlewares/errorHandler');
      24 +const { buildRouter } = require('./routes');                   
      25  
       5 -const app = express();                                         
       6 -app.use(express.json());                                       
      26 +function createApp({ db, config: appConfig, logger }) {        
      27 +    const users = new UserModel(db);                           
      28 +    const courses = new CourseModel(db);                       
      29 +    const enrollments = new EnrollmentModel(db);               
      30 +    const payments = new PaymentModel(db);                     
      31 +    const auditLogs = new AuditLogModel(db);                   
      32 +    const financialReports = new FinancialReportModel(db);     
      33  
       8 -const manager = new AppManager();                              
       9 -manager.initDb();                                              
      10 -manager.setupRoutes(app);                                      
      34 +    const paymentGateway = new SimulatedPaymentGateway({ apiKey
         +: appConfig.paymentGatewayKey, logger });                      
      35  
      12 -app.listen(config.port, () => {                                
      13 -    console.log(`Frankenstein LMS rodando na porta ${config.por
         -t}...`);                                                       
      14 -});                                                            
      36 +    const checkoutService = new CheckoutService({              
      37 +        db, users, courses, enrollments, payments, auditLogs, p
         +aymentGateway, logger,                                         
      38 +    });                                                        
      39 +    const reportService = new ReportService({ financialReports 
         +});                                                            
      40 +    const userService = new UserService({ db, users, enrollment
         +s, payments, logger });                                        
      41 +                                                               
      42 +    const app = express();                                     
      43 +    app.use(express.json());                                   
      44 +    app.use(buildRouter({                                      
      45 +        checkoutController: new CheckoutController(checkoutServ
         +ice),                                                          
      46 +        reportController: new ReportController(reportService), 
      47 +        userController: new UserController(userService),       
      48 +        requireAdmin: requireAdmin(appConfig.adminToken),      
      49 +    }));                                                       
      50 +    app.use(errorHandler(logger));                             
      51 +    return app;                                                
      52 +}                                                              
      53 +                                                               
      54 +async function bootstrap() {                                   
      55 +    const logger = createLogger(config.logLevel);              
      56 +    const db = await openDatabase(config.dbPath);              
      57 +    await initSchema(db);                                      
      58 +    await seedDatabase(db);                                    
      59 +    const migrated = await migrateLegacyPasswords(db);         
      60 +    if (migrated > 0) logger.info(`${migrated} senha(s) legada(
         +s) migrada(s) para scrypt`);                                   
      61 +                                                               
      62 +    if (!config.adminToken) logger.warn('ADMIN_TOKEN não defini
         +do: rotas administrativas responderão 403');                   
      63 +    if (!config.paymentGatewayKey) logger.warn('PAYMENT_GATEWAY
         +_KEY não definida (gateway simulado em uso)');                 
      64 +                                                               
      65 +    const app = createApp({ db, config, logger });             
      66 +    const server = app.listen(config.port, () => {             
      67 +        logger.info(`LMS API rodando na porta ${config.port}`);
      68 +    });                                                        
      69 +                                                               
      70 +    const shutdown = () => {                                   
      71 +        server.close(() => db.close().finally(() => process.exi
         +t(0)));                                                        
      72 +    };                                                         
      73 +    process.once('SIGINT', shutdown);                          
      74 +    process.once('SIGTERM', shutdown);                         
      75 +}                                                              
      76 +                                                               
      77 +if (require.main === module) {                                 
      78 +    bootstrap().catch((err) => {                               
      79 +        console.error('Falha ao iniciar a aplicação', err);    
      80 +        process.exit(1);                                       
      81 +    });                                                        
      82 +}                                                              
      83 +                                                               
      84 +module.exports = { createApp };                                

● Bash(cd /c/Dev/Projects/MBA-DT-03/ecommerce-api-legacy && rm src/AppManager.js
      src/utils.js && for f in $(find src -name '*.js'); do node --check $f ||
      echo "FAIL $f…)
  ⎿  import ok
  ⎿  Deleted src\AppManager.js (+0 -141)
        1 -const sqlite3 = require('sqlite3').verbose();                 
        2 -const { config, logAndCache, badCrypto, totalRevenue } = requi
          -re('./utils');                                                
        3 -                                                              
        4 -class AppManager {                                            
        5 -    constructor() {                                           
        6 -                                                              
        7 -        this.db = new sqlite3.Database(':memory:');           
        8 -    }                                                         
        9 -                                                              
       10 -    initDb() {                                                
       11 -        this.db.serialize(() => {                             
       12 -            this.db.run("CREATE TABLE users (id INTEGER PRIMAR
          -Y KEY, name TEXT, email TEXT, pass TEXT)");                   
       13 -            this.db.run("CREATE TABLE courses (id INTEGER PRIM
          -ARY KEY, title TEXT, price REAL, active INTEGER)");           
       14 -            this.db.run("CREATE TABLE enrollments (id INTEGER 
          -PRIMARY KEY, user_id INTEGER, course_id INTEGER)");           
       15 -            this.db.run("CREATE TABLE payments (id INTEGER PRI
          -MARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)"); 
       16 -            this.db.run("CREATE TABLE audit_logs (id INTEGER P
          -RIMARY KEY, action TEXT, created_at DATETIME)");              
       17 -                                                              
       18 -            this.db.run("INSERT INTO users (name, email, pass)
          - VALUES ('Leonan', 'leonan@fullcycle.com.br', '123')");       
       19 -            this.db.run("INSERT INTO courses (title, price, ac
          -tive) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497
          -.00, 1)");                                                    
       20 -            this.db.run("INSERT INTO enrollments (user_id, cou
          -rse_id) VALUES (1, 1)");                                      
       21 -            this.db.run("INSERT INTO payments (enrollment_id, 
          -amount, status) VALUES (1, 997.00, 'PAID')");                 
       22 -        });                                                   
       23 -    }                                                         
       24 -                                                              
       25 -    setupRoutes(app) {                                        
       26 -        const self = this;                                    
       27 -                                                              
       28 -        app.post('/api/checkout', (req, res) => {             
       29 -            let u = req.body.usr;                             
       30 -            let e = req.body.eml;                             
       31 -            let p = req.body.pwd;                             
       32 -            let cid = req.body.c_id;                          
       33 -            let cc = req.body.card;                           
       34 -                                                              
       35 -            if (!u || !e || !cid || !cc) return res.status(400
          -).send("Bad Request");                                        
       36 -                                                              
       37 -            this.db.get("SELECT * FROM courses WHERE id = ? AN
          -D active = 1", [cid], (err, course) => {                      
       38 -                if (err || !course) return res.status(404).sen
          -d("Curso não encontrado");                                    
       39 -                                                              
       40 -                this.db.get("SELECT id FROM users WHERE email 
          -= ?", [e], (err, user) => {                                   
     … 101 more lines (ctrl+o to expand)
  ⎿  Deleted src\utils.js (+0 -25)
       1 -const config = {                                               
       2 -    dbUser: "admin_master",                                    
       3 -    dbPass: "senha_super_secreta_prod_123",                    
       4 -    paymentGatewayKey: "pk_live_1234567890abcdef",             
       5 -    smtpUser: "no-reply@fullcycle.com.br",                     
       6 -    port: 3000                                                 
       7 -};                                                             
       8 -                                                               
       9 -let globalCache = {};                                          
      10 -let totalRevenue = 0;                                          
      11 -                                                               
      12 -function logAndCache(key, data) {                              
      13 -    console.log(`[LOG] Salvando no cache: ${key}`);            
      14 -    globalCache[key] = data;                                   
      15 -}                                                              
      16 -                                                               
      17 -function badCrypto(pwd) {                                      
      18 -    let hash = "";                                             
      19 -    for(let i = 0; i < 10000; i++) {                           
      20 -        hash += Buffer.from(pwd).toString('base64').substring(0
         -, 2);                                                          
      21 -    }                                                          
      22 -    return hash.substring(0, 10);                              
      23 -}                                                              
      24 -                                                               
      25 -module.exports = { config, logAndCache, badCrypto, globalCache,
         - totalRevenue };                                               

● Everything compiles. Adding .env.example and updating the README and api.http
  for the admin token.

● Write(.env.example)
  ⎿  Wrote 11 lines to .env.example
       1 # Copie para .env (ou exporte no shell) e preencha. Nunca commit
         e valores reais.
       2 PORT=3000
       3 # ":memory:" (padrão) ou caminho de arquivo SQLite, ex.: ./data/
         lms.db
       4 DB_PATH=:memory:
       5 # Token exigido no header X-Admin-Token das rotas administrativa
         s.
       6 # Sem valor, as rotas administrativas respondem 403.
       7 ADMIN_TOKEN=
     … +4 lines (ctrl+o to expand)

● Write(README.md)
  ⎿  Added 35 lines, removed 2 lines
       6  
       7  ```bash
       8  npm install
       9 -npm start                                                      
       9 +ADMIN_TOKEN=troque-me npm start                                
      10  ```
      11  
      12 -A aplicação sobe em `http://localhost:3000`. O banco SQLite é e
         -m memória e já carrega seeds automaticamente no boot.          
      12 +A aplicação sobe em `http://localhost:3000`. O banco SQLite é e
         +m memória por padrão e já carrega seeds automaticamente no boot
         + (usuário `leonan@fullcycle.com.br` / senha `123`).            
      13  
      14 +### Variáveis de ambiente                                      
      15 +                                                               
      16 +Veja `.env.example`. As variáveis são lidas do ambiente do proc
         +esso:                                                          
      17 +                                                               
      18 +| Variável | Padrão | Uso |                                    
      19 +|---|---|---|                                                  
      20 +| `PORT` | `3000` | Porta HTTP |                               
      21 +| `DB_PATH` | `:memory:` | Banco SQLite (memória ou arquivo) | 
      22 +| `ADMIN_TOKEN` | vazio | Token exigido no header `X-Admin-Toke
         +n` das rotas administrativas; vazio = rotas bloqueadas (403) | 
      23 +| `PAYMENT_GATEWAY_KEY` | vazio | Chave do gateway de pagamento
         + (gateway atual é simulado) |                                  
      24 +| `LOG_LEVEL` | `info` | `error`, `warn`, `info` ou `debug` |  
      25 +                                                               
      26 +No PowerShell: `$env:ADMIN_TOKEN="troque-me"; npm start`.      
      27 +                                                               
      28 +## Estrutura                                                   
      29 +                                                               
      30 +```                                                            
      31 +src/                                                           
      32 +├── app.js            # composition root                       
      33 +├── config/           # leitura de variáveis de ambiente       
      34 +├── database/         # conexão promisificada + transações, sch
         +ema, seed                                                      
      35 +├── errors/           # exceções de domínio                    
      36 +├── models/           # acesso a dados por entidade (SQL parame
         +trizado)                                                       
      37 +├── gateways/         # gateway de pagamento (simulado, injetáv
         +el)                                                            
      38 +├── services/         # regras de negócio (checkout, relatório,
         + usuários)                                                     
      39 +├── controllers/      # fluxo HTTP                             
      40 +├── validators/       # validação de entrada                   
      41 +├── views/            # serialização das respostas             
      42 +├── routes/           # mapeamento de rotas                    
      43 +├── middlewares/      # autorização admin e error handler centr
         +al                                                             
      44 +└── utils/            # hash de senha, logger, asyncHandler    
      45 +```                                                            
      46 +                                                               
      47  Exemplos de requisições estão em `api.http`.

● Write(api.http)
  ⎿  Added 5 lines, removed 1 line
      1  @baseUrl = http://localhost:3000
      2 +# Mesmo valor da variável de ambiente ADMIN_TOKEN usada para sub
        +ir a API                                                        
      3 +@adminToken = troque-me                                         
      4  
      5  ### Checkout - sucesso
      6  POST {{baseUrl}}/api/checkout
     ...
      28  
      29  ### Relatório financeiro administrativo
      30  GET {{baseUrl}}/api/admin/financial-report
      31 +X-Admin-Token: {{adminToken}}                                  
      32  
      30 -### Deletar usuário                                            
      33 +### Deletar usuário (remove também matrículas e pagamentos)    
      34  DELETE {{baseUrl}}/api/users/1
      35 +X-Admin-Token: {{adminToken}}                                  

● Now validating: booting with the original command (npm start) and replaying
  the baseline requests.

  Ran 1 shell command (ctrl+o to expand)

● All 11 contract requests match the baseline apart from the planned changes,
  and all 8 security probes pass with no deprecation warnings. Next I'm checking
  the database effects directly: the legacy password migration, orphan rows,
  and that a denied payment writes nothing.

  Ran 1 shell command (ctrl+o to expand)

● Confirmed the migrated legacy password still works, denied payments create no
  user, and deleting a user leaves no orphan rows. Next I'm checking rollback
  when a step fails mid-checkout.

  Ran 1 shell command (ctrl+o to expand)

● Rollback works: no user and no extra enrollment were left behind. Final step:
  re-running the catalog's detection signals on the new code.

  Ran 1 shell command (ctrl+o to expand)

● Remaining hits are false positives, except one: console.error in app.js:79,
  used for boot failures. I'll route it through the logger, then confirm no
  server is left running.

● Bash(node - <<'EOF'
      const fs = require('fs'); const f = 'src/app.js'; let s =
      fs.readFileSync(f, 'utf8');…)
  ⎿      const db = await openDatabase(config.dbPath);
         await initSchema(db);
         await seedDatabase(db);
     … +51 lines (ctrl+o to expand)
  ⎿  Updated src\app.js (+4 -4)
      51      return app;
      52  }
      53  
      54 -async function bootstrap() {                                   
      55 -    const logger = createLogger(config.logLevel);              
      54 +async function bootstrap(logger) {                             
      55      const db = await openDatabase(config.dbPath);
      56      await initSchema(db);
      57      await seedDatabase(db);
     ...
      74  }
      75  
      76  if (require.main === module) {
      78 -    bootstrap().catch((err) => {                               
      79 -        console.error('Falha ao iniciar a aplicação', err);    
      77 +    const logger = createLogger(config.logLevel);              
      78 +    bootstrap(logger).catch((err) => {                         
      79 +        logger.error('Falha ao iniciar a aplicação', err);     
      80          process.exit(1);
      81      });
      82  }

● That app.js edit is mine. The test server on port 3012 is still running: $!
  captured a subshell PID instead of node's. Stopping it by its own PID (10892):

  Ran 1 shell command (ctrl+o to expand)

● ================================
  PHASE 3: REFACTORING COMPLETE
  ================================
  ## New Project Structure
  ecommerce-api-legacy/
  ├── .env.example
  ├── api.http                       (admin requests now send X-Admin-Token)
  ├── README.md                      (env vars + structure)
  ├── package.json                   (unchanged — "start": "node src/app.js")
  └── src/
      ├── app.js                     composition root (createApp + bootstrap)
      ├── config/index.js            only module that reads process.env
      ├── database/
      │   ├── connection.js          promisified run/get/all + serialized 
  transactions
      │   ├── schema.js              DDL (IF NOT EXISTS)
      │   └── seed.js                seed with hash + legacy password migration
      ├── errors/index.js            
  Validation/PaymentDenied/Unauthorized/Forbidden/NotFound
      ├── models/                    user, course, enrollment, payment, 
  auditLog, financialReport
      ├── gateways/payment.gateway.js  SimulatedPaymentGateway (injectable, 
  masks card)
      ├── services/                  checkout, report, user
      ├── controllers/               checkout, report, user
      ├── validators/                checkout.validator.js, common.validator.js
      ├── views/serializers.js       response fields of the contract
      ├── routes/index.js            route mapping only
      ├── middlewares/               auth.js (requireAdmin), errorHandler.js
      └── utils/                     password.js (crypto.scrypt), logger.js, 
  asyncHandler.js
  (removed: src/AppManager.js, src/utils.js)

  ## Changes Applied
  [CRITICAL] F-01 AP-01 Hardcoded secrets → PB-02 — secrets removed (unused 
  dbUser/dbPass/smtpUser dropped); PORT, DB_PATH, ADMIN_TOKEN, 
  PAYMENT_GATEWAY_KEY, LOG_LEVEL come from env (config/index.js, .env.example)
  [CRITICAL] F-02 AP-03 Insecure password storage → PB-03 — badCrypto replaced 
  by scrypt + salt + timingSafeEqual (utils/password.js); no default password; 
  seed stored hashed; plaintext passwords in a persistent DB are re-hashed at 
  boot (database/seed.js)
  [CRITICAL] F-03 AP-04 Card/key in logs → PB-04 — gateway logs only ****1234; 
  the key is never logged (gateways/payment.gateway.js)
  [CRITICAL] F-04 AP-05 God Class → PB-05 — AppManager split into 
  config/database/models/services/controllers/views/routes/middlewares
  [CRITICAL] F-05 AP-06 Unprotected endpoints → PB-14 — requireAdmin 
  (X-Admin-Token, constant-time compare, fail-closed) on the report and DELETE 
  (middlewares/auth.js, routes/index.js)
  [HIGH] F-06 AP-07 Fat controller → PB-06 — rules in 
  CheckoutService/ReportService; approval rule inside the injectable gateway
  [HIGH] F-07 AP-07 Delete without cascade → PB-06+PB-11 — 
  UserService.deleteUser removes payments → enrollments → user in one 
  transaction
  [HIGH] F-08 AP-08 Global state → PB-07 — globalCache/totalRevenue/logAndCache 
  removed (they had no readers)
  [HIGH] F-09 AP-09 Password ignored for existing user → PB-14 — CheckoutService
  checks the password before using an existing account (401)
  [HIGH] F-10 AP-10 No transaction / callback hell → PB-11 — async/await; 
  user+enrollment+payment+audit in one transaction; denied payment writes 
  nothing
  [HIGH] F-11 AP-11 Coupling → PB-07 — db and gateway created in the composition
  root and injected through constructors
  [HIGH] F-12 AP-14 Missing validation (DoS) → PB-10 — validators/*: types, 
  email, numeric card, positive id → 400
  [MEDIUM] F-13 AP-12 N+1 → PB-08 — a single LEFT JOIN query 
  (models/financialReport.model.js), deterministic order by course
  [MEDIUM] F-14 AP-13 Error handling → PB-09 — domain errors + central 
  errorHandler (plain text, as the original); detail only in the log; 404 for a 
  missing user
  [LOW] F-15 AP-18 Magic values → PB-13 — PAYMENT_STATUS, COURSE_ACTIVE, 
  APPROVED_CARD_PREFIX, DEFAULT_PORT etc.
  [LOW] F-16 AP-19 Naming → PB-13 — usr/eml/pwd/c_id/card kept only at the edge;
  domain uses name/email/password/courseId/cardNumber
  [LOW] F-17 AP-20 console.log → PB-15 — leveled logger (LOG_LEVEL)
  [LOW] F-18 AP-21 Dead code → PB-13 — totalRevenue, globalCache, unused configs
  and imports removed
  [LOW] F-19 AP-22 Non-idiomatic → PB-13 — no self=this; const/arrow functions; 
  async/await

  ## Intentional Contract Changes
  - GET /api/admin/financial-report and DELETE /api/users/:id require the 
  `X-Admin-Token` header (= ADMIN_TOKEN); without it, or if wrong → 403 "Acesso 
  negado". Without ADMIN_TOKEN set, both always return 403. (F-05)
  - POST /api/checkout: `pwd` is now required (was a silent default "123456") → 
  400 "Bad Request"; existing email + wrong password → 401 "Credenciais 
  inválidas" (was 200). (F-02, F-09)
  - POST /api/checkout: invalid types/formats (e.g. numeric `card`, invalid 
  email, non-positive `c_id`) → 400 "Bad Request" instead of crashing the 
  process; malformed JSON → plain-text 400 instead of an HTML page with a stack 
  trace. (F-12, F-14)
  - DELETE /api/users/:id: nonexistent id → 404 "Usuário não encontrado"; 
  invalid id → 400 (was a false 200). The success message changed from "…ficaram
  sujos no banco." to "Usuário deletado, junto com suas matrículas e 
  pagamentos." because the delete now really cascades. (F-07, F-14)
  - Financial report now has a deterministic order (by course id); before it 
  depended on callback timing. Keys and shape unchanged.

  ## Validation
    ✓ Application boots without errors (npm start — no stack traces, no 
  deprecation warnings with --trace-deprecation --pending-deprecation)
    ✓ All original endpoints respond (11/11 match baseline: same status and JSON
  keys; the differences are only the documented contract changes)
    ✓ Security fixes verified (admin without token/wrong token → 403; wrong 
  password → 401; new user without pwd → 400; numeric card → 400 and server 
  stays up; card masked in the log, key absent; delete cascades with 0 orphan 
  enrollments/payments; denied payment creates no user; checkout transaction 
  rolls back on mid-flow failure; legacy plaintext password migrated and 
  accepted)
    ✓ Remaining anti-patterns: 0 — remaining grep hits are false positives: seed
  password "123" (seed data, stored as a hash); loops in schema/seed/migration 
  (one-time bootstrap); console.* only inside utils/logger.js; sha256 only to 
  normalize the token before timingSafeEqual

  ## How to run
  npm install
  ADMIN_TOKEN=<token> npm start                     # bash
  $env:ADMIN_TOKEN="<token>"; npm start             # PowerShell
  # optional: PORT=3000  DB_PATH=:memory:|./lms.db  PAYMENT_GATEWAY_KEY=...  
  LOG_LEVEL=info
  # admin routes: header  X-Admin-Token: <token>
  # seed user: leonan@fullcycle.com.br / 123
  ================================

  No new dependencies were added; hashing uses Node's built-in crypto. All test
  servers I started are stopped, and the probe scripts and logs stayed in the
  scratchpad, outside the project. Nothing has been committed, so the changes
  are in the working tree for you to review.

✻ Churned for 6m 18s · done 10:46

※ recap: We audited ecommerce-api-legacy and refactored it to MVC: all 19 findings fixed, all 11 baseline requests match, and the security fixes are verified. Next, review the uncommitted changes and commit them if they look right. (disable recaps in /config)