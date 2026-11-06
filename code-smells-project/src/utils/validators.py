"""Validação de entrada centralizada. Lança ValidationError com as mensagens originais da API."""
import math
import re

from src.exceptions import ValidationError
from src.models.constants import (
    CATEGORIA_PADRAO,
    CATEGORIAS_VALIDAS,
    NOME_PRODUTO_MAX,
    NOME_PRODUTO_MIN,
    STATUS_PEDIDO,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _as_int(value):
    """Inteiro (aceita 5.0) ou None se não for inteiro."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _require_dict(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def validate_produto(dados):
    """A mesma regra vale para criar e atualizar (PUT substitui o recurso inteiro)."""
    dados = _require_dict(dados)
    for campo, mensagem in (("nome", "Nome é obrigatório"),
                            ("preco", "Preço é obrigatório"),
                            ("estoque", "Estoque é obrigatório")):
        if campo not in dados:
            raise ValidationError(mensagem)

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = _as_int(dados["estoque"])
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if not _is_number(preco):
        raise ValidationError("Preço deve ser numérico")
    if estoque is None:
        raise ValidationError("Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(f"Categoria inválida. Válidas: {CATEGORIAS_VALIDAS}")

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def validate_novo_usuario(dados):
    dados = _require_dict(dados)
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(v, str) for v in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")
    email = email.strip()
    if not _EMAIL_RE.match(email):
        raise ValidationError("Email inválido")
    return {"nome": nome, "email": email, "senha": senha}


def validate_credenciais(dados):
    dados = dados if isinstance(dados, dict) else {}
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha or not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha são obrigatórios")
    return email.strip(), senha


def validate_pedido(dados):
    dados = _require_dict(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    usuario_id = _as_int(usuario_id)
    if usuario_id is None or usuario_id <= 0:
        raise ValidationError("Usuario ID inválido")
    if not isinstance(itens, list):
        raise ValidationError("Itens do pedido inválidos")

    normalizados = []
    for item in itens:
        produto_id = _as_int(item.get("produto_id")) if isinstance(item, dict) else None
        quantidade = _as_int(item.get("quantidade")) if isinstance(item, dict) else None
        if produto_id is None or quantidade is None or quantidade <= 0:
            raise ValidationError("Cada item precisa de produto_id e quantidade inteira positiva")
        normalizados.append({"produto_id": produto_id, "quantidade": quantidade})
    return usuario_id, normalizados


def validate_status(dados):
    status = dados.get("status", "") if isinstance(dados, dict) else ""
    if status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")
    return status


def parse_float_param(value, nome):
    """Parâmetro numérico opcional de query string. Ausente ou vazio vira None."""
    if value is None or value == "":
        return None
    try:
        numero = float(value)
    except ValueError:
        raise ValidationError(f"Parâmetro {nome} deve ser numérico") from None
    if not math.isfinite(numero):
        raise ValidationError(f"Parâmetro {nome} deve ser numérico")
    return numero
