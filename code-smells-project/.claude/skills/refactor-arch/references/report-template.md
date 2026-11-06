# Template do Relatório de Auditoria (Fase 2)

O relatório é impresso na conversa **e** salvo em arquivo Markdown. Siga a estrutura abaixo exatamente — seções, ordem e rótulos. Texto descritivo pode ser em português; rótulos e cabeçalhos ficam como no template.

## Regras

1. **Ordem:** findings agrupados e ordenados por severidade — CRITICAL → HIGH → MEDIUM → LOW. Dentro de cada severidade, ordene pelo ID do catálogo.
2. **Localização exata:** `File:` sempre com `caminho/relativo:linha` ou `caminho/relativo:inicio-fim`. Vários locais → separe por `; `. Caminhos relativos à raiz do projeto.
3. **Um finding por problema**, não por ocorrência. Ocorrências múltiplas vão no mesmo finding (campo `File:` com todos os locais).
4. **Evidência:** inclua um trecho curto (até ~3 linhas) do código problemático quando ajudar a entender o finding. Não inclua segredos completos — mascare (`pk_live_1234****`).
5. **Summary** deve bater com a contagem dos findings listados. **Total** = soma do Summary.
6. Numere os findings sequencialmente (`F-01`, `F-02`, ...) para que o usuário possa referenciá-los ao aprovar a Fase 3.
7. A seção **Deprecated APIs** é obrigatória: liste as APIs encontradas ou escreva `None detected (checked against <versões>)`.

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório do projeto>
Stack:   <Linguagem> + <Framework> (<banco / forma de acesso>)
Files:   <N> analyzed | ~<L> lines of code
Date:    <AAAA-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

<1–3 frases: diagnóstico geral da arquitetura atual e dos riscos mais graves>

## Findings

### F-01 [CRITICAL] <Nome do anti-pattern> (AP-xx)
File: <arquivo:linha>; <arquivo:inicio-fim>
Description: <o que acontece, concretamente, neste código>
Evidence:
```<linguagem>
<trecho curto>
```
Impact: <consequência concreta: o que pode dar errado / quem é afetado>
Recommendation: <o que fazer> — Playbook PB-xx

### F-02 [CRITICAL] ...

### F-0n [HIGH] ...

### F-0n [MEDIUM] ...

### F-0n [LOW] ...

## Deprecated APIs
| API | Location | Replacement |
|-----|----------|-------------|
| <api> | <arquivo:linha> | <substituição> |

## Refactoring Plan Preview
<lista curta: estrutura MVC alvo e quais findings cada etapa elimina>

================================
Total: <n> findings
================================
````

## Exemplo de finding bem escrito

````markdown
### F-02 [CRITICAL] SQL Injection (AP-02)
File: models.py:28; models.py:47-50; models.py:109-111
Description: As queries são montadas concatenando valores recebidos do request. Em `login_usuario`, email e senha entram diretamente na cláusula WHERE.
Evidence:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```
Impact: Bypass de autenticação (`' OR '1'='1`) e leitura/alteração/remoção arbitrária de dados.
Recommendation: Usar queries parametrizadas (`?`) em todas as consultas e mover o acesso a dados para repositórios — Playbook PB-01
````

## Exemplo de finding mal escrito (não faça)

````markdown
### [CRITICAL] Código inseguro
File: models.py
Description: O código tem problemas de segurança.
````
Problemas: sem linha, sem ID do catálogo, descrição vaga, sem impacto nem recomendação acionável.
