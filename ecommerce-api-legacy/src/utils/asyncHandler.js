// Express 4 não encaminha rejeições de handlers async: envia-as ao error handler central.
module.exports = (handler) => (req, res, next) => {
    Promise.resolve(handler(req, res, next)).catch(next);
};
