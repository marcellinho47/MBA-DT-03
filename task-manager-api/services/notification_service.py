"""Notifications for task events. The e-mail transport is injected, so business code never
creates SMTP connections and tests/dev can run without a mail server."""
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class LogEmailSender:
    """Default transport when SMTP is not configured: records the e-mail in the log."""

    def send(self, to, subject, body):
        logger.info("E-mail (not sent, SMTP not configured) to=%s subject=%r", to, subject)
        return True


class SmtpEmailSender:
    def __init__(self, host, port, username, password, sender, use_tls=True, timeout=10):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self.use_tls = use_tls
        self.timeout = timeout

    def send(self, to, subject, body):
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError):
            logger.exception("Failed to send e-mail to %s", to)
            return False
        logger.info("E-mail sent to %s", to)
        return True


class NotificationService:
    def __init__(self, email_sender):
        self.email_sender = email_sender

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}"
        )
        return self.email_sender.send(user.email, subject, body)
