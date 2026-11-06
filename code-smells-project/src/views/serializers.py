"""Serializers: definem exatamente quais campos saem na resposta. Senha e hash nunca saem."""


def serialize_produto(produto):
    return {
        "id": produto["id"],
        "nome": produto["nome"],
        "descricao": produto["descricao"],
        "preco": produto["preco"],
        "estoque": produto["estoque"],
        "categoria": produto["categoria"],
        "ativo": produto["ativo"],
        "criado_em": produto["criado_em"],
    }


def serialize_usuario(usuario):
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "tipo": usuario["tipo"],
        "criado_em": usuario["criado_em"],
    }


def serialize_usuario_autenticado(usuario):
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "tipo": usuario["tipo"],
    }


def serialize_pedido(pedido):
    return {
        "id": pedido["id"],
        "usuario_id": pedido["usuario_id"],
        "status": pedido["status"],
        "total": pedido["total"],
        "criado_em": pedido["criado_em"],
        "itens": [
            {
                "produto_id": item["produto_id"],
                "produto_nome": item["produto_nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            }
            for item in pedido["itens"]
        ],
    }
