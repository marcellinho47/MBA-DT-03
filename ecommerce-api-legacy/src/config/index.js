// Único módulo que lê variáveis de ambiente. Nenhum segredo literal aqui:
// os defaults servem apenas para desenvolvimento local.
const DEFAULT_PORT = 3000;
const DEFAULT_DB_PATH = ':memory:';
const LOG_LEVELS = ['error', 'warn', 'info', 'debug'];
const DEFAULT_LOG_LEVEL = 'info';

function readPort(raw) {
    if (raw === undefined || raw === '') return DEFAULT_PORT;
    const port = Number(raw);
    if (!Number.isInteger(port) || port < 0 || port > 65535) {
        throw new Error(`PORT inválida: "${raw}"`);
    }
    return port;
}

function readLogLevel(raw) {
    return LOG_LEVELS.includes(raw) ? raw : DEFAULT_LOG_LEVEL;
}

module.exports = Object.freeze({
    port: readPort(process.env.PORT),
    dbPath: process.env.DB_PATH || DEFAULT_DB_PATH,
    // Sem token configurado as rotas administrativas ficam bloqueadas (fail closed).
    adminToken: process.env.ADMIN_TOKEN || '',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    logLevel: readLogLevel(process.env.LOG_LEVEL),
});
