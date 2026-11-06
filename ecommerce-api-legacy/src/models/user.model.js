class UserModel {
    constructor(db) {
        this.db = db;
    }

    findByEmail(email) {
        return this.db.get(
            'SELECT id, name, email, pass AS passwordHash FROM users WHERE email = ?',
            [email],
        );
    }

    async create({ name, email, passwordHash }) {
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, passwordHash],
        );
        return lastID;
    }

    async deleteById(userId) {
        const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [userId]);
        return changes > 0;
    }
}

module.exports = { UserModel };
