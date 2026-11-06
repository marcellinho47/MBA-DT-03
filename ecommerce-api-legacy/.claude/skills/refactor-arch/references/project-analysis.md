# Heurísticas de Análise de Projeto (Fase 1)

Objetivo: identificar **com evidência** a stack, o domínio e a arquitetura atual. Cada afirmação do resumo da Fase 1 deve poder ser apontada para um arquivo.

## 1. Linguagem — arquivos de manifesto

Procure na raiz do projeto (e um nível abaixo). O manifesto define a linguagem e, frequentemente, o framework.

| Manifesto | Linguagem | Onde ler a versão |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `setup.cfg` | Python | `requires-python`, `python_requires`, `.python-version`, `runtime.txt` |
| `package.json` | JavaScript / TypeScript (TS se houver `tsconfig.json` ou `typescript` nas deps) | `engines.node`, `.nvmrc`, `.node-version` |
| `go.mod` | Go | diretiva `go` |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin | `maven.compiler.source`, `sourceCompatibility`, `jvmToolchain` |
| `Gemfile` | Ruby | `ruby '...'`, `.ruby-version` |
| `composer.json` | PHP | `require.php` |
| `*.csproj`, `*.sln` | C# | `<TargetFramework>` |
| `Cargo.toml` | Rust | `edition`, `rust-version` |

Sem manifesto: decida pela extensão predominante dos arquivos-fonte.

Também registre a **versão do runtime instalado** (`python --version`, `node --version`, etc.) — ela importa para detectar APIs deprecated (AP-15).

## 2. Framework

Confirme pelo manifesto **e** pelo uso no código.

| Linguagem | Framework | Sinais no código |
|---|---|---|
| Python | Flask | `from flask import Flask`, `Flask(__name__)`, `@app.route`, `Blueprint(`, `add_url_rule(` |
| Python | FastAPI | `from fastapi import FastAPI`, `APIRouter`, `@app.get(` |
| Python | Django | `manage.py`, `settings.py`, `urls.py` com `urlpatterns`, `INSTALLED_APPS` |
| JS/TS | Express | `require('express')` / `import express`, `express()`, `app.get(`, `express.Router()` |
| JS/TS | NestJS | `@nestjs/core`, `@Controller(`, `@Module(` |
| JS/TS | Fastify / Koa / Hapi | `fastify(`, `new Koa()`, `Hapi.server(` |
| Java | Spring Boot | `@SpringBootApplication`, `@RestController`, `@GetMapping` |
| Go | Gin / Echo / net/http | `gin.Default()`, `echo.New()`, `http.HandleFunc` |
| Ruby | Rails / Sinatra | `config/routes.rb`, `ApplicationController`; `require 'sinatra'` |
| PHP | Laravel / Slim | `artisan`, `Route::get(`; `$app->get(` |

Versão do framework: use a do manifesto (`flask==3.1.1`, `"express": "^4.18.2"`) ou do lockfile, se presente.

## 3. Banco de dados e forma de acesso

| Sinal | Banco | Forma de acesso |
|---|---|---|
| `import sqlite3`, `sqlite3.connect(` | SQLite | SQL cru (driver) |
| `require('sqlite3')`, `new sqlite3.Database(` | SQLite | SQL cru (driver, API de callbacks) |
| `':memory:'` no connect | SQLite em memória | dados não persistem entre execuções |
| `flask_sqlalchemy`, `SQLAlchemy(`, `db.Model` | o da URI (`SQLALCHEMY_DATABASE_URI`) | ORM |
| `psycopg2`, `pg`, `mysql`, `mysql2`, `pymongo`, `mongoose` | PostgreSQL / MySQL / MongoDB | driver ou ODM |
| `sequelize`, `typeorm`, `prisma`, `knex`, `peewee`, `django.db` | o da config | ORM / query builder |

Liste as **tabelas/entidades**: `CREATE TABLE`, classes de modelo (`class X(db.Model)`, `@Entity`, schemas do mongoose), migrations.

## 4. Domínio da aplicação

Deduza a partir dos nomes de **tabelas/entidades** e **rotas**, e confirme com o README e os dados de seed. Descreva em uma linha com as entidades principais. Exemplos:

- `produtos`, `pedidos`, `itens_pedido`, `usuarios` + rotas `/produtos`, `/pedidos` → "E-commerce API (produtos, pedidos, usuários)".
- `courses`, `enrollments`, `payments` + `/api/checkout` → "LMS com checkout (cursos, matrículas, pagamentos)".
- `tasks`, `categories`, `users` + `/reports` → "Task Manager (tasks, categorias, usuários, relatórios)".

Mantenha os nomes no idioma original do código.

## 5. Inventário de endpoints

Liste **todos** os endpoints: método, caminho, handler e `arquivo:linha`. Fontes:

- Flask: `@app.route(...)`, `@bp.route(...)`, `app.add_url_rule(...)` — considere o `url_prefix` dos blueprints e o `methods=` (padrão `GET`).
- Express: `app.<verbo>(...)`, `router.<verbo>(...)` — considere o prefixo de `app.use('/prefix', router)`.
- Outros: anotações/decorators de rota equivalentes, arquivos de rotas.

Também anote arquivos de exemplo de requisição (`*.http`, coleções Postman, `curl` no README): eles indicam payloads válidos para a validação da Fase 3.

Esse inventário é o **contrato** que a Fase 3 deve preservar.

## 6. Classificação da arquitetura atual

Escolha **uma** classificação e justifique em uma frase:

| Classificação | Critério |
|---|---|
| **Monolítica — sem separação de camadas** | Poucos arquivos; acesso a dados, regra de negócio e HTTP misturados no mesmo arquivo/classe; ou um arquivo/classe concentra várias responsabilidades (God Class). Nomes como `models.py`/`controllers.py` não bastam: verifique se o conteúdo respeita a camada. |
| **Parcialmente em camadas** | Existem diretórios/módulos por camada (`models/`, `routes/`, `services/`...), mas há vazamento: rotas com regra de negócio ou consultas, services/utils não utilizados, lógica duplicada entre camadas. |
| **Em camadas (MVC / layered)** | Rotas só roteiam, controllers orquestram, regras em models/services, acesso a dados isolado, config centralizada, tratamento de erro central. |

Sinais rápidos de vazamento de camada:
- Handler HTTP contendo SQL/consultas ORM e cálculos de negócio no mesmo corpo.
- Módulo "model" que formata resposta HTTP ou envia notificação.
- Arquivos em `services/` ou `utils/` que nenhum outro arquivo importa.
- A mesma regra de negócio implementada em mais de um handler.

## 7. Contagem de arquivos e linhas

Conte apenas arquivos-fonte da aplicação (excluindo os diretórios listados na Fase 1 do `SKILL.md`, arquivos de teste de requisição e lockfiles). Exemplos:

```bash
# Python
find . -name "*.py" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/.claude/*" | xargs wc -l
# JavaScript/TypeScript
find . \( -name "*.js" -o -name "*.ts" \) -not -path "*/node_modules/*" -not -path "*/.claude/*" | xargs wc -l
```

Em Windows sem bash, use o equivalente em PowerShell (`Get-ChildItem -Recurse -Include *.py | Where-Object { $_.FullName -notmatch '\\(\.venv|node_modules|\.claude)\\' } | Get-Content | Measure-Object -Line`).

## 8. Entry point e comando de execução

Procure, nesta ordem: README do projeto (seção "como rodar"), `scripts.start` do `package.json`, `if __name__ == "__main__":`, `Procfile`, `Dockerfile` (`CMD`/`ENTRYPOINT`), `main` do `package.json`. Registre também scripts auxiliares obrigatórios (ex.: `python seed.py` antes do primeiro boot) e a porta padrão.
