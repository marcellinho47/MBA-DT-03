---
name: refactor-arch
description: Audita e refatora um projeto backend legado para o padrão MVC, em 3 fases sequenciais — (1) análise da stack e da arquitetura, (2) auditoria contra um catálogo de anti-patterns com relatório por severidade e arquivo:linha, pausando para confirmação, (3) refatoração para MVC com validação de boot e endpoints. Agnóstica de linguagem/framework. Use quando o usuário pedir /refactor-arch, auditoria arquitetural, detecção de code smells/anti-patterns ou refatoração de um projeto para MVC.
argument-hint: "[caminho-do-relatório.md]"
disable-model-invocation: true
---

# refactor-arch — Auditoria e Refatoração Arquitetural para MVC

Você atua como um **arquiteto de software sênior** fazendo a revisão de um projeto legado que acabou de herdar. O trabalho tem **três fases estritamente sequenciais**. Nunca pule uma fase, nunca as execute fora de ordem e **nunca modifique código-fonte antes da confirmação explícita do usuário ao final da Fase 2**.

O diretório de trabalho atual (onde o usuário invocou a skill) é a **raiz do projeto alvo**. Tudo o que for analisado e refatorado está dentro dele.

## Arquivos de referência

Leia cada arquivo **no momento indicado** (não antes — economize contexto):

| Arquivo | Quando ler | Conteúdo |
|---|---|---|
| [`references/project-analysis.md`](references/project-analysis.md) | Início da Fase 1 | Heurísticas para detectar linguagem, framework, banco, domínio e classificar a arquitetura |
| [`references/anti-patterns-catalog.md`](references/anti-patterns-catalog.md) | Início da Fase 2 | Catálogo de anti-patterns com sinais de detecção e severidade (inclui APIs deprecated) |
| [`references/report-template.md`](references/report-template.md) | Ao montar o relatório da Fase 2 | Formato obrigatório do relatório de auditoria |
| [`references/mvc-guidelines.md`](references/mvc-guidelines.md) | Início da Fase 3 | Arquitetura MVC alvo, responsabilidades de cada camada, estruturas por stack |
| [`references/refactoring-playbook.md`](references/refactoring-playbook.md) | Durante a Fase 3 | Transformações concretas (antes/depois) para cada anti-pattern |
| [`references/validation-protocol.md`](references/validation-protocol.md) | Antes e depois da refatoração (Fase 3) | Como subir a aplicação, testar endpoints e comparar com a linha de base |

## Argumentos

`$ARGUMENTS`

- Se o argumento acima for um caminho terminado em `.md`, ele é o **caminho do relatório** da Fase 2 (relativo ao diretório atual ou absoluto).
- Caso contrário, use o padrão: `<raiz-do-repositório-git>/reports/audit-<nome-do-diretório-do-projeto>.md`. Descubra a raiz com `git rev-parse --show-toplevel`; se não houver git, use `./reports/`.

---

## FASE 1 — Análise do Projeto

**Objetivo:** entender o que é o projeto antes de julgar qualquer coisa. Somente leitura.

1. Leia `references/project-analysis.md`.
2. Inventarie os arquivos-fonte **ignorando** dependências e artefatos: `.git/`, `.claude/`, `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `dist/`, `build/`, `vendor/`, `target/`, bancos (`*.db`, `*.sqlite`) e lockfiles.
3. Detecte, com evidência (arquivo que comprova): linguagem e versão quando declarada, framework e versão, dependências relevantes, banco de dados e forma de acesso (SQL cru, ORM, query builder), entry point e comando de execução.
4. **Leia integralmente todos os arquivos-fonte.** Projetos legados escondem problemas em qualquer lugar; amostrar não é suficiente.
5. Mapeie: domínio da aplicação (a partir de tabelas/entidades/rotas), tabelas/entidades, **inventário de endpoints** (método + caminho + handler + arquivo:linha) e a arquitetura atual segundo a classificação do arquivo de referência.
6. Imprima o resumo **exatamente** neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se conhecida>
Framework:     <framework + versão>
Dependencies:  <dependências relevantes, separadas por vírgula>
Database:      <banco + forma de acesso>
Domain:        <descrição curta do domínio (entidades principais)>
Architecture:  <classificação — justificativa em uma frase>
Entry point:   <arquivo + comando de execução>
Source files:  <N> files analyzed (~<L> lines)
DB tables:     <tabelas/entidades>
Endpoints:     <N> (<lista compacta METHOD /path>)
================================
```

Siga direto para a Fase 2 (não é necessário pedir confirmação entre a Fase 1 e a Fase 2).

---

## FASE 2 — Auditoria Arquitetural

**Objetivo:** cruzar o código contra o catálogo e produzir um relatório acionável. Somente leitura do código-fonte; o **único arquivo escrito nesta fase é o relatório**, fora do código da aplicação.

1. Leia `references/anti-patterns-catalog.md` e `references/report-template.md`.
2. Para **cada** anti-pattern do catálogo, aplique os sinais de detecção (buscas por padrão **e** leitura do código). Um sinal de busca é só um indício: **confirme lendo o trecho** antes de registrar o finding.
3. Regras para os findings:
   - **Arquivo e linha exatos** (`arquivo:linha` ou `arquivo:inicio-fim`), conferidos no arquivo atual. Nunca estime números de linha.
   - Um finding por problema; quando o mesmo problema ocorre em vários locais, liste todos os locais no mesmo finding.
   - Severidade conforme o catálogo. Só eleve ou rebaixe com justificativa explícita no texto (ex.: o "segredo" é claramente um valor de teste).
   - Cada finding referencia o ID do catálogo (`AP-xx`) e a transformação do playbook (`PB-xx`) que o resolve.
   - **Sempre** verifique APIs deprecated (AP-15) considerando as versões declaradas nos manifests e a versão do runtime instalado.
   - Não invente problemas para atingir números. Se uma categoria do catálogo não se aplica, ela simplesmente não aparece.
4. Ordene os findings por severidade: **CRITICAL → HIGH → MEDIUM → LOW**; dentro da mesma severidade, pelo ID do catálogo.
5. Monte o relatório seguindo `references/report-template.md`, **imprima-o** na conversa e **salve-o** no caminho definido em "Argumentos" (crie o diretório se necessário).
6. **PARE.** Termine a sua resposta com exatamente:

```
Phase 2 complete. Report saved to <caminho>.
Proceed with refactoring (Phase 3)? [y/n]
```

Encerre o turno e aguarde a resposta do usuário. **Não altere nenhum arquivo do projeto** antes de receber uma resposta afirmativa (`y`, `yes`, `s`, `sim`, ou equivalente inequívoco). Se a resposta for negativa, encerre a skill informando que o relatório está disponível. Se o usuário pedir para refatorar apenas parte dos findings, respeite o escopo indicado.

---

## FASE 3 — Refatoração para MVC

**Objetivo:** reestruturar o projeto para MVC eliminando os findings, **sem quebrar** a aplicação.

### 3.1 Preparação
1. Leia `references/mvc-guidelines.md`, `references/refactoring-playbook.md` e `references/validation-protocol.md`.
2. Se o projeto estiver em um repositório git com alterações não commitadas no diretório do projeto, avise o usuário (as mudanças da refatoração ficarão misturadas) — mas não faça commits por conta própria.
3. **Linha de base:** suba a aplicação **original** e registre, para cada endpoint do inventário da Fase 1, o status HTTP e o formato da resposta (chaves do JSON), conforme o protocolo de validação. Guarde o resultado (em memória ou em arquivo temporário **fora** do projeto). Se não for possível subir a aplicação original, registre o motivo e use o inventário estático como referência.

### 3.2 Plano
Antes de editar, escreva um plano curto:
- A **estrutura de diretórios alvo** (baseada em `mvc-guidelines.md`, adaptada à stack e ao que já existe no projeto — em projetos parcialmente organizados, **evolua** a estrutura existente em vez de reescrever do zero).
- O mapeamento **finding → transformação do playbook → arquivos afetados**.
- As **mudanças intencionais de contrato** (se houver), sempre justificadas por segurança (ex.: remover hash de senha da resposta, proteger endpoint administrativo). Todo o resto do contrato HTTP — caminhos, métodos, nomes de campos de entrada/saída, códigos de status de sucesso — deve ser **preservado**.

### 3.3 Execução
1. Aplique as transformações **incrementalmente**, uma camada/domínio por vez, priorizando CRITICAL e HIGH.
2. Regras invioláveis:
   - O comando de execução documentado no README do projeto (ex.: `python app.py`, `npm start`) **continua funcionando**. Mantenha o entry point no mesmo caminho como um *composition root* fino.
   - **Nenhum segredo** no código: tudo vem de variáveis de ambiente via módulo de configuração, com defaults seguros apenas para desenvolvimento. Crie/atualize um `.env.example` (sem valores reais).
   - **Não adicione dependências novas** se a biblioteca padrão ou o framework já oferecem a solução (ex.: `werkzeug.security` no Flask, `crypto.scrypt` no Node). Se uma dependência for indispensável, justifique no resumo final.
   - Dados de seed e bancos existentes devem continuar utilizáveis: se mudar o formato de armazenamento (ex.: hash de senha), trate os dados legados (migração na inicialização ou re-seed documentado).
   - Remova o código antigo que foi substituído — não deixe arquivos mortos convivendo com a nova estrutura.
3. Após cada etapa significativa, verifique ao menos que o projeto ainda importa/compila (ex.: `python -c "import app"`, `node --check`).

### 3.4 Validação
Siga `references/validation-protocol.md`:
1. Suba a aplicação refatorada com o comando original.
2. Repita **todas** as requisições da linha de base e compare status e formato.
3. Teste também as correções de segurança (ex.: o payload de SQL Injection agora falha, o segredo não aparece mais na resposta).
4. Se algo falhar, **corrija e valide novamente**. Não declare sucesso com falhas pendentes.
5. Rode novamente os sinais de detecção do catálogo sobre o código novo para listar o que restou.
6. Encerre a aplicação que você subiu (somente o processo que você iniciou).

### 3.5 Resumo final
Imprima exatamente neste formato:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios do código da aplicação>

## Changes Applied
<por finding: [SEVERIDADE] AP-xx Nome → PB-xx — o que foi feito (arquivos)>

## Intentional Contract Changes
<lista justificada, ou "None">

## Validation
  ✓/✗ Application boots without errors (<comando>)
  ✓/✗ All original endpoints respond (<N>/<N> match baseline)
  ✓/✗ Security fixes verified (<quais>)
  ✓/✗ Remaining anti-patterns: <0 ou lista com justificativa>

## How to run
<comandos, incluindo variáveis de ambiente necessárias>
================================
```

Use `✗` com honestidade: o resumo deve refletir exatamente o que foi verificado.
