"""Repositório de produtos: acesso a dados com SQL parametrizado."""

_COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def _to_produto(row):
    return dict(row) if row is not None else None


class ProdutoRepository:
    def __init__(self, conn):
        self.conn = conn

    def list_all(self):
        rows = self.conn.execute(f"SELECT {_COLUNAS} FROM produtos ORDER BY id").fetchall()
        return [_to_produto(row) for row in rows]

    def find_by_id(self, produto_id):
        row = self.conn.execute(f"SELECT {_COLUNAS} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return _to_produto(row)

    def find_by_ids(self, produto_ids):
        """Retorna {id: produto} para os ids existentes, em uma única consulta."""
        ids = list(produto_ids)
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self.conn.execute(f"SELECT {_COLUNAS} FROM produtos WHERE id IN ({placeholders})", ids).fetchall()
        return {row["id"]: _to_produto(row) for row in rows}

    def search(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        clauses, params = [], []
        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clauses.append("preco <= ?")
            params.append(preco_max)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(f"SELECT {_COLUNAS} FROM produtos {where} ORDER BY id", params).fetchall()
        return [_to_produto(row) for row in rows]

    def create(self, nome, descricao, preco, estoque, categoria):
        cursor = self.conn.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        return cursor.lastrowid

    def update(self, produto_id, nome, descricao, preco, estoque, categoria):
        self.conn.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )

    def delete(self, produto_id):
        self.conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def decrement_stock(self, produto_id, quantidade):
        """Baixa o estoque só se houver saldo. Retorna False se não havia estoque suficiente."""
        cursor = self.conn.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
        return cursor.rowcount == 1

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
