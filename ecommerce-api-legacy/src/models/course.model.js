const COURSE_ACTIVE = 1;

class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(courseId) {
        return this.db.get(
            'SELECT id, title, price FROM courses WHERE id = ? AND active = ?',
            [courseId, COURSE_ACTIVE],
        );
    }
}

module.exports = { CourseModel, COURSE_ACTIVE };
