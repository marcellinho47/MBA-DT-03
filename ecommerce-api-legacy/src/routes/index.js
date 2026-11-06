const { Router } = require('express');
const asyncHandler = require('../utils/asyncHandler');

// Camada de view: apenas o mapeamento URL + método → controller (+ middlewares).
function buildRouter({ checkoutController, reportController, userController, requireAdmin }) {
    const router = Router();

    router.post('/api/checkout', asyncHandler(checkoutController.checkout));
    router.get('/api/admin/financial-report', requireAdmin, asyncHandler(reportController.financialReport));
    router.delete('/api/users/:id', requireAdmin, asyncHandler(userController.deleteUser));

    return router;
}

module.exports = { buildRouter };
