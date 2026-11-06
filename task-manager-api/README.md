# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Refatorada para MVC: `routes/` + `views/` (View), `controllers/` (Controller), `models/` + `services/` (Model), com `config/`, `middlewares/` e `app.py` como composition root.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # opcional: defina SECRET_KEY e demais variáveis
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` recria o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

## Configuração (variáveis de ambiente)

Veja `.env.example`. As principais:

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | aleatória por processo | Assina os tokens de login. Defina em qualquer ambiente real. |
| `DATABASE_URL` | `sqlite:///tasks.db` | URI do banco (relativa à pasta `instance/`). |
| `FLASK_DEBUG` | `false` | Nunca habilite fora do desenvolvimento local. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Use `HOST=0.0.0.0` em contêineres. |
| `CORS_ORIGINS` | `*` | Lista separada por vírgulas; restrinja em produção. |
| `SMTP_HOST` ... | vazio | Sem `SMTP_HOST`, as notificações de atribuição de task são apenas registradas em log. |

## Autenticação

`POST /login` devolve um `token` assinado. Envie-o como `Authorization: Bearer <token>` em:

- `PUT /users/<id>` e `DELETE /users/<id>` — o próprio usuário ou um admin; alterar `role`/`active` exige admin;
- `POST /users` com `role` diferente de `user` — exige admin.

Senhas são armazenadas com `werkzeug.security` (scrypt). Hashes MD5 de bancos antigos são convertidos automaticamente no próximo login bem-sucedido.
