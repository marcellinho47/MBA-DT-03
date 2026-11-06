const { ValidationError } = require('../errors');
const { isNonEmptyString, parsePositiveInt } = require('./common.validator');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_PATTERN = /^\d{1,19}$/;

// Mantém os nomes de campos do contrato (usr, eml, pwd, c_id, card) apenas na borda
// e devolve o comando com nomes de domínio. Qualquer entrada inválida → 400 "Bad Request".
function validateCheckoutInput(body) {
    if (!body || typeof body !== 'object') throw new ValidationError();
    const { usr, eml, pwd, c_id: courseId, card } = body;

    if (![usr, eml, pwd, card].every(isNonEmptyString)) throw new ValidationError();
    if (!EMAIL_PATTERN.test(eml)) throw new ValidationError();
    if (!CARD_PATTERN.test(card)) throw new ValidationError();

    return {
        name: usr.trim(),
        email: eml.trim(),
        password: pwd,
        courseId: parsePositiveInt(courseId),
        cardNumber: card,
    };
}

module.exports = { validateCheckoutInput };
