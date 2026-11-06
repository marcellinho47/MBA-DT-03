// Exceções de domínio. O error handler central converte cada uma em status HTTP;
// as mensagens são as mesmas que a API original devolvia em texto puro.
class AppError extends Error {
    constructor(message, status) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class PaymentDeniedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Credenciais inválidas') { super(message, 401); }
}

class ForbiddenError extends AppError {
    constructor(message = 'Acesso negado') { super(message, 403); }
}

class NotFoundError extends AppError {
    constructor(message = 'Não encontrado') { super(message, 404); }
}

module.exports = {
    AppError,
    ValidationError,
    PaymentDeniedError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
};
