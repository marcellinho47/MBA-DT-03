"""Repositório de pedidos e itens de pedido."""
from src.models.constants import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

PRODUTO_DESCONHECIDO = "Desconhecido"


class PedidoRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, usuario_id, total, status=STATUS_PENDENTE):
        cursor = self.conn.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)", (usuario_id, status, total)
        )
        return cursor.lastrowid

    def add_item(self, pedido_id, produto_id, quantidade, preco_unitario):
        self.conn.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )

    def find_by_id(self, pedido_id):
        row = self.conn.execute(
            "SELECT id, usuario_id, status, total, criado_em FROM pedidos WHERE id = ?", (pedido_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def update_status(self, pedido_id, status):
        self.conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))

    def list_with_items(self, usuario_id=None):
        """Pedidos com seus itens em uma única consulta (sem N+1)."""
        where, params = ("WHERE p.usuario_id = ?", (usuario_id,)) if usuario_id is not None else ("", ())
        rows = self.conn.execute(
            f"""
            SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
                   i.id AS item_id, i.produto_id, i.quantidade, i.preco_unitario,
                   pr.id AS produto_ref, pr.nome AS produto_nome
            FROM pedidos p
            LEFT JOIN itens_pedido i ON i.pedido_id = p.id
            LEFT JOIN produtos pr ON pr.id = i.produto_id
            {where}
            ORDER BY p.id, i.id
            """,
            params,
        ).fetchall()

        pedidos = {}
        for row in rows:
            pedido = pedidos.get(row["id"])
            if pedido is None:
                pedido = pedidos[row["id"]] = {
                    "id": row["id"],
                    "usuario_id": row["usuario_id"],
                    "status": row["status"],
                    "total": row["total"],
                    "criado_em": row["criado_em"],
                    "itens": [],
                }
            if row["item_id"] is not None:
                pedido["itens"].append({
                    "produto_id": row["produto_id"],
                    "produto_nome": PRODUTO_DESCONHECIDO if row["produto_ref"] is None else row["produto_nome"],
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                })
        return list(pedidos.values())

    def sales_summary(self):
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS total_pedidos,
                   COALESCE(SUM(total), 0) AS faturamento,
                   COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS pendentes,
                   COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS aprovados,
                   COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS cancelados
            FROM pedidos
            """,
            (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
        ).fetchone()
        return dict(row)

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
