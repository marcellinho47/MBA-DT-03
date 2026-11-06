const { serializeFinancialReport } = require('../views/serializers');

class ReportController {
    constructor(reportService) {
        this.reportService = reportService;
    }

    financialReport = async (req, res) => {
        const report = await this.reportService.getFinancialReport();
        res.json(serializeFinancialReport(report));
    };
}

module.exports = { ReportController };
