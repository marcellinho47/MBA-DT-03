const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

class PaymentModel {
    constructor(db) {
        this.db = db;
    }

    async create({ enrollmentId, amount, status }) {
        const { lastID } = await this.db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status],
        );
        return lastID;
    }

    async deleteByUserId(userId) {
        const { changes } = await this.db.run(
            'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
            [userId],
        );
        return changes;
    }
}

module.exports = { PaymentModel, PAYMENT_STATUS };
