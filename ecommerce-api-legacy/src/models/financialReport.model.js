// Leitura agregada para o relatório financeiro: uma única consulta com JOINs
// (substitui as 1 + C + 2E consultas em loop do código original).
// Cada matrícula tem no máximo um pagamento (garantido pelo CheckoutService).
class FinancialReportModel {
    constructor(db) {
        this.db = db;
    }

    findCourseEnrollments() {
        return this.db.all(`
            SELECT c.id      AS courseId,
                   c.title   AS courseTitle,
                   e.id      AS enrollmentId,
                   u.name    AS studentName,
                   p.amount  AS paymentAmount,
                   p.status  AS paymentStatus
              FROM courses c
              LEFT JOIN enrollments e ON e.course_id = c.id
              LEFT JOIN users u       ON u.id = e.user_id
              LEFT JOIN payments p    ON p.enrollment_id = e.id
             ORDER BY c.id, e.id
        `);
    }
}

module.exports = { FinancialReportModel };
