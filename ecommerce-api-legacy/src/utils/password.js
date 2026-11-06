const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SCHEME = 'scrypt';
const SALT_BYTES = 16;
const KEY_LENGTH = 64;

async function hashPassword(raw) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derived = await scrypt(String(raw), salt, KEY_LENGTH);
    return `${SCHEME}$${salt}$${derived.toString('hex')}`;
}

function isPasswordHash(stored) {
    const parts = String(stored).split('$');
    return parts.length === 3 && parts[0] === SCHEME;
}

async function verifyPassword(raw, stored) {
    if (!isPasswordHash(stored)) return false;
    const [, salt, hashHex] = String(stored).split('$');
    const expected = Buffer.from(hashHex, 'hex');
    if (expected.length !== KEY_LENGTH) return false;
    const candidate = await scrypt(String(raw), salt, KEY_LENGTH);
    return crypto.timingSafeEqual(candidate, expected);
}

module.exports = { hashPassword, verifyPassword, isPasswordHash };
