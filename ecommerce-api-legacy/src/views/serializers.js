// Camada de view: define exatamente os campos expostos no contrato HTTP.
const CHECKOUT_SUCCESS_MESSAGE = 'Sucesso';
const USER_DELETED_MESSAGE = 'Usuário deletado, junto com suas matrículas e pagamentos.';

const serializeCheckout = ({ enrollmentId }) => ({
    msg: CHECKOUT_SUCCESS_MESSAGE,
    enrollment_id: enrollmentId,
});

const serializeFinancialReport = (courses) => courses.map((course) => ({
    course: course.title,
    revenue: course.revenue,
    students: course.students.map((student) => ({ student: student.name, paid: student.paid })),
}));

module.exports = { serializeCheckout, serializeFinancialReport, USER_DELETED_MESSAGE };
