const { PAYMENT_STATUS } = require('../models/payment.model');

const UNKNOWN_STUDENT = 'Unknown';

class ReportService {
    constructor({ financialReports }) {
        this.financialReports = financialReports;
    }

    // Receita por curso (somente pagamentos PAID) e lista de alunos com o valor pago.
    // Cursos sem matrícula aparecem com receita 0 e lista vazia, como no original.
    async getFinancialReport() {
        const rows = await this.financialReports.findCourseEnrollments();
        const courses = new Map();

        for (const row of rows) {
            if (!courses.has(row.courseId)) {
                courses.set(row.courseId, { title: row.courseTitle, revenue: 0, students: [] });
            }
            if (row.enrollmentId === null) continue;

            const course = courses.get(row.courseId);
            if (row.paymentStatus === PAYMENT_STATUS.PAID) course.revenue += row.paymentAmount;
            course.students.push({
                name: row.studentName ?? UNKNOWN_STUDENT,
                paid: row.paymentAmount ?? 0,
            });
        }

        return [...courses.values()];
    }
}

module.exports = { ReportService };
