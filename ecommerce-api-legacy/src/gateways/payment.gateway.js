const { PAYMENT_STATUS } = require('../models/payment.model');

// Regra do gateway simulado herdada do código original: cartões iniciados em "4" são aprovados.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

const maskCard = (cardNumber) => `****${String(cardNumber).slice(-VISIBLE_CARD_DIGITS)}`;

// Adaptador de pagamento injetável. Um gateway real implementaria a mesma interface
// (`charge`) usando `apiKey`, sem alterar o CheckoutService.
class SimulatedPaymentGateway {
    constructor({ apiKey, logger }) {
        this.apiKey = apiKey;
        this.logger = logger;
    }

    async charge({ cardNumber, amount }) {
        const status = cardNumber.startsWith(APPROVED_CARD_PREFIX)
            ? PAYMENT_STATUS.PAID
            : PAYMENT_STATUS.DENIED;
        this.logger.info(`Cobrança de ${amount} no cartão ${maskCard(cardNumber)}: ${status}`);
        return status;
    }
}

module.exports = { SimulatedPaymentGateway, maskCard };
