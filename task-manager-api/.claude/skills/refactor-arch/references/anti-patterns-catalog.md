# Catálogo de Anti-Patterns (Fase 2)

Cada entrada tem: **ID**, **severidade padrão**, **o que é**, **sinais de detecção** (buscas por padrão + o que confirmar lendo o código), **falsos positivos comuns** e a **transformação do playbook** que resolve.

As buscas usam sintaxe de regex do ripgrep/grep -E. Elas são **indícios**: todo finding precisa ser confirmado lendo o trecho e deve citar `arquivo:linha` exatos.

## Escala de severidade

| Severidade | Critério |
|---|---|
| **CRITICAL** | Falha grave de segurança ou de arquitetura: expõe dados sensíveis, permite execução/injeção arbitrária, ou viola completamente a separação de responsabilidades (God Class). |
| **HIGH** | Forte violação de MVC/SOLID que dificulta muito manutenção e testes: regra de negócio no controller/rota, acoplamento sem injeção de dependência, estado global mutável, ausência de controle de acesso, escrita multi-etapa sem transação. |
| **MEDIUM** | Padronização, duplicação, performance moderada: N+1, validação ausente/duplicada, tratamento de erro genérico, APIs deprecated, configuração insegura de ambiente. |
| **LOW** | Legibilidade: magic numbers, nomes ruins, `print` como log, código morto, construções não idiomáticas. |

## Índice

| ID | Anti-pattern | Severidade | Playbook |
|---|---|---|---|
| AP-01 | Credenciais e segredos hardcoded | CRITICAL | PB-02 |
| AP-02 | SQL Injection (query montada por concatenação/interpolação) | CRITICAL | PB-01 |
| AP-03 | Armazenamento inseguro de senha | CRITICAL | PB-03 |
| AP-04 | Exposição de dados sensíveis (respostas e logs) | CRITICAL | PB-04 |
| AP-05 | God Class / God File | CRITICAL | PB-05 |
| AP-06 | Endpoint perigoso sem proteção | CRITICAL | PB-14 |
| AP-07 | Regra de negócio no controller/rota (Fat Controller) | HIGH | PB-06 |
| AP-08 | Estado global mutável / conexão singleton implícita | HIGH | PB-07 |
| AP-09 | Autenticação/autorização ausente ou falsa | HIGH | PB-14 |
| AP-10 | Escrita multi-etapa sem transação / callback hell | HIGH | PB-11 |
| AP-11 | Acoplamento rígido a infraestrutura (sem injeção de dependência) | HIGH | PB-07 |
| AP-12 | Consultas N+1 | MEDIUM | PB-08 |
| AP-13 | Tratamento de erro genérico, silencioso ou que vaza detalhes | MEDIUM | PB-09 |
| AP-14 | Validação de entrada ausente ou duplicada | MEDIUM | PB-10 |
| AP-15 | Uso de APIs deprecated | MEDIUM | PB-12 |
| AP-16 | Configuração insegura de ambiente (debug, CORS aberto) | MEDIUM | PB-02 |
| AP-17 | Lógica duplicada (copy-paste) | MEDIUM | PB-06 / PB-10 |
| AP-18 | Magic numbers e strings | LOW | PB-13 |
| AP-19 | Nomenclatura ruim | LOW | PB-13 |
| AP-20 | `print`/`console.log` como mecanismo de log | LOW | PB-15 |
| AP-21 | Código morto e imports não utilizados | LOW | PB-13 |
| AP-22 | Construções não idiomáticas / verbosas | LOW | PB-13 |

---

## CRITICAL

### AP-01 — Credenciais e segredos hardcoded
**O que é:** chaves, senhas, tokens, connection strings com senha ou chaves de API literais no código-fonte.

**Sinais:**
```
(?i)(secret|passw(or)?d|pwd|pass|api[_-]?key|token|private[_-]?key|credential)\w*\s*[:=]\s*['"][^'"]{3,}['"]
(?i)SECRET_KEY['"]?\]?\s*=\s*['"]
(sk|pk|rk)_(live|test)_[0-9A-Za-z]+
(?i)(smtp|mail|email)_(user|pass|password)\s*[:=]
(postgres|mysql|mongodb)(\+\w+)?://[^:\s]+:[^@\s]+@
```
Confirme que o valor é usado como segredo real (não é um placeholder lido de env com fallback de desenvolvimento explícito).

**Falsos positivos:** `os.environ.get("SECRET_KEY")` sem default real; valores em `.env.example`; senhas de **dados de seed/fixture** (essas entram em AP-03 se forem gravadas sem hash).

### AP-02 — SQL Injection
**O que é:** SQL montado concatenando ou interpolando valores vindos de fora (request, parâmetros de função).

**Sinais:**
```
(execute|executemany|query|run|get|all|raw)\s*\(\s*f?["'].*(SELECT|INSERT|UPDATE|DELETE).*["']\s*\+
["'](SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*\+\s*\w+
f["'](SELECT|INSERT|UPDATE|DELETE)[^"']*\{
`(SELECT|INSERT|UPDATE|DELETE)[^`]*\$\{
\.format\(.*\)\s*\)?\s*$     (em linhas com SQL)
% \(?\w+     (formatação % em string SQL)
```
Confirme que a parte variável pode vir do usuário (rastreie até o handler). Construir `WHERE` dinamicamente é aceitável **se** os valores forem passados como parâmetros (`?`, `%s`, `:name`, `$1`).

**Falsos positivos:** queries 100% literais; concatenação apenas de fragmentos fixos com valores parametrizados.

### AP-03 — Armazenamento inseguro de senha
**O que é:** senha gravada em texto puro, com hash rápido/quebrado (MD5, SHA-1, SHA-256 sem salt/KDF) ou com "criptografia" caseira; comparação de senha direto no SQL.

**Sinais:**
```
hashlib\.(md5|sha1|sha256)\(
createHash\(['"](md5|sha1|sha256)['"]\)
(?i)(senha|password|pass|pwd)\s*=\s*['"]     (em INSERT/seed)
(?i)WHERE .*(senha|password|pass)\s*=
Buffer\.from\(.*\)\.toString\(['"]base64['"]\)     (em funções de "hash")
(?i)function\s+\w*(crypt|hash)\w*\s*\(     (implementação própria)
```
Confirme o fluxo completo: criação de usuário → armazenamento → login.

**Falsos positivos:** uso de `bcrypt`, `argon2`, `scrypt`, `pbkdf2`, `werkzeug.security.generate_password_hash`.

### AP-04 — Exposição de dados sensíveis
**O que é:** senha/hash, segredos de configuração, dados de cartão ou tokens retornados em respostas HTTP ou escritos em logs.

**Sinais:**
```
["'](senha|password|pass|pwd|secret_key|token)["']\s*:     (em dicts/objetos serializados)
(?i)(print|console\.log|logger\.\w+)\(.*(card|cartao|cc|senha|password|key|token)
SELECT \*     (em entidades com coluna de senha, quando o resultado vai direto para a resposta)
```
Confirme lendo o serializer (`to_dict`, `toJSON`, dict literal) e quais endpoints o usam; liste os endpoints afetados.

### AP-05 — God Class / God File
**O que é:** um arquivo ou classe concentra várias responsabilidades de camadas diferentes (conexão/DDL, consultas, regras de negócio, roteamento HTTP, formatação) ou vários domínios.

**Sinais:**
- Arquivo com > ~250 linhas **ou** classe com > ~10 métodos cobrindo domínios diferentes.
- O mesmo arquivo contém: abertura de conexão/`CREATE TABLE` **e** definição de rotas; ou consultas **e** regras de negócio **e** formatação de resposta.
- Nomes genéricos: `Manager`, `AppManager`, `Utils`, `Helper`, `Main`, `Service` único para tudo.
- Funções de domínios distintos no mesmo módulo (produtos, usuários, pedidos, relatórios...).

**Falsos positivos:** arquivo grande mas coeso (um único domínio, uma única camada).

### AP-06 — Endpoint perigoso sem proteção
**O que é:** endpoint que executa código/SQL arbitrário, apaga/reinicia dados, ou expõe operações administrativas sem autenticação/autorização.

**Sinais:**
```
(?i)route\(.*/(admin|debug|internal|reset|query|exec|eval|shell)
cursor\.execute\(\s*(query|sql|dados|data|body)\b
(?i)DELETE FROM \w+["']\s*\)     (DELETE sem WHERE)
\beval\(|\bexec\(|child_process|subprocess
```
Confirme que não há verificação de identidade/permissão antes da operação.

---

## HIGH

### AP-07 — Regra de negócio no controller/rota (Fat Controller)
**O que é:** handlers HTTP (ou funções de acesso a dados) contendo cálculos, regras de domínio, orquestração de efeitos colaterais (notificação, estoque, pagamento) — em vez de delegar a um model/service.

**Sinais:**
- Handler com mais de ~30 linhas, vários `if` de regra de negócio, cálculos (`total +=`, percentuais, descontos), ou chamadas a mais de um repositório/tabela.
- Efeitos colaterais no handler: `print("ENVIANDO EMAIL")`, envio SMTP, atualização de estoque.
- Função de "model" que decide regra de negócio (faixas de desconto, aprovação de pagamento) misturada com SQL.
- Regra existente no model (ex.: `is_overdue()`) reimplementada dentro das rotas.
- **Ação anunciada mas não executada:** mensagens de log/`print`, comentários, `TODO` ou textos de resposta que descrevem um efeito de negócio que o código **não realiza** (ex.: `print("Pedido cancelado. Devolver estoque.")` sem nenhuma atualização de estoque; `"Usuário deletado, mas as matrículas ficaram sujas"`). Para cada mensagem desse tipo, procure o código que faria o efeito; se não existir, registre o finding citando a linha da mensagem e o fluxo afetado — é regra de negócio incompleta, e a Fase 3 deve implementá-la no service.
```
(?i)(print|console\.log|logger\.\w+|log)\(.*(devolver|estornar|reembolsar|enviar|notificar|restore|refund|rollback|cleanup|limpar)
(?i)#\s*(TODO|FIXME|XXX)|//\s*(TODO|FIXME|XXX)
```

### AP-08 — Estado global mutável / conexão singleton implícita
**O que é:** variáveis de módulo mutáveis compartilhadas entre requisições (cache, contadores, conexão) acessadas via `global` ou exports mutáveis.

**Sinais:**
```
^\s*global\s+\w+
^(let|var)\s+\w+\s*=\s*(\{\}|\[\]|0|null)     (nível de módulo, mutado em funções)
check_same_thread\s*=\s*False
module\.exports\s*=\s*\{[^}]*(cache|state|total|count)
```
Confirme que o estado é **mutado** em tempo de execução e compartilhado.

### AP-09 — Autenticação/autorização ausente ou falsa
**O que é:** login que não emite credencial verificável (token fake/previsível), rotas que deveriam ser protegidas sem nenhuma verificação, usuário capaz de atribuir a si mesmo papel privilegiado.

**Sinais:**
```
(?i)fake[-_]?(jwt|token)|['"]token['"]\s*:\s*['"][^'"]*['"]\s*\+
(?i)role\s*=\s*(data|req\.body|request)\b.*(get\(|\[)['"]role
```
- Nenhum decorator/middleware de auth (`login_required`, `@jwt_required`, `authenticate`, `requireAuth`) nas rotas de escrita/admin.

### AP-10 — Escrita multi-etapa sem transação / callback hell
**O que é:** operação de negócio que grava em várias tabelas em passos independentes, sem `BEGIN/COMMIT/ROLLBACK`; ou cadeia de callbacks aninhados com erros ignorados.

**Sinais:**
- Vários `INSERT/UPDATE` consecutivos sem transação explícita, com `return` de erro no meio do fluxo.
- Callbacks aninhados em 3+ níveis (`function(err, ...) {` dentro de outro).
- Parâmetro `err` recebido e não tratado.

### AP-11 — Acoplamento rígido a infraestrutura
**O que é:** lógica de negócio que instancia/importa diretamente conexão de banco, cliente SMTP, gateway de pagamento, sem receber a dependência por parâmetro/construtor; impossível substituir em testes.

**Sinais:**
- `get_db()`/`new Database(...)`/`smtplib.SMTP(...)` chamados dentro de funções de negócio.
- Classe que cria suas próprias dependências no construtor (`this.db = new sqlite3.Database(...)`).

---

## MEDIUM

### AP-12 — Consultas N+1
**O que é:** uma consulta para a lista e mais uma (ou várias) para cada item.

**Sinais:**
- `execute(`/`.query`/`.get(`/`db.get(`/`Model.query...` **dentro** de `for`/`forEach`/`map` que itera resultados de outra consulta.
- Acesso a relacionamento lazy dentro de loop (`len(u.tasks)`, `t.user.name`) sem eager loading.
- Contagens por item (`filter_by(category_id=c.id).count()` em loop).

### AP-13 — Tratamento de erro genérico, silencioso ou que vaza detalhes
**Sinais:**
```
except\s*:
except Exception( as \w+)?:\s*$     (repetido em todos os handlers)
return .*str\(e\)
\(err(, \w+)?\)\s*=>\s*\{(?![^}]*err)     (callback que ignora err)
catch\s*\(\w*\)\s*\{\s*\}
```
Confirme se o erro é engolido, se o detalhe interno vai para o cliente e se não existe handler central.

### AP-14 — Validação de entrada ausente ou duplicada
**O que é:** campos do request usados sem validação de presença/tipo/faixa (gerando 500 em vez de 400), ou a mesma validação copiada em vários handlers; helpers de validação existentes mas não usados.

**Sinais:**
- Comparação numérica direta com valor do request (`data['priority'] < 1`) sem conversão/checagem de tipo.
- `request.get_json()` usado sem checar `None` antes de `'x' in data`.
- Blocos de validação idênticos em create/update.

### AP-15 — Uso de APIs deprecated
**O que é:** chamadas a APIs marcadas como deprecated/legadas ou removidas nas versões declaradas (ou instaladas) da linguagem, framework ou bibliotecas. **Sempre** verifique esta categoria; recomende a substituição moderna.

| Ecossistema | API deprecated / legada | Substituição |
|---|---|---|
| Python ≥ 3.12 | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` |
| Python ≥ 3.12/3.13 | módulos `distutils`, `imp`, `cgi`, `asynchat`, `asyncore` (removidos) | `setuptools`/`packaging`, `importlib`, `email`/framework, `asyncio` |
| SQLAlchemy 2.x | `Model.query.get(id)` / `Query.get()` (legado) | `db.session.get(Model, id)` |
| SQLAlchemy 2.x | `session.query(...)` estilo 1.x (legado) | `db.session.execute(select(...))` |
| Flask ≥ 2.3 / 3.x | `@app.before_first_request` (removido), `flask.json.JSONEncoder` (removido), `flask.__version__` (deprecated) | inicialização na factory, `app.json` provider, `importlib.metadata.version("flask")` |
| Node.js | `new Buffer(...)` | `Buffer.from(...)` / `Buffer.alloc(...)` |
| Node.js | `url.parse()` | `new URL()` |
| Node.js | `crypto.createCipher()` (removido no Node 22) | `crypto.createCipheriv()` |
| Node.js | `util.isArray()`, `util.isString()` etc. | `Array.isArray()`, `typeof` |
| Node.js | `fs.exists()` | `fs.existsSync()` / `fs.promises.access()` |
| Express 4 | `body-parser` como dependência separada | `express.json()` / `express.urlencoded()` (desde 4.16) |
| Express 4 → 5 | `req.param()`, `res.send(status)`, `res.json(status, body)`, `app.del()` | `req.params/query/body`, `res.sendStatus()`, `res.status().json()`, `app.delete()` |
| npm | pacote `request` (deprecated) | `fetch` nativo / `undici` |

**Sinais:** busque os nomes da tabela acima; rode a aplicação/scripts com avisos habilitados (`python -W default`, `node --trace-deprecation`) e registre os `DeprecationWarning` emitidos.

### AP-16 — Configuração insegura de ambiente
**Sinais:**
```
debug\s*=\s*True|DEBUG['"]?\]?\s*=\s*True
app\.run\(.*debug=True
CORS\(app\)\s*$     (CORS liberado para qualquer origem sem configuração)
host\s*=\s*['"]0\.0\.0\.0['"]     (combinado com debug)
```
Configuração por ambiente fixa no código em vez de vir de env/config.

### AP-17 — Lógica duplicada (copy-paste)
**Sinais:**
- Funções quase idênticas (mesma sequência de consultas/transformações) com nomes diferentes.
- Mesmo bloco de serialização (row → dict) repetido em várias funções.
- A mesma regra de negócio em mais de um arquivo.

---

## LOW

### AP-18 — Magic numbers e strings
**Sinais:** literais numéricos de regra de negócio (`> 10000`, `* 0.1`, `<= 5`, `< 4`) e listas de valores válidos (`["pendente", "aprovado", ...]`) inline em vez de constantes/enums nomeados; constantes definidas mas não usadas.

### AP-19 — Nomenclatura ruim
**Sinais:** variáveis de uma letra fora de loops curtos (`u`, `e`, `p`, `cc`), abreviações obscuras, nomes que sombreiam builtins (`id`, `type`, `list`, `input`), nomes enganosos (`badCrypto`, `data2`, `cursor3`).

### AP-20 — `print`/`console.log` como log
**Sinais:**
```
^\s*print\(
console\.(log|error)\(
```
em código de aplicação (não em scripts CLI/seed). Recomende o logger da linguagem/framework com níveis.

### AP-21 — Código morto e imports não utilizados
**Sinais:** imports sem uso (`import os, sys, json` sem referências), funções/helpers/constantes nunca chamados, variáveis exportadas nunca atualizadas. Confirme buscando referências ao símbolo em todo o projeto.

### AP-22 — Construções não idiomáticas / verbosas
**Sinais:**
```
if .*:\s*\n\s*return True\s*\n\s*else:\s*\n\s*return False
type\(\w+\)\s*==\s*(list|dict|str|int)
==\s*None|!=\s*None
```
`if/else` aninhados que poderiam ser uma expressão booleana; `self = this` desnecessário.
