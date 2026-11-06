const sqlite3 = require('sqlite3');

// Envolve o driver de callbacks do sqlite3 em uma API baseada em Promises
// (run/get/all) e oferece transações serializadas sobre a conexão única.
function wrapConnection(raw) {
    let transactionQueue = Promise.resolve();

    const db = {
        run(sql, params = []) {
            return new Promise((resolve, reject) => {
                raw.run(sql, params, function onRun(err) {
                    if (err) return reject(err);
                    resolve({ lastID: this.lastID, changes: this.changes });
                });
            });
        },

        get(sql, params = []) {
            return new Promise((resolve, reject) => {
                raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
            });
        },

        all(sql, params = []) {
            return new Promise((resolve, reject) => {
                raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
            });
        },

        // Executa `work` entre BEGIN/COMMIT, com ROLLBACK em caso de erro.
        // Como há uma única conexão, as transações são enfileiradas para não se intercalarem.
        transaction(work) {
            const result = transactionQueue.then(async () => {
                await db.run('BEGIN');
                try {
                    const value = await work(db);
                    await db.run('COMMIT');
                    return value;
                } catch (err) {
                    await db.run('ROLLBACK');
                    throw err;
                }
            });
            transactionQueue = result.catch(() => {});
            return result;
        },

        close() {
            return new Promise((resolve, reject) => {
                raw.close((err) => (err ? reject(err) : resolve()));
            });
        },
    };

    return db;
}

function openDatabase(path) {
    return new Promise((resolve, reject) => {
        const raw = new sqlite3.Database(path, (err) => {
            if (err) return reject(err);
            resolve(wrapConnection(raw));
        });
    });
}

module.exports = { openDatabase };
