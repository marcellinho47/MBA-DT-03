const crypto = require('crypto');
const { ForbiddenError } = require('../errors');

const ADMIN_TOKEN_HEADER = 'X-Admin-Token';

const digest = (value) => crypto.createHash('sha256').update(String(value)).digest();

// Guarda das rotas administrativas: compara o header com ADMIN_TOKEN em tempo constante.
// Sem ADMIN_TOKEN configurado, todo acesso é negado (fail closed).
function requireAdmin(adminToken) {
    const expected = adminToken ? digest(adminToken) : null;
    return (req, res, next) => {
        const provided = req.get(ADMIN_TOKEN_HEADER);
        const authorized = expected !== null
            && typeof provided === 'string'
            && crypto.timingSafeEqual(digest(provided), expected);
        next(authorized ? undefined : new ForbiddenError());
    };
}

module.exports = { requireAdmin, ADMIN_TOKEN_HEADER };
