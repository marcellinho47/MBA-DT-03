const { parsePositiveInt } = require('../validators/common.validator');
const { USER_DELETED_MESSAGE } = require('../views/serializers');

class UserController {
    constructor(userService) {
        this.userService = userService;
    }

    deleteUser = async (req, res) => {
        const userId = parsePositiveInt(req.params.id);
        await this.userService.deleteUser(userId);
        res.send(USER_DELETED_MESSAGE);
    };
}

module.exports = { UserController };
