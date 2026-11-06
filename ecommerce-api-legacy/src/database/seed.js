const { hashPassword, isPasswordHash } = require('../utils/password');
const { PAYMENT_STATUS } = require('../models/payment.model');
const { COURSE_ACTIVE } = require('../models/course.model');

// Dados de desenvolvimento (mesmos do projeto original). A senha do usuário
// de seed continua sendo "123", mas agora é gravada com hash.
const SEED_USER = { name: 'Leonan', email: 'leonan@fullcycle.com.br', password: '123' };
const SEED_COURSES = [
    { title: 'Clean Architecture', price: 997.0 },
    { title: 'Docker', price: 497.0 },
];

async function seedDatabase(db) {
    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) return false;

    const passwordHash = await hashPassword(SEED_USER.password);
    await db.transaction(async (tx) => {
        const { lastID: userId } = await tx.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [SEED_USER.name, SEED_USER.email, passwordHash],
        );
        const courseIds = [];
        for (const course of SEED_COURSES) {
            const { lastID } = await tx.run(
                'INSERT INTO courses (title, price, active) VALUES (?, ?, ?)',
                [course.title, course.price, COURSE_ACTIVE],
            );
            courseIds.push(lastID);
        }
        const { lastID: enrollmentId } = await tx.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseIds[0]],
        );
        await tx.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, SEED_COURSES[0].price, PAYMENT_STATUS.PAID],
        );
    });
    return true;
}

// Migração de legado: bancos persistentes (DB_PATH) criados antes desta versão
// guardavam a senha do seed em texto puro. Re-hash de tudo que não está no formato novo.
async function migrateLegacyPasswords(db) {
    const users = await db.all('SELECT id, pass FROM users WHERE pass IS NOT NULL');
    const legacy = users.filter((user) => !isPasswordHash(user.pass));
    for (const user of legacy) {
        const passwordHash = await hashPassword(user.pass);
        await db.run('UPDATE users SET pass = ? WHERE id = ?', [passwordHash, user.id]);
    }
    return legacy.length;
}

module.exports = { seedDatabase, migrateLegacyPasswords };
