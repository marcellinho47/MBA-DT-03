"""Infraestrutura de banco: conexão por requisição, transações, schema, seed e migrações."""
import logging
import sqlite3
from contextlib import contextmanager

from flask import current_app, g

from src.models.constants import TIPO_ADMIN, TIPO_CLIENTE
from src.utils.security import hash_password, is_password_hash

logger = logging.getLogger(__name__)

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
)

SEED_PRODUTOS = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)

# Credenciais de demonstração para desenvolvimento local. São gravadas como hash.
SEED_USUARIOS = (
    ("Admin", "admin@loja.com", "admin123", TIPO_ADMIN),
    ("João Silva", "joao@email.com", "123456", TIPO_CLIENTE),
    ("Maria Santos", "maria@email.com", "senha123", TIPO_CLIENTE),
)


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """Conexão da requisição atual, aberta sob demanda e fechada no teardown."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction(conn):
    """Unidade de trabalho atômica. BEGIN IMMEDIATE pega o lock de escrita logo no início."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()


def clear_all_data(conn):
    for table in ("itens_pedido", "pedidos", "produtos", "usuarios"):
        conn.execute(f"DELETE FROM {table}")  # nomes fixos, sem entrada externa


def init_db(path):
    conn = connect(path)
    try:
        with transaction(conn):
            for ddl in SCHEMA:
                conn.execute(ddl)
            if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
                _seed(conn)
            _migrate_plaintext_passwords(conn)
    finally:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app.config["DATABASE_PATH"])


def _seed(conn):
    conn.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        SEED_PRODUTOS,
    )
    conn.executemany(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        [(nome, email, hash_password(senha), tipo) for nome, email, senha, tipo in SEED_USUARIOS],
    )
    logger.info("Banco populado com dados de exemplo")


def _migrate_plaintext_passwords(conn):
    """Bancos legados guardavam senhas em texto puro: troca cada uma pelo hash correspondente."""
    rows = conn.execute("SELECT id, senha FROM usuarios").fetchall()
    legados = [(hash_password(row["senha"] or ""), row["id"]) for row in rows if not is_password_hash(row["senha"])]
    if legados:
        conn.executemany("UPDATE usuarios SET senha = ? WHERE id = ?", legados)
        logger.warning("%d senha(s) em texto puro migrada(s) para hash", len(legados))
