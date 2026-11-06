"""Notificações (por ora simuladas em log). Ponto único para a futura integração real de email/SMS/push."""
import logging

from src.models.constants import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


class NotificationService:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("[email] Pedido %s criado para usuario %s", pedido_id, usuario_id)
        logger.info("[sms] Seu pedido foi recebido!")
        logger.info("[push] Novo pedido recebido pelo sistema")

    def status_alterado(self, pedido_id, status):
        if status == STATUS_APROVADO:
            logger.info("Pedido %s foi aprovado! Preparar envio.", pedido_id)
        elif status == STATUS_CANCELADO:
            logger.info("Pedido %s cancelado. Devolver estoque.", pedido_id)
