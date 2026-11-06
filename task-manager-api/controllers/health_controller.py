from datetime import datetime


class HealthController:
    def index(self):
        return {"message": "Task Manager API", "version": "1.0"}

    def health(self):
        # Local server time, as in the original contract.
        return {"status": "ok", "timestamp": str(datetime.now())}
