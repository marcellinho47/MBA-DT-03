const { AppError } = require('../errors');

const BAD_REQUEST_MESSAGE = 'Bad Request';
const INTERNAL_ERROR_MESSAGE = 'Erro interno do servidor';

// Error handler central: exceções de domínio → status + mensagem em texto puro
// (mesmo formato de corpo de erro da API original). Detalhes internos só vão para o log.
function errorHandler(logger) {
    return (err, req, res, next) => {
        if (res.headersSent) return next(err);

        if (err instanceof AppError) {
            return res.status(err.status).send(err.message);
        }
        // Erros do body parser do Express (JSON malformado, payload grande demais...).
        if (err.expose && err.status >= 400 && err.status < 500) {
            return res.status(err.status).send(BAD_REQUEST_MESSAGE);
        }

        logger.error(`Erro não tratado em ${req.method} ${req.path}`, err);
        return res.status(500).send(INTERNAL_ERROR_MESSAGE);
    };
}

module.exports = { errorHandler };
