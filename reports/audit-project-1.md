================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.15 + Flask 3.1.1 (SQLite / SQL cru via sqlite3)
Files:   4 analyzed | ~780 lines of code
Date:    2026-11-06

## Summary
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 5

API monolítica sem separação real de camadas: `models.py` e `controllers.py` são God Files que misturam todos os domínios, e `app.py` contém handlers com SQL inline. Os riscos mais graves são SQL Injection generalizado (inclusive no login), senhas em texto puro expostas nas respostas, segredo exposto via `/health` e dois endpoints administrativos sem proteção que apagam o banco ou executam SQL arbitrário.

## Findings

### F-01 [CRITICAL] Credenciais e segredos hardcoded (AP-01)
File: app.py:7; controllers.py:289
Description: A `SECRET_KEY` do Flask está fixa no código e o mesmo valor é repetido literalmente na resposta do health check.
Evidence:
```python
app.config["SECRET_KEY"] = "minha-chave-****"
"secret_key": "minha-chave-****"
```
Impact: Qualquer pessoa com acesso ao repositório (ou a `/health`) conhece a chave usada para assinar sessões/cookies; impossível trocar o segredo por ambiente sem alterar o código.
Recommendation: Ler `SECRET_KEY` (e demais configurações) de variáveis de ambiente em um módulo `config.py`, com default apenas para desenvolvimento, e criar `.env.example` — Playbook PB-02

### F-02 [CRITICAL] SQL Injection (AP-02)
File: models.py:28; models.py:47-50; models.py:57-61; models.py:68; models.py:92; models.py:109-111; models.py:126-129; models.py:140; models.py:148-151; models.py:155; models.py:157-161; models.py:163-166; models.py:174; models.py:188; models.py:192; models.py:220; models.py:224; models.py:279-281; models.py:289-297
Description: Praticamente todas as queries são montadas por concatenação de strings. Valores vindos do request entram direto no SQL: email/senha no login, nome/descrição/categoria em criar/atualizar produto, nome/email/senha em criar usuário, `produto_id`/`quantidade` dos itens do pedido (JSON sem validação de tipo) e `q`/`categoria` na busca.
Evidence:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
```
Impact: Bypass de autenticação (`' OR '1'='1' --` em `/login`), leitura de toda a tabela `usuarios` via `/produtos/busca?q=`, alteração/remoção arbitrária de dados; nomes com apóstrofo legítimo (ex.: "Monitor 27''") quebram as queries.
Recommendation: Usar queries parametrizadas (`?`) em todas as consultas, inclusive no `WHERE` dinâmico da busca, isoladas em repositórios — Playbook PB-01

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: database.py:75-83; models.py:126-129; models.py:109-111
Description: As senhas são gravadas em texto puro no seed e em `criar_usuario`, e o login compara a senha diretamente na cláusula `WHERE` do SQL.
Evidence:
```python
("Admin", "admin@loja.com", "admin123", "admin"),
"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
```
Impact: Qualquer vazamento do banco (ou do endpoint `/admin/query`, ou de F-04) expõe as senhas reais de todos os usuários, que costumam ser reutilizadas em outros serviços.
Recommendation: Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (já instalado com o Flask), buscar o usuário por email e verificar o hash em código; migrar as senhas legadas em texto puro na inicialização — Playbook PB-03

### F-04 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83; models.py:99; controllers.py:284-289; controllers.py:161; controllers.py:179; controllers.py:182
Description: Os serializers de usuário incluem o campo `senha`, que é retornado por `GET /usuarios` e `GET /usuarios/<id>`. O `GET /health` devolve `secret_key`, `debug`, `db_path` e `ambiente`. Emails (PII) são escritos no stdout a cada login/cadastro.
Evidence:
```python
"senha": row["senha"],
"debug": True,
"secret_key": "minha-chave-****"
```
Impact: Qualquer cliente anônimo obtém as senhas (em texto puro, ver F-03) de todos os usuários, incluindo o admin, e a chave secreta da aplicação.
Recommendation: Serializar usuários sem `senha`; remover segredos e detalhes de configuração da resposta de `/health`; não registrar PII em logs — Playbook PB-04

### F-05 [CRITICAL] God Class / God File (AP-05)
File: models.py:1-314; controllers.py:1-292; app.py:1-88; database.py:1-86
Description: `models.py` concentra acesso a dados **e** regras de negócio de quatro domínios (produtos, usuários, pedidos, relatórios). `controllers.py` concentra os handlers de todos os domínios, com validação, efeitos colaterais e SQL (`health_check`). `app.py` mistura configuração, registro de rotas e handlers com SQL inline. `database.py` mistura conexão, DDL e seed.
Evidence:
```python
def criar_pedido(usuario_id, itens):      # models.py: validação de estoque + cálculo + 3 tabelas
def relatorio_vendas():                   # models.py: SQL + faixas de desconto
@app.route("/admin/query", ...)           # app.py: rota com SQL
```
Impact: Qualquer mudança em um domínio toca arquivos compartilhados por todos; impossível testar regras de negócio sem banco real; alto risco de regressão.
Recommendation: Separar em pacotes por camada e domínio (config, database, repositories/models, services, controllers, routes/blueprints) com `app.py` como composition root fino — Playbook PB-05

### F-06 [CRITICAL] Endpoint perigoso sem proteção (AP-06)
File: app.py:47-57; app.py:59-78
Description: `POST /admin/reset-db` apaga todas as tabelas (`DELETE` sem `WHERE`) e `POST /admin/query` executa qualquer SQL enviado no corpo — ambos sem autenticação nem autorização.
Evidence:
```python
query = dados.get("sql", "")
cursor.execute(query)
```
Impact: Qualquer cliente na rede pode apagar todo o banco, ler senhas, criar administradores ou executar `DROP TABLE` com uma única requisição.
Recommendation: Remover o endpoint de SQL arbitrário; proteger o reset (desabilitado por padrão, habilitado só por configuração de desenvolvimento e exigindo token de admin) — Playbook PB-14

### F-07 [HIGH] Regra de negócio no controller/rota (Fat Controller) (AP-07)
File: controllers.py:24-62; controllers.py:203-210; controllers.py:242-250; controllers.py:264-290; models.py:137-146; models.py:256-262; app.py:47-78
Description: Os controllers validam regras de domínio (categorias válidas, limites de nome, status permitidos), orquestram notificações (email/SMS/push simulados com `print`) e executam SQL (`health_check`, rotas admin). Na direção oposta, a camada de dados decide regras de negócio: verificação de estoque e cálculo de total em `criar_pedido`, e faixas de desconto em `relatorio_vendas`.
Evidence:
```python
print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + ...)   # controller
if faturamento > 10000: desconto = faturamento * 0.1                     # "model" com SQL
```
Impact: Regras espalhadas entre camadas, não reutilizáveis nem testáveis isoladamente; efeitos colaterais acoplados ao HTTP.
Recommendation: Mover regras para services de domínio (`ProdutoService`, `PedidoService`, `RelatorioService`), notificações para um serviço próprio, e deixar controllers apenas traduzindo HTTP ↔ service — Playbook PB-06

### F-08 [HIGH] Estado global mutável / conexão singleton implícita (AP-08)
File: database.py:4-11
Description: Uma única conexão SQLite global (`global db_connection`) é compartilhada por todas as requisições e threads, com `check_same_thread=False` para silenciar a proteção do driver.
Evidence:
```python
global db_connection
db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Impact: Requisições concorrentes compartilham o mesmo estado transacional: uma escrita interrompida em uma requisição pode ser commitada (ou corrompida) por outra; condições de corrida sob carga.
Recommendation: Conexão por requisição via `flask.g` com fechamento em `teardown_appcontext` — Playbook PB-07

### F-09 [HIGH] Autenticação/autorização ausente ou falsa (AP-09)
File: controllers.py:176-180; app.py:11-30
Description: O login não emite nenhuma credencial (token/sessão) — apenas devolve os dados do usuário. Nenhuma rota verifica identidade ou papel: criação/edição/remoção de produtos, listagem de todos os usuários, listagem de todos os pedidos, alteração de status de pedido e relatório de vendas são públicos.
Evidence:
```python
return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
```
Impact: O campo `tipo` (admin/cliente) não tem efeito; qualquer cliente anônimo executa operações administrativas.
Recommendation: Emitir token assinado no login (`itsdangerous`, já dependência do Flask) e aplicar decorators `require_auth`/`require_admin` nas rotas administrativas, preservando o contrato das rotas públicas — Playbook PB-14

### F-10 [HIGH] Escrita multi-etapa sem transação (AP-10)
File: models.py:133-169
Description: `criar_pedido` lê estoque, insere o pedido, insere os itens e decrementa o estoque em passos independentes, sem transação explícita nem `rollback`. A verificação de estoque (check) e o decremento (act) não são atômicos, e itens repetidos do mesmo produto são verificados isoladamente.
Evidence:
```python
cursor.execute("INSERT INTO pedidos ...")
...
cursor.execute("UPDATE produtos SET estoque = estoque - " + str(item["quantidade"]) + ...)
db.commit()
```
Impact: Uma exceção no meio deixa escritas pendentes na conexão global (F-08), que serão commitadas pela próxima requisição — pedidos sem itens ou estoque decrementado sem pedido; vendas acima do estoque sob concorrência.
Recommendation: Executar a operação em uma unidade transacional (`with conn:` / `BEGIN … COMMIT/ROLLBACK`) no service, com decremento condicional (`WHERE estoque >= ?`) — Playbook PB-11

### F-11 [HIGH] Acoplamento rígido a infraestrutura (AP-11)
File: models.py:5; models.py:25; models.py:44; models.py:55; models.py:66; models.py:73; models.py:90; models.py:106; models.py:123; models.py:134; models.py:172; models.py:204; models.py:236; models.py:276; models.py:286; controllers.py:266; app.py:49; app.py:66; database.py:5
Description: Toda função de dados/negócio chama `get_db()` diretamente e o caminho do banco é fixo (`db_path = "loja.db"`); não há como injetar outra conexão ou banco.
Evidence:
```python
db_path = "loja.db"
def get_todos_produtos():
    db = get_db()
```
Impact: Impossível testar com banco em memória ou trocar de banco por configuração; regras de negócio presas ao SQLite.
Recommendation: Repositórios que recebem a conexão; services que recebem repositórios; caminho do banco via configuração (`DATABASE_PATH`) — Playbook PB-07

### F-12 [MEDIUM] Consultas N+1 (AP-12)
File: models.py:186-199; models.py:219-231; models.py:139-141; models.py:154-156
Description: Para cada pedido é feita uma consulta de itens e, para cada item, uma consulta do nome do produto (`cursor2`/`cursor3` em loops aninhados). Em `criar_pedido`, cada produto é consultado duas vezes (validação e novamente para obter o preço).
Evidence:
```python
for row in rows:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Impact: `GET /pedidos` executa 1 + P + I consultas; o tempo de resposta cresce linearmente com o histórico de pedidos.
Recommendation: Uma consulta com `JOIN` entre `itens_pedido` e `produtos` filtrada pelos ids dos pedidos (`IN (...)` parametrizado) e agrupamento em memória; reutilizar os produtos já carregados em `criar_pedido` — Playbook PB-08

### F-13 [MEDIUM] Tratamento de erro genérico que vaza detalhes (AP-13)
File: controllers.py:10-12; controllers.py:21-22; controllers.py:60-62; controllers.py:95-96; controllers.py:108-109; controllers.py:125-126; controllers.py:133-134; controllers.py:143-144; controllers.py:164-165; controllers.py:185-186; controllers.py:218-220; controllers.py:226-227; controllers.py:234-235; controllers.py:254-255; controllers.py:261-262; controllers.py:291-292; app.py:77-78
Description: Todos os handlers envolvem o corpo em `try/except Exception` e devolvem `str(e)` ao cliente; não existe error handler central.
Evidence:
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
Impact: Mensagens internas (SQL, nomes de tabelas, tipos Python) vazam ao cliente e auxiliam a exploração de F-02; erros de entrada do cliente viram 500; código repetido 17 vezes.
Recommendation: Exceções de domínio (`ValidationError`, `NotFoundError`) mapeadas em `@app.errorhandler` central, com mensagem genérica e log do detalhe para erros inesperados — Playbook PB-09

### F-14 [MEDIUM] Validação de entrada ausente ou duplicada (AP-14)
File: controllers.py:169-170; controllers.py:239-240; controllers.py:43-50; controllers.py:72-90; controllers.py:118-121; controllers.py:153-160; controllers.py:195-201; models.py:144; models.py:275-283
Description: `login` e `atualizar_status_pedido` usam `dados.get` sem checar se o JSON é `None` (500). `preco`/`estoque` são comparados sem checagem de tipo (string → `TypeError` 500). A validação de produto é copiada entre criar e atualizar, mas o update omite limites de nome e categoria válida (inconsistência). `preco_min`/`preco_max` inválidos geram 500. Itens do pedido não são validados (chaves ausentes → `KeyError`; `quantidade` negativa **aumenta** o estoque). Email sem validação de formato e duplicável. Alterar status de pedido inexistente retorna 200.
Evidence:
```python
dados = request.get_json()
email = dados.get("email", "")      # AttributeError se corpo vazio
if preco < 0:                       # TypeError se preco = "10"
```
Impact: Erros do cliente retornam 500; dados inconsistentes (estoque inflado, produtos com categoria inválida via PUT, usuários com email duplicado).
Recommendation: Validadores centralizados por entidade usados por create e update, checagem de tipo/faixa, validação dos itens do pedido e 404 para pedido inexistente — Playbook PB-10

### F-15 [MEDIUM] Configuração insegura de ambiente (AP-16)
File: app.py:8; app.py:9; app.py:88
Description: Debug ligado fixo no código e no `app.run`, servidor escutando em `0.0.0.0`, e CORS liberado para qualquer origem.
Evidence:
```python
app.config["DEBUG"] = True
CORS(app)
app.run(host="0.0.0.0", port=5000, debug=True)
```
Impact: O debugger interativo do Werkzeug exposto na rede permite execução remota de código; qualquer site pode chamar a API a partir do navegador da vítima.
Recommendation: `DEBUG`, `HOST`, `PORT` e `CORS_ORIGINS` vindos de variáveis de ambiente com defaults seguros (debug desligado, host `127.0.0.1`) — Playbook PB-02

### F-16 [MEDIUM] Lógica duplicada (copy-paste) (AP-17)
File: models.py:12-21; models.py:31-40; models.py:304-313; models.py:79-86; models.py:95-102; models.py:171-201; models.py:203-233; controllers.py:28-50; controllers.py:72-90
Description: O mapeamento row → dict de produto aparece três vezes e o de usuário duas; `get_pedidos_usuario` e `get_todos_pedidos` são idênticas exceto pelo `WHERE`; o bloco de validação de produto está duplicado entre criar e atualizar.
Evidence:
```python
def get_pedidos_usuario(usuario_id): ...   # 31 linhas
def get_todos_pedidos(): ...               # as mesmas 31 linhas, sem WHERE
```
Impact: Correções precisam ser replicadas manualmente e já divergiram (validação de update incompleta, ver F-14).
Recommendation: Serializers únicos por entidade, uma função de listagem de pedidos com filtro opcional e validador compartilhado — Playbook PB-06 / PB-10

### F-17 [LOW] Magic numbers e strings (AP-18)
File: models.py:257-262; controllers.py:47-50; controllers.py:52; controllers.py:242; app.py:36; controllers.py:285; app.py:88
Description: Faixas e percentuais de desconto (`10000`, `0.1`, `5000`, `0.05`, `1000`, `0.02`), limites de nome (2/200), lista de categorias, lista de status de pedido, versão `"1.0.0"` repetida e porta `5000` inline.
Evidence:
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
```
Impact: Regras de negócio difíceis de localizar e alterar com segurança; valores repetidos divergem.
Recommendation: Constantes nomeadas no módulo de domínio (`CATEGORIAS_VALIDAS`, `STATUS_PEDIDO`, `FAIXAS_DESCONTO`) e versão/porta em configuração — Playbook PB-13

### F-18 [LOW] Nomenclatura ruim (AP-19)
File: controllers.py:14; controllers.py:56; controllers.py:64; controllers.py:98; controllers.py:136; controllers.py:160; models.py:24; models.py:54; models.py:65; models.py:89; models.py:187; models.py:191; models.py:219; models.py:223
Description: Parâmetros e variáveis chamados `id` sombreiam o builtin; `cursor2`/`cursor3` não indicam o que consultam.
Evidence:
```python
def buscar_produto(id):
cursor3 = db.cursor()
```
Impact: Legibilidade reduzida e risco de bugs ao precisar do builtin `id()`.
Recommendation: Renomear para `produto_id`, `usuario_id` (mantendo o nome do parâmetro da rota onde necessário) e eliminar os cursores extras com o JOIN de F-12 — Playbook PB-13

### F-19 [LOW] `print` como mecanismo de log (AP-20)
File: app.py:56; app.py:83-86; controllers.py:8; controllers.py:11; controllers.py:57; controllers.py:61; controllers.py:106; controllers.py:161; controllers.py:179; controllers.py:182; controllers.py:208-210; controllers.py:219; controllers.py:248; controllers.py:250
Description: 19 chamadas a `print` usadas como log e como "envio" de notificações.
Evidence:
```python
print("ERRO CRITICO ao criar pedido: " + str(e))
```
Impact: Sem níveis, sem timestamp, sem possibilidade de redirecionar/filtrar; notificações simuladas indistinguíveis de logs.
Recommendation: Usar `logging` (logger por módulo, nível configurável) e um `NotificationService` para as notificações — Playbook PB-15

### F-20 [LOW] Código morto e imports não utilizados (AP-21)
File: database.py:2; models.py:2; controllers.py:268
Description: `import os` e `import sqlite3` (em `models.py`) nunca usados; `cursor.execute("SELECT 1")` no health check é imediatamente sobrescrito pela consulta seguinte e não tem efeito.
Evidence:
```python
import os
cursor.execute("SELECT 1")
```
Impact: Ruído e falsa impressão de dependências.
Recommendation: Remover imports e instruções sem efeito — Playbook PB-13

### F-21 [LOW] Construções não idiomáticas / verbosas (AP-22)
File: controllers.py:200; models.py:9-22; models.py:63; models.py:70; models.py:283; controllers.py:8
Description: `if not itens or len(itens) == 0` (redundante); montagem manual de dicts campo a campo em vez de `dict(row)`; funções de dados retornando `True` fixo nunca usado; concatenação de strings com `str()` em vez de f-strings.
Evidence:
```python
if not itens or len(itens) == 0:
print("Listando " + str(len(produtos)) + " produtos")
```
Impact: Código mais longo e propenso a erro do que o necessário.
Recommendation: Expressões idiomáticas, f-strings, serialização a partir de `sqlite3.Row` — Playbook PB-13

## Deprecated APIs
None detected (checked against Python 3.15.2, Flask 3.1.1, Werkzeug 3.1.9, flask-cors 5.0.1; `python -W error::DeprecationWarning -c "import app"` sem avisos; nenhum uso de `datetime.utcnow`, `before_first_request`, `flask.__version__`, `JSONEncoder` ou adaptadores de datetime do sqlite3).

| API | Location | Replacement |
|-----|----------|-------------|
| — | — | — |

## Refactoring Plan Preview
1. **config.py + .env.example** — segredos, debug, host/porta, CORS e caminho do banco por ambiente → F-01, F-15, F-11 (parcial).
2. **database.py** — conexão por requisição (`flask.g` + teardown), DDL/seed separados, migração de senhas legadas → F-08, F-03 (dados legados), F-20.
3. **repositories/** (produto, usuario, pedido) — SQL 100% parametrizado, serializers únicos, JOIN no lugar de N+1 → F-02, F-12, F-16, F-18.
4. **services/** (produto, usuario/auth, pedido, relatorio, notificacao) — regras de negócio, validação, transação no pedido, hash de senha, token → F-03, F-07, F-10, F-14, F-17, F-19.
5. **controllers/ + routes (Blueprints)** — handlers finos por domínio, decorators de auth, errorhandler central, usuários sem `senha`, `/health` sem segredos → F-04, F-05, F-09, F-13, F-21.
6. **Admin** — remover `/admin/query`; `/admin/reset-db` protegido por admin e desabilitado por padrão → F-06.
7. **app.py** — composition root fino (`create_app()`), mantendo `python app.py` → F-05.

================================
Total: 21 findings
================================
