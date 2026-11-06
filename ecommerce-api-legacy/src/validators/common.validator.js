const { ValidationError } = require('../errors');

const POSITIVE_INTEGER = /^[1-9]\d*$/;

const isNonEmptyString = (value) => typeof value === 'string' && value.trim() !== '';

// Aceita inteiro positivo como número JSON ou string numérica ("2"), como o original.
function parsePositiveInt(value) {
    if (Number.isSafeInteger(value) && value > 0) return value;
    if (typeof value === 'string' && POSITIVE_INTEGER.test(value)) {
        const parsed = Number(value);
        if (Number.isSafeInteger(parsed)) return parsed;
    }
    throw new ValidationError();
}

module.exports = { isNonEmptyString, parsePositiveInt };
