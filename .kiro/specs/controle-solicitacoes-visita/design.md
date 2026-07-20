# Design: Controle de Solicitações de Visita

## Overview

O módulo adiciona ao sistema CadÚnico/PBF um ciclo de vida completo para solicitações de visita domiciliar. Atualmente, "Visita Domiciliar" é apenas um tipo de atendimento registrado de forma avulsa; o novo módulo cria uma entidade dedicada com rastreabilidade de status (`Pendente → Em Andamento → Realizada | Cancelada`), controle de acesso por perfil, auditoria de todas as ações e integração com o dashboard existente.

A implementação segue **exatamente** os padrões já estabelecidos em `app.py`: camada de BD via `get_db()` / `_exec()` / `_fetchone()` / `_fetchall()` com placeholder `PH`, autenticação por `_requer_login()` e `session['perfil']`, auditoria via `audit()`, paginação de 20 itens por página e flash messages com categorias `'ok'` / `'erro'`.

---

## Architecture

### Camadas envolvidas

```
Browser
  └── Jinja2 Templates (5 novas: painel_visitas, nova_visita, detalhe_visita, editar_visita, atualizar_status_visita)
        └── Flask Routes (6 novas rotas em app.py)
              └── DB Abstraction Layer (get_db / _exec / _fetchone / _fetchall)
                    └── SQLite (dev) / PostgreSQL (prod)
                    └── audit_log (existente)
```

### Fluxo de dados por operação

```
POST /visitas/nova
  → validar_cpf() + validação de campos obrigatórios
  → INSERT solicitacoes_visita (status=Pendente)
  → audit(VISITA_CRIADA)
  → redirect → painel_visitas

POST /visitas/<id>/editar
  → verificar permissão + status != Realizada/Cancelada
  → UPDATE solicitacoes_visita (campos editáveis)
  → audit(VISITA_EDITADA)
  → redirect → detalhe_visita

POST /visitas/<id>/status
  → validar campos condicionais (data_realizada / motivo_cancelamento)
  → UPDATE solicitacoes_visita (status + timestamps)
  → audit(VISITA_STATUS_ATUALIZADO)
  → redirect → detalhe_visita

POST /visitas/<id>/excluir
  → verificar perfil == admin
  → DELETE solicitacoes_visita
  → audit(VISITA_EXCLUIDA)
  → redirect → painel_visitas
```

---

## Components and Interfaces

### Rotas Flask (app.py)

| Rota | Métodos | Função | Descrição |
|---|---|---|---|
| `/visitas` | GET | `painel_visitas` | Listagem com filtros e paginação |
| `/visitas/nova` | GET, POST | `nova_visita` | Formulário de criação |
| `/visitas/<int:visita_id>` | GET | `detalhe_visita` | Visualização de detalhes |
| `/visitas/<int:visita_id>/editar` | GET, POST | `editar_visita` | Formulário de edição |
| `/visitas/<int:visita_id>/status` | POST | `atualizar_status_visita` | Atualização de status |
| `/visitas/<int:visita_id>/excluir` | POST | `excluir_visita` | Exclusão (admin only) |

### Templates Jinja2

| Template | Contexto recebido |
|---|---|
| `painel_visitas.html` | `visitas`, `pagina`, `total_paginas`, `total_filtrado`, `filtros`, `usuarios` (admin) |
| `nova_visita.html` | `erros`, `form`, `usuarios` (para campo responsavel_id) |
| `detalhe_visita.html` | `visita`, `solicitante`, `responsavel`, `pode_editar`, `pode_excluir` |
| `editar_visita.html` | `visita`, `erros`, `form`, `usuarios` |
| `atualizar_status_visita.html` | renderizado inline dentro de `detalhe_visita.html` (painel modal ou seção) |

### Modificações em arquivos existentes

- **`app.py`**: adição das 6 rotas e integração no `init_db()` (ambos os branches SQLite e PostgreSQL)
- **`templates/base.html`**: adicionar link "Visitas" na `<nav>` com classe `ativo` condicional
- **`templates/dashboard.html`**: adicionar card com contagem de `Pendente` e link para painel com filtro

---

## Data Models

### Tabela `solicitacoes_visita`

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS solicitacoes_visita (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf_rf          TEXT NOT NULL,
    nome_rf         TEXT NOT NULL,
    endereco        TEXT NOT NULL,
    motivo          TEXT NOT NULL,
    data_prevista   TEXT NOT NULL,          -- formato ISO: YYYY-MM-DD
    data_realizada  TEXT,                   -- preenchido ao marcar Realizada
    status          TEXT NOT NULL DEFAULT 'Pendente',
                                            -- Pendente | Em Andamento | Realizada | Cancelada
    solicitante_id  INTEGER NOT NULL REFERENCES usuarios(id),
    responsavel_id  INTEGER REFERENCES usuarios(id),  -- nulável
    observacoes     TEXT,
    motivo_cancelamento TEXT,               -- preenchido ao marcar Cancelada
    criado_em       TEXT NOT NULL,          -- ISO datetime
    atualizado_em   TEXT NOT NULL           -- ISO datetime, atualizado em cada mutação
);

-- PostgreSQL
CREATE TABLE IF NOT EXISTS solicitacoes_visita (
    id              SERIAL PRIMARY KEY,
    cpf_rf          TEXT NOT NULL,
    nome_rf         TEXT NOT NULL,
    endereco        TEXT NOT NULL,
    motivo          TEXT NOT NULL,
    data_prevista   TEXT NOT NULL,
    data_realizada  TEXT,
    status          TEXT NOT NULL DEFAULT 'Pendente',
    solicitante_id  INTEGER NOT NULL REFERENCES usuarios(id),
    responsavel_id  INTEGER REFERENCES usuarios(id),
    observacoes     TEXT,
    motivo_cancelamento TEXT,
    criado_em       TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL
);
```

**Invariantes de domínio:**
- `status` ∈ `{'Pendente', 'Em Andamento', 'Realizada', 'Cancelada'}`
- `data_realizada` é NOT NULL apenas quando `status = 'Realizada'`
- `motivo_cancelamento` é NOT NULL apenas quando `status = 'Cancelada'`
- `atualizado_em` é atualizado em toda operação de UPDATE

### Modelo Python (dict-like via `_PGRow` / `sqlite3.Row`)

Os campos são acessados por chave string: `visita['cpf_rf']`, `visita['status']`, etc. — consistente com o padrão já adotado para `atendimentos` e `usuarios`.

### Lógica de visibilidade (filtro de acesso)

```python
# Entrevistador: vê somente suas próprias solicitações
filtro_acesso = f"AND (sv.solicitante_id = {PH} OR sv.responsavel_id = {PH})"
params_acesso = [uid, uid]

# Admin: sem restrição adicional
filtro_acesso = ""
params_acesso = []
```

### Lógica de paginação

```python
por_pagina = 20
pagina = max(1, int(request.args.get('pagina', 1)))
offset = (pagina - 1) * por_pagina
# ... query com LIMIT {PH} OFFSET {PH}, appending [por_pagina, offset]
total_paginas = max(1, (total_filtrado + por_pagina - 1) // por_pagina)
```

---

## Correctness Properties

*Uma propriedade é uma característica ou comportamento que deve se manter verdadeiro em todas as execuções válidas de um sistema — essencialmente, uma afirmação formal sobre o que o sistema deve fazer. Propriedades servem como ponte entre especificações legíveis por humanos e garantias de correção verificáveis por máquina.*

### Property 1: Criação inicializa status como Pendente

*Para qualquer* conjunto de dados válidos de solicitação (cpf_rf válido, nome_rf, endereço, motivo, data_prevista não vazios), ao criar uma nova solicitação, o registro persistido deve ter `status = 'Pendente'` e `solicitante_id` igual ao ID do usuário autenticado.

**Validates: Requirements 1.1**

---

### Property 2: Validação de CPF rejeita entradas inválidas

*Para qualquer* string que não satisfaça o algoritmo de dígitos verificadores do CPF, a função `validar_cpf()` deve retornar `False`, e nenhuma solicitação deve ser persistida com esse CPF.

**Validates: Requirements 1.2, 1.3**

---

### Property 3: Campos obrigatórios em branco bloqueiam persistência

*Para qualquer* submissão de formulário com pelo menos um campo obrigatório (cpf_rf, nome_rf, endereco, motivo, data_prevista) vazio ou composto apenas de espaços em branco, o sistema deve rejeitar a criação e o número de registros na tabela `solicitacoes_visita` deve permanecer inalterado.

**Validates: Requirements 1.4**

---

### Property 4: Criação bem-sucedida gera entrada de auditoria

*Para qualquer* solicitação criada com sucesso, deve existir exatamente uma entrada na tabela `audit_log` com `acao = 'VISITA_CRIADA'` contendo o `cpf_rf` e o `id` da solicitação criada no campo `detalhe`.

**Validates: Requirements 1.5**

---

### Property 5: Listagem respeita visibilidade por perfil

*Para qualquer* conjunto de solicitações distribuídas entre múltiplos usuários: (a) um usuário com perfil `entrevistador` ao consultar o painel deve receber apenas registros onde `solicitante_id = seu_id OR responsavel_id = seu_id`; (b) um usuário com perfil `admin` deve receber todos os registros existentes.

**Validates: Requirements 2.2, 2.3**

---

### Property 6: Filtros retornam apenas resultados que correspondem ao critério

*Para qualquer* conjunto de solicitações com status, datas e nomes/CPFs variados:
- Aplicando filtro de status `S`, todos os resultados devem ter `status = S`.
- Aplicando filtro de período `[d_ini, d_fim]`, todos os resultados devem ter `data_prevista` dentro do intervalo.
- Aplicando filtro de texto `t`, todos os resultados devem ter `cpf_rf LIKE %t%` ou `nome_rf ILIKE %t%`.

**Validates: Requirements 2.4, 2.5, 2.6**

---

### Property 7: Paginação limita resultados a no máximo 20 por página

*Para qualquer* conjunto de solicitações com N registros (N > 20), cada página retornada deve conter no máximo 20 registros, e a soma de registros em todas as páginas deve ser igual a N (após aplicar os mesmos filtros de acesso).

**Validates: Requirements 2.7**

---

### Property 8: Detalhe exibe todos os campos e respeita controle de acesso

*Para qualquer* solicitação, o detalhe acessado pelo solicitante ou pelo responsável deve conter todos os campos especificados (cpf_rf, nome_rf, endereco, motivo, data_prevista, data_realizada, status, solicitante, responsavel, observacoes). *Para qualquer* entrevistador que não seja solicitante nem responsável da solicitação, o acesso ao detalhe deve resultar em redirecionamento para o painel.

**Validates: Requirements 3.1, 3.2**

---

### Property 9: Edição persiste exatamente os campos submetidos

*Para qualquer* solicitação com status `Pendente` ou `Em Andamento` e qualquer conjunto válido de valores editados (nome_rf, endereco, motivo, data_prevista, responsavel_id, observacoes), após submeter o formulário de edição os valores persistidos devem ser iguais aos submetidos.

**Validates: Requirements 4.1**

---

### Property 10: Edição gera entrada de auditoria

*Para qualquer* edição bem-sucedida de uma solicitação, deve existir uma entrada em `audit_log` com `acao = 'VISITA_EDITADA'` contendo o ID da solicitação no campo `detalhe`.

**Validates: Requirements 4.3**

---

### Property 11: Transições de status exigem campos condicionais corretos

*Para qualquer* solicitação: (a) transição para `Realizada` sem `data_realizada` deve ser rejeitada e o status deve permanecer inalterado; (b) transição para `Realizada` com `data_realizada` válida deve ser aceita e persistida; (c) transição para `Cancelada` sem `motivo_cancelamento` deve ser rejeitada; (d) transição para `Cancelada` com `motivo_cancelamento` preenchido deve ser aceita e persistida.

**Validates: Requirements 5.2, 5.3, 5.4, 5.5**

---

### Property 12: Atualização de status gera auditoria com estado anterior e novo

*Para qualquer* transição de status bem-sucedida, deve existir uma entrada em `audit_log` com `acao = 'VISITA_STATUS_ATUALIZADO'` contendo o ID da solicitação, o status anterior e o novo status no campo `detalhe`.

**Validates: Requirements 5.6**

---

### Property 13: Exclusão é restrita a admin e gera auditoria

*Para qualquer* solicitação: (a) tentativa de exclusão por usuário com perfil `entrevistador` deve ser bloqueada e o registro deve continuar existindo; (b) exclusão por `admin` deve remover o registro e gerar entrada em `audit_log` com `acao = 'VISITA_EXCLUIDA'` contendo o ID e o CPF da solicitação.

**Validates: Requirements 6.1, 6.3**

---

### Property 14: init_db() é idempotente — não apaga dados existentes

*Para qualquer* conjunto de registros em `solicitacoes_visita`, chamar `init_db()` novamente não deve remover nem alterar nenhum registro existente.

**Validates: Requirements 7.3**

---

### Property 15: Dashboard exibe contagem correta de Pendentes visíveis

*Para qualquer* conjunto de solicitações com status variados, a contagem exibida no dashboard para um usuário deve ser igual ao número de registros com `status = 'Pendente'` visíveis para aquele usuário (respeitando as regras de visibilidade por perfil).

**Validates: Requirements 9.1**

---

## Error Handling

### Validações de entrada (criação e edição)

| Condição | Comportamento |
|---|---|
| CPF inválido | `flash('CPF inválido', 'erro')` + re-render do formulário com dados preenchidos |
| Campo obrigatório vazio | `flash('Campo X é obrigatório', 'erro')` + re-render |
| Status terminal na edição | `flash('Esta solicitação não pode ser editada pois já foi finalizada', 'erro')` + redirect para detalhe |
| Realizada sem data_realizada | `flash('Informe a data de realização da visita', 'erro')` + re-render |
| Cancelada sem motivo | `flash('Informe o motivo do cancelamento', 'erro')` + re-render |

### Controle de acesso

| Situação | Comportamento |
|---|---|
| Entrevistador acessa detalhe de solicitação alheia | `flash('Acesso negado', 'erro')` + `redirect(url_for('painel_visitas'))` |
| Não-admin tenta excluir | `redirect(url_for('painel_visitas'))` silencioso (consistente com padrão de `excluir_atendimento`) |
| Usuário não autenticado em qualquer rota | `redirect(url_for('login'))` via `_requer_login()` |

### Registro inexistente

- Se `visita_id` não existir: `redirect(url_for('painel_visitas'))` com flash de erro, sem expor detalhes internos.

### Integridade no banco

- O campo `atualizado_em` é sempre atualizado em toda operação de `UPDATE`, garantindo rastreabilidade temporal.
- O `responsavel_id` é FK nullable; se o usuário responsável for excluído do sistema, o campo fica `NULL` (sem cascade delete) — o registro de visita é preservado.

---

## Testing Strategy

### Abordagem dual

O módulo combina **testes de exemplo** (para comportamentos específicos e fluxos de UI) com **testes de propriedade** (para invariantes universais de lógica de negócio).

### Biblioteca de property-based testing

**[Hypothesis](https://hypothesis.readthedocs.io/)** para Python — biblioteca madura, amplamente adotada no ecossistema Flask/pytest.

```
pip install hypothesis pytest
```

Cada teste de propriedade roda com no mínimo **100 iterações** (configuração padrão do Hypothesis, ajustável via `@settings(max_examples=100)`).

### Testes de propriedade

Para cada propriedade do design, um único teste de propriedade usando `@given`:

```python
# Feature: controle-solicitacoes-visita, Property 2: validar_cpf rejeita entradas inválidas
@given(st.text())
@settings(max_examples=500)
def test_cpf_invalido_rejeitado(cpf_aleatorio):
    """Qualquer CPF que não passe nos dígitos verificadores não deve ser aceito."""
    if not validar_cpf(cpf_aleatorio):
        assert not persistir_visita(cpf=cpf_aleatorio, ...)
```

Cada teste deve ter um comentário de tag no formato:
`# Feature: controle-solicitacoes-visita, Property N: <texto da propriedade>`

### Testes de exemplo (unit tests)

Focados em fluxos específicos que não se beneficiam de geração aleatória:

- Confirmação de exclusão requer POST com token CSRF (Req. 6.2)
- Link "Visitas" presente na nav para usuário autenticado (Req. 8.1)
- Classe `ativo` aplicada ao link quando no painel (Req. 8.2)
- Card do dashboard redireciona para painel com `?status=Pendente` (Req. 9.2)
- Chamada de `init_db()` com tabela `solicitacoes_visita` já existente não lança exceção (Req. 7.1, 7.2)

### Testes de integração

- Ciclo de vida completo: criar → Em Andamento → Realizada (com data)
- Ciclo de cancelamento: criar → Cancelada (com motivo)
- Visibilidade cruzada: entrevistador A não vê registros do entrevistador B
- Filtros combinados: status + período + texto simultaneamente

### Cobertura mínima esperada

| Área | Tipo de teste prioritário |
|---|---|
| `validar_cpf()` | Property (Hypothesis) |
| Lógica de visibilidade por perfil | Property |
| Filtros do painel | Property |
| Validações de status + campos condicionais | Property |
| Auditoria em todas as operações | Property |
| Idempotência do `init_db()` | Property |
| Controles de UI (nav, dashboard card, confirmação de exclusão) | Example |
| Ciclos de vida completos | Integration |
