const { validateCheckoutInput } = require('../validators/checkout.validator');
const { serializeCheckout } = require('../views/serializers');

class CheckoutController {
    constructor(checkoutService) {
        this.checkoutService = checkoutService;
    }

    checkout = async (req, res) => {
        const command = validateCheckoutInput(req.body);
        const result = await this.checkoutService.checkout(command);
        res.status(200).json(serializeCheckout(result));
    };
}

module.exports = { CheckoutController };
