// Logger mínimo com níveis (o projeto não tem biblioteca de log nas dependências).
// Nunca registre senhas, segredos ou números de cartão completos.
const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;

    const write = (name, sink) => (message, ...meta) => {
        if (LEVELS[name] > threshold) return;
        sink(`${new Date().toISOString()} [${name.toUpperCase()}] ${message}`, ...meta);
    };

    return {
        error: write('error', console.error),
        warn: write('warn', console.warn),
        info: write('info', console.info),
        debug: write('debug', console.debug),
    };
}

module.exports = { createLogger };
