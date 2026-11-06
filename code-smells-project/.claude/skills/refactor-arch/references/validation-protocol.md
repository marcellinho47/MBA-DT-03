# Protocolo de Validação (Fase 3)

A refatoração só está concluída quando a aplicação **sobe sem erros** e **todos os endpoints originais respondem** como na linha de base (exceto as mudanças intencionais de contrato, documentadas).

## 1. Preparar o ambiente

- Use o ambiente isolado do projeto se existir (`.venv/`, `venv/`, `node_modules/`). Se não existir, crie (`python -m venv .venv` + `pip install -r requirements.txt`; `npm install`) — esses diretórios devem estar no `.gitignore`.
- Rode scripts de preparação documentados no README (ex.: `python seed.py`).
- Escolha a porta padrão do projeto; se estiver ocupada, use outra via variável de ambiente/config (não altere o código só para isso).

## 2. Subir a aplicação e encerrar com segurança

Regras:
- Suba **um** processo em background, guarde o **PID** e encerre **somente esse PID** ao final. Nunca encerre processos por nome (`taskkill /IM node.exe`, `pkill python`) — isso derruba processos do usuário.
- Evite o *reloader* do modo debug (ele cria um processo filho que sobrevive ao `kill` do pai): para Flask use `flask --app <entry> run --no-reload --port <porta>` ou garanta `debug=False` via env.
- Aguarde a porta responder (poll com timeout de ~10 s) em vez de `sleep` fixo longo.
- Capture stdout/stderr em arquivo temporário **fora do projeto** para inspecionar erros de boot e avisos (`DeprecationWarning`).

Exemplo (bash):
```bash
LOG="$(mktemp)"
.venv/Scripts/python -m flask --app app run --no-reload --port 5000 > "$LOG" 2>&1 &   # Linux/macOS: .venv/bin/python
PID=$!
for i in $(seq 1 20); do curl -s -o /dev/null localhost:5000/ && break; sleep 0.5; done
# ... requisições ...
kill $PID
```
```bash
node src/app.js > "$LOG" 2>&1 & PID=$!
```

**Boot OK** = processo continua vivo, porta responde, nenhum traceback/stack trace no log.

## 3. Linha de base (antes de refatorar)

Para cada endpoint do inventário da Fase 1:

1. Monte uma requisição válida:
   - `GET` de coleção e de item existente (use IDs do seed).
   - `POST`/`PUT` com payload válido — use os exemplos de `*.http`, README ou o próprio código (campos obrigatórios).
   - Um caso de erro representativo por recurso (ID inexistente → 404; payload inválido → 400).
   - `DELETE` por último, sobre registros criados durante o teste quando possível.
2. Registre: **método, caminho, status HTTP, tipo do corpo (JSON/texto) e as chaves de primeiro nível do JSON** (e as chaves dos itens, se for lista).
3. Registre também as provas dos problemas de segurança relevantes (ex.: payload de SQL Injection que funciona; campo sensível presente na resposta).

Formato sugerido (guarde fora do projeto):
```
GET  /produtos            200 json {dados[], sucesso}  item keys: id,nome,descricao,preco,estoque,categoria,ativo,criado_em
POST /login (sqli)        200 json  ← vulnerável
```

Dica: um script curto (bash com `curl -s -o /dev/null -w '%{http_code}'`, ou Python `urllib`/Node `fetch`) que roda a mesma lista antes e depois evita diferenças de procedimento. Mantenha o script fora do projeto.

## 4. Depois da refatoração

1. Suba a aplicação com o **comando original** de execução do README (ex.: `python app.py` deve funcionar — teste ao menos o boot com ele, mesmo que as requisições sejam feitas com `--no-reload`).
2. Re-execute **exatamente** a mesma lista de requisições.
3. Compare com a linha de base:
   - Status igual e mesmas chaves → ✓
   - Diferença prevista em "Intentional Contract Changes" → ✓ (anotar)
   - Qualquer outra diferença → ✗: corrija e repita.
4. Verifique as correções de segurança: o payload de injeção agora falha (401/400), campos sensíveis não aparecem, endpoints protegidos retornam 401/403 sem credencial e funcionam com ela.
5. Verifique os **efeitos de negócio** dos fluxos que alteram estado, consultando o dado depois da operação (não basta o status HTTP): ex.: estoque cai ao criar pedido e volta ao cancelar; remover um registro não deixa dependentes órfãos; pagamento recusado não cria matrícula.
6. Verifique que nenhum `DeprecationWarning` do catálogo continua sendo emitido (`python -W default`, `node --trace-deprecation`).

## 5. Verificação estática final

- Rode de novo as buscas de sinais do catálogo (AP-01..AP-22) sobre o código novo.
- Confirme a conformidade com o checklist de `mvc-guidelines.md`.
- Liste qualquer anti-pattern remanescente com a justificativa (ex.: "AP-09 — autenticação real exige biblioteca de JWT; fora do escopo, documentado").

## 6. Limpeza

- Encerre o processo iniciado (pelo PID).
- Não deixe arquivos temporários, logs ou bancos de teste dentro do projeto (bancos gerados devem estar cobertos pelo `.gitignore`).
- Não faça commit — o usuário decide quando commitar.
