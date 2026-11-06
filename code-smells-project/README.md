# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo. Bancos antigos, com senhas em texto puro, são migrados para hash no boot.

A configuração vem de variáveis de ambiente; veja `.env.example`. Fora do ambiente local, defina ao menos `SECRET_KEY`:

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python app.py
```

## Autenticação

`POST /login` devolve um `token`. Rotas administrativas exigem o token de um usuário `admin` no header `Authorization: Bearer <token>`:

- `POST/PUT/DELETE /produtos...`
- `GET /usuarios`
- `GET /pedidos`
- `PUT /pedidos/<id>/status`
- `GET /relatorios/vendas`
- `POST /admin/reset-db` (exige também `ENABLE_ADMIN_RESET=true`)

Usuário admin de exemplo (apenas desenvolvimento): `admin@loja.com` / `admin123`.

```bash
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' | python -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -s localhost:5000/relatorios/vendas -H "Authorization: Bearer $TOKEN"
```

## Estrutura

```
app.py              entry point (composition root)
src/app.py          create_app(): config, banco, injeção de dependências, rotas, erros
src/config/         leitura das variáveis de ambiente
src/database.py     conexão por requisição, transações, schema, seed, migrações
src/models/         repositórios (SQL parametrizado) e constantes de domínio
src/services/       regras de negócio e casos de uso
src/controllers/    fluxo HTTP por domínio
src/views/          rotas (blueprint) e serializers
src/middlewares/    error handler central e guards de autenticação
src/utils/          validação de entrada e hash de senha
```
