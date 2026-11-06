"""Constantes e regras de domínio da loja."""

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)

TIPO_ADMIN = "admin"
TIPO_CLIENTE = "cliente"

# (faturamento mínimo, exclusivo; percentual de desconto), da maior faixa para a menor
FAIXAS_DESCONTO = (
    (10_000, 0.10),
    (5_000, 0.05),
    (1_000, 0.02),
)
