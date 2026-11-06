const { NotFoundError } = require('../errors');

class UserService {
    constructor({ db, users, enrollments, payments, logger }) {
        this.db = db;
        this.users = users;
        this.enrollments = enrollments;
        this.payments = payments;
        this.logger = logger;
    }

    // Exclusão em cascata (pagamentos → matrículas → usuário) numa única transação,
    // para não deixar registros órfãos no banco.
    async deleteUser(userId) {
        await this.db.transaction(async () => {
            const removedPayments = await this.payments.deleteByUserId(userId);
            const removedEnrollments = await this.enrollments.deleteByUserId(userId);
            const removed = await this.users.deleteById(userId);
            if (!removed) throw new NotFoundError('Usuário não encontrado');
            this.logger.info(
                `Usuário ${userId} removido (${removedEnrollments} matrículas, ${removedPayments} pagamentos)`,
            );
        });
    }
}

module.exports = { UserService };
