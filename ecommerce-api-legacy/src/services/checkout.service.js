const { hashPassword, verifyPassword } = require('../utils/password');
const { PAYMENT_STATUS } = require('../models/payment.model');
const { NotFoundError, UnauthorizedError, PaymentDeniedError } = require('../errors');

class CheckoutService {
    constructor({ db, users, courses, enrollments, payments, auditLogs, paymentGateway, logger }) {
        this.db = db;
        this.users = users;
        this.courses = courses;
        this.enrollments = enrollments;
        this.payments = payments;
        this.auditLogs = auditLogs;
        this.paymentGateway = paymentGateway;
        this.logger = logger;
    }

    // Compra de um curso: identifica (ou cria) o aluno, cobra e registra matrícula,
    // pagamento e auditoria de forma atômica. Pagamento recusado não grava nada.
    async checkout({ name, email, password, courseId, cardNumber }) {
        const course = await this.courses.findActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        const existingUser = await this.users.findByEmail(email);
        if (existingUser && !(await verifyPassword(password, existingUser.passwordHash))) {
            throw new UnauthorizedError('Credenciais inválidas');
        }

        const status = await this.paymentGateway.charge({ cardNumber, amount: course.price });
        if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeniedError();

        const newUserHash = existingUser ? null : await hashPassword(password);

        const enrollmentId = await this.db.transaction(async () => {
            const userId = existingUser
                ? existingUser.id
                : await this.users.create({ name, email, passwordHash: newUserHash });
            const newEnrollmentId = await this.enrollments.create(userId, course.id);
            await this.payments.create({ enrollmentId: newEnrollmentId, amount: course.price, status });
            await this.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);
            return newEnrollmentId;
        });

        this.logger.info(`Checkout concluído: matrícula ${enrollmentId} no curso ${course.id}`);
        return { enrollmentId };
    }
}

module.exports = { CheckoutService };
