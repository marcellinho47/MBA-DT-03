# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
ADMIN_TOKEN=troque-me npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória por padrão e já carrega seeds automaticamente no boot (usuário `leonan@fullcycle.com.br` / senha `123`).

### Variáveis de ambiente

Veja `.env.example`. As variáveis são lidas do ambiente do processo:

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `DB_PATH` | `:memory:` | Banco SQLite (memória ou arquivo) |
| `ADMIN_TOKEN` | vazio | Token exigido no header `X-Admin-Token` das rotas administrativas; vazio = rotas bloqueadas (403) |
| `PAYMENT_GATEWAY_KEY` | vazio | Chave do gateway de pagamento (gateway atual é simulado) |
| `LOG_LEVEL` | `info` | `error`, `warn`, `info` ou `debug` |

No PowerShell: `$env:ADMIN_TOKEN="troque-me"; npm start`.

## Estrutura

```
src/
├── app.js            # composition root
├── config/           # leitura de variáveis de ambiente
├── database/         # conexão promisificada + transações, schema, seed
├── errors/           # exceções de domínio
├── models/           # acesso a dados por entidade (SQL parametrizado)
├── gateways/         # gateway de pagamento (simulado, injetável)
├── services/         # regras de negócio (checkout, relatório, usuários)
├── controllers/      # fluxo HTTP
├── validators/       # validação de entrada
├── views/            # serialização das respostas
├── routes/           # mapeamento de rotas
├── middlewares/      # autorização admin e error handler central
└── utils/            # hash de senha, logger, asyncHandler
```

Exemplos de requisições estão em `api.http`.
