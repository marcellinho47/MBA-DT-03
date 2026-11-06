// Composition root: carrega config, abre o banco, monta models → services → controllers,
// registra rotas e middlewares e sobe o servidor. Sem regra de negócio.
const express = require('express');
const config = require('./config');
const { createLogger } = require('./utils/logger');
const { openDatabase } = require('./database/connection');
const { initSchema } = require('./database/schema');
const { seedDatabase, migrateLegacyPasswords } = require('./database/seed');
const { UserModel } = require('./models/user.model');
const { CourseModel } = require('./models/course.model');
const { EnrollmentModel } = require('./models/enrollment.model');
const { PaymentModel } = require('./models/payment.model');
const { AuditLogModel } = require('./models/auditLog.model');
const { FinancialReportModel } = require('./models/financialReport.model');
const { SimulatedPaymentGateway } = require('./gateways/payment.gateway');
const { CheckoutService } = require('./services/checkout.service');
const { ReportService } = require('./services/report.service');
const { UserService } = require('./services/user.service');
const { CheckoutController } = require('./controllers/checkout.controller');
const { ReportController } = require('./controllers/report.controller');
const { UserController } = require('./controllers/user.controller');
const { requireAdmin } = require('./middlewares/auth');
const { errorHandler } = require('./middlewares/errorHandler');
const { buildRouter } = require('./routes');

function createApp({ db, config: appConfig, logger }) {
    const users = new UserModel(db);
    const courses = new CourseModel(db);
    const enrollments = new EnrollmentModel(db);
    const payments = new PaymentModel(db);
    const auditLogs = new AuditLogModel(db);
    const financialReports = new FinancialReportModel(db);

    const paymentGateway = new SimulatedPaymentGateway({ apiKey: appConfig.paymentGatewayKey, logger });

    const checkoutService = new CheckoutService({
        db, users, courses, enrollments, payments, auditLogs, paymentGateway, logger,
    });
    const reportService = new ReportService({ financialReports });
    const userService = new UserService({ db, users, enrollments, payments, logger });

    const app = express();
    app.use(express.json());
    app.use(buildRouter({
        checkoutController: new CheckoutController(checkoutService),
        reportController: new ReportController(reportService),
        userController: new UserController(userService),
        requireAdmin: requireAdmin(appConfig.adminToken),
    }));
    app.use(errorHandler(logger));
    return app;
}

async function bootstrap(logger) {
    const db = await openDatabase(config.dbPath);
    await initSchema(db);
    await seedDatabase(db);
    const migrated = await migrateLegacyPasswords(db);
    if (migrated > 0) logger.info(`${migrated} senha(s) legada(s) migrada(s) para scrypt`);

    if (!config.adminToken) logger.warn('ADMIN_TOKEN não definido: rotas administrativas responderão 403');
    if (!config.paymentGatewayKey) logger.warn('PAYMENT_GATEWAY_KEY não definida (gateway simulado em uso)');

    const app = createApp({ db, config, logger });
    const server = app.listen(config.port, () => {
        logger.info(`LMS API rodando na porta ${config.port}`);
    });

    const shutdown = () => {
        server.close(() => db.close().finally(() => process.exit(0)));
    };
    process.once('SIGINT', shutdown);
    process.once('SIGTERM', shutdown);
}

if (require.main === module) {
    const logger = createLogger(config.logLevel);
    bootstrap(logger).catch((err) => {
        logger.error('Falha ao iniciar a aplicação', err);
        process.exit(1);
    });
}

module.exports = { createApp };
