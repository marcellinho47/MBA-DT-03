# Guidelines da Arquitetura MVC Alvo (Fase 3)

Em uma API HTTP, o MVC é interpretado assim:

- **Model** — os dados e as regras do domínio: entidades, regras de negócio e acesso a dados (repositórios). Não conhece HTTP.
- **View** — a representação exposta ao cliente: **definição das rotas** (URL + método → controller) e **serialização** da resposta (quais campos saem, em que formato). Numa API JSON não há templates; a "view" é o contrato HTTP.
- **Controller** — o fluxo de uma requisição: extrai e valida a entrada, chama o model/service, escolhe o status HTTP e entrega o resultado para a view serializar.

Complementos que não são camadas MVC mas são obrigatórios no resultado:

- **Config** — único lugar que lê variáveis de ambiente; nenhum outro módulo lê env ou contém segredos.
- **Services** (opcional, parte do lado "Model") — regras que envolvem mais de uma entidade ou efeitos colaterais (pagamento, notificação, relatórios agregados). Use quando a regra não pertence naturalmente a uma única entidade.
- **Middlewares** — preocupações transversais: tratamento central de erros, autenticação/autorização, logging de requisição.
- **Composition root** — o entry point: cria a aplicação, carrega config, inicializa banco, injeta dependências, registra rotas e middlewares. Sem regra de negócio.

## Regra de dependência

```
routes/views ──► controllers ──► services ──► models/repositories ──► database
      │                │              │
      └── middlewares   └── validators └── config (somente leitura)
```

- Dependências apontam **sempre para dentro** (da borda HTTP para o domínio). Um model nunca importa controller, request/response do framework ou módulo de rotas.
- Controllers **não** executam SQL nem consultas ORM diretamente; chamam services/repositórios.
- Rotas **não** contêm lógica: apenas mapeiam URL + método → função do controller (+ middlewares).
- Services/models **não** retornam objetos HTTP (`jsonify`, `res.json`) nem status codes; retornam dados ou lançam exceções de domínio.
- Infraestrutura (conexão, cliente SMTP, gateway) é **recebida** (parâmetro/construtor/factory), não criada dentro da regra de negócio.

## Responsabilidades por camada

| Camada | Faz | Não faz |
|---|---|---|
| `config` | Lê env vars, define defaults seguros de desenvolvimento, expõe constantes de configuração | Lógica de negócio; segredos literais |
| `models` / `repositories` | Esquema/entidades; consultas **parametrizadas**; mapeamento linha→entidade; regras intrínsecas à entidade (`is_overdue`, `check_password`) | Ler request; formatar resposta HTTP; enviar notificações |
| `services` | Casos de uso: orquestram repositórios, aplicam regras de negócio, controlam transações, disparam efeitos colaterais | Conhecer HTTP |
| `controllers` | Extrair parâmetros, validar entrada (via validators), chamar service, mapear resultado → status + corpo | SQL; regra de negócio; `try/except` genérico por handler |
| `views` / `routes` | Registrar rotas; serializers/DTOs que definem os campos expostos (sem dados sensíveis) | Lógica |
| `middlewares` | Error handler central (exceções de domínio → status HTTP), auth guard, logging | Regra de negócio |
| entry point | Composition root: `create_app()` / bootstrap | Rotas inline; SQL; segredos |

## Exceções de domínio + error handler central

Defina um pequeno conjunto de exceções e mapeie **uma vez** para HTTP:

| Exceção | Status |
|---|---|
| `ValidationError` | 400 |
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| qualquer outra | 500 com mensagem genérica (detalhe só no log) |

Preserve o **formato de corpo de erro** que a API original usava (ex.: `{"erro": "..."}` ou `{"error": "..."}`) para não quebrar clientes.

## Estruturas alvo por stack

Adapte nomes ao idioma/convenção do projeto (ex.: `produto_model.py` se o domínio está em português). Mantenha o entry point original no mesmo caminho.

### Python / Flask

```
<projeto>/
├── app.py                      # composition root fino: from src.app import create_app; app = create_app()
├── src/
│   ├── __init__.py
│   ├── app.py                  # create_app(): config, db, blueprints, error handlers
│   ├── config/
│   │   └── settings.py         # Settings lidos de os.environ
│   ├── database.py             # conexão/sessão por app ou por request; init do schema; seed
│   ├── models/                 # entidades + repositórios (SQL parametrizado ou ORM)
│   │   └── <entidade>_model.py
│   ├── services/               # casos de uso / regras de negócio
│   │   └── <dominio>_service.py
│   ├── controllers/            # fluxo HTTP por domínio
│   │   └── <dominio>_controller.py
│   ├── views/                  # rotas (blueprints) + serializers
│   │   ├── routes.py           # ou <dominio>_routes.py
│   │   └── serializers.py
│   ├── middlewares/
│   │   ├── error_handler.py
│   │   └── auth.py             # se houver rotas protegidas
│   └── utils/                  # helpers genuinamente genéricos (validação, datas)
├── .env.example
└── requirements.txt
```

**Projeto Flask já parcialmente organizado** (ex.: já tem `models/`, `routes/`, `services/`): **evolua** em vez de mover tudo:
- `routes/` vira a camada de view (só registro de rotas) — mantenha o nome do diretório se for o idioma do projeto;
- extraia a lógica das rotas para `controllers/` e `services/`;
- reaproveite e corrija o que já existe (`models/*.py`, `services/*.py`, `utils/*.py` não utilizados) em vez de duplicar;
- adicione `config/` e `middlewares/error_handler.py`.

### Node.js / Express

```
<projeto>/
├── src/
│   ├── app.js                  # composition root: cria express app, injeta dependências, listen
│   ├── config/
│   │   └── index.js            # lê process.env
│   ├── database/
│   │   ├── connection.js       # abre o banco; helpers promisificados (run/get/all)
│   │   └── schema.js           # DDL + seed
│   ├── models/                 # repositórios por entidade (SQL parametrizado)
│   │   └── <entidade>.model.js
│   ├── services/               # regras de negócio, transações
│   │   └── <dominio>.service.js
│   ├── controllers/
│   │   └── <dominio>.controller.js
│   ├── routes/                 # camada de view: express.Router por domínio
│   │   └── index.js
│   ├── middlewares/
│   │   ├── errorHandler.js
│   │   └── auth.js
│   └── utils/
├── .env.example
└── package.json                # "start" continua apontando para src/app.js
```

Converta callbacks para `async/await` (promisifique o driver) para permitir transações e tratamento de erro linear. Express 4 não captura rejeições de handlers `async`: use um wrapper `asyncHandler` ou `try/catch → next(err)`.

### Outras stacks (referência rápida)

| Stack | Models | Controllers | Views/Rotas | Config |
|---|---|---|---|---|
| FastAPI | `models/`, `repositories/` | `services/` + funções de rota finas | `routers/` + schemas Pydantic | `pydantic-settings` |
| Django | `models.py` por app | `views.py` (são controllers) | `urls.py` + serializers DRF | `settings.py` + env |
| Spring Boot | `@Entity` + `Repository` | `@Service` | `@RestController` + DTOs | `application.yml` + env |
| Go (net/http, Gin) | `internal/model`, `internal/repository` | `internal/service` | `internal/handler` + router | `internal/config` |

## Checklist de conformidade (usado na validação)

- [ ] Estrutura de diretórios segue MVC (models, views/routes, controllers) + config + middlewares
- [ ] Configuração extraída para módulo de config; nenhum segredo literal
- [ ] Models abstraem os dados; todas as queries parametrizadas
- [ ] Views/Routes apenas registram rotas e serializam
- [ ] Controllers concentram o fluxo HTTP, sem SQL e sem regra de negócio pesada
- [ ] Error handling centralizado
- [ ] Entry point claro (composition root) e comando original de execução funcionando
- [ ] Aplicação inicia sem erros e endpoints originais respondem como na linha de base
