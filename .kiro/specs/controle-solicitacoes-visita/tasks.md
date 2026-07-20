# Implementation Plan: Controle de Solicitações de Visita

## Overview

Implementação incremental do módulo de solicitações de visita domiciliar no sistema CadÚnico/PBF.
A ordem das tarefas garante que cada passo compile e seja testável antes de avançar: primeiro o banco,
depois as rotas, depois os templates e por fim a integração com elementos existentes (nav, dashboard).
Todos os testes de propriedade utilizam **Hypothesis** (`pip install hypothesis pytest`).

---

## Tasks

- [x] 1. Criar tabelas no banco de dados (`init_db`)
  - [x] 1.1 Adicionar bloco `CREATE TABLE IF NOT EXISTS solicitacoes_visita` na branch SQLite de `init_db()` em `app.py`
    - Colunas: `id`, `cpf_rf`, `nome_rf`, `endereco`, `motivo`, `data_prevista`, `data_realizada`, `status` (DEFAULT `'Pendente'`), `solicitante_id` (FK), `responsavel_id` (FK nullable), `observacoes`, `motivo_cancelamento`, `atendimento_id`, `criado_em`, `atualizado_em`
    - Status válidos: `Pendente`, `Em Andamento`, `Realizada`, `Cancelada`
    - _Requisitos: 1.1, 7.1, 7.2_
  - [x] 1.2 Adicionar bloco `CREATE TABLE IF NOT EXISTS solicitacoes_visita` na branch PostgreSQL de `init_db()` em `app.py`
    - Mesma estrutura com `SERIAL PRIMARY KEY`, `REFERENCES usuarios(id)` e `ADD COLUMN IF NOT EXISTS` para migrações seguras
    - _Requisitos: 1.1, 7.1, 7.2_
  - [x] 1.3 Escrever teste de propriedade para idempotência do `init_db()`
    - **Property 14: `init_db()` é idempotente — não apaga dados existentes**
    - **Validates: Requisito 7.3**
    - Chamar `init_db()` duas vezes seguidas e verificar que registros pré-existentes em `solicitacoes_visita` não são removidos nem alterados
    - _Requisitos: 7.3_

- [x] 2. Implementar rota `GET/POST /visitas/nova` e template `nova_visita.html`
  - [x] 2.1 Criar rota `nova_visita` em `app.py` com `GET` e `POST`
    - Proteger com `_requer_login()`; permitir todos os perfis autenticados
    - No `GET`: buscar lista de usuários para campo `responsavel_id` (visível apenas para admin); preencher `nome_rf` a partir do atendimento mais recente do CPF via `_fetchone` se CPF enviado por query string
    - No `POST`: validar CPF com `validar_cpf()`, validar campos obrigatórios (`cpf_rf`, `nome_rf`, `endereco`, `motivo`, `data_prevista`), inserir em `solicitacoes_visita` com `status='Pendente'`, `solicitante_id=session['usuario_id']`, `criado_em` e `atualizado_em` como `datetime.now().isoformat()`
    - Chamar `audit('VISITA_CRIADA', ...)` com CPF e nome do RF após INSERT bem-sucedido
    - Flash `'ok'` e redirecionar para `painel_visitas` em caso de sucesso; re-render do formulário com erros em caso de falha
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  - [x] 2.2 Criar template `templates/nova_visita.html` estendendo `base.html`
    - Campos: CPF do RF (text, required), Nome do RF (text, required, preenchimento automático via JS fetch ao sair do campo CPF), Endereço (text, required), Motivo (textarea, required), Data Prevista (date, required), Observações (textarea, opcional)
    - Exibir `<select name="responsavel_id">` com entrevistadores somente quando `session.perfil == 'admin'`
    - Exibir mensagens de erro via `get_flashed_messages` com classe `alerta-erro`
    - Botões "Salvar" (`btn-primary`) e "Cancelar" (link para `painel_visitas`)
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.6_
  - [ ] 2.3 Escrever teste de propriedade: criação inicializa status como `Pendente`
    - **Property 1: Criação inicializa status como Pendente**
    - **Validates: Requisito 1.1**
    - Usar `@given` para gerar conjuntos válidos de (cpf_rf, nome_rf, endereco, motivo, data_prevista) e verificar que o registro persistido tem `status='Pendente'` e `solicitante_id` correto
    - _Requisitos: 1.1_
  - [ ] 2.4 Escrever teste de propriedade: `validar_cpf()` rejeita entradas inválidas
    - **Property 2: Validação de CPF rejeita entradas inválidas**
    - **Validates: Requisitos 1.2, 1.3**
    - Usar `@given(st.text())` com `@settings(max_examples=500)`; para qualquer string que não passe nos dígitos verificadores, verificar que nenhuma solicitação é persistida
    - _Requisitos: 1.2, 1.3_
  - [ ] 2.5 Escrever teste de propriedade: campos obrigatórios em branco bloqueiam persistência
    - **Property 3: Campos obrigatórios em branco bloqueiam persistência**
    - **Validates: Requisito 1.4**
    - Usar `@given` para gerar formulários com pelo menos um campo obrigatório vazio/espaços; verificar que o total de linhas em `solicitacoes_visita` permanece inalterado
    - _Requisitos: 1.4_
  - [ ] 2.6 Escrever teste de propriedade: criação bem-sucedida gera entrada de auditoria
    - **Property 4: Criação bem-sucedida gera entrada de auditoria**
    - **Validates: Requisito 1.5**
    - Para cada criação bem-sucedida verificar que existe exatamente uma entrada em `audit_log` com `acao='VISITA_CRIADA'` contendo o `cpf_rf` e o `id` da solicitação no campo `detalhe`
    - _Requisitos: 1.5_

- [x] 3. Checkpoint — verificar criação e banco
  - Garantir que `init_db()` cria a tabela sem erros em SQLite local, que a rota `/visitas/nova` rende o formulário corretamente, que um POST válido insere a linha com `status='Pendente'` e que a auditoria é registrada. Todos os testes das tarefas 1 e 2 devem passar.

- [x] 4. Implementar rota `GET /visitas` e template `painel_visitas.html`
  - [x] 4.1 Criar rota `painel_visitas` em `app.py`
    - Proteger com `_requer_login()`
    - Ler parâmetros de query: `status`, `data_ini`, `data_fim`, `busca`, `pagina` (padrão 1)
    - Montar cláusula `WHERE` dinâmica: filtro de acesso por perfil (entrevistador vê apenas `solicitante_id=uid OR responsavel_id=uid`; admin vê tudo), filtro por `status`, filtro por `data_prevista BETWEEN`, filtro `LIKE` em `cpf_rf` e `nome_rf` (via `LOWER()` para case-insensitive)
    - Paginação: `por_pagina=20`, calcular `total_paginas` e `offset`
    - Calcular contadores por status com query `GROUP BY status`
    - Passar ao template: `visitas`, `pagina`, `total_paginas`, `total_filtrado`, `filtros`, `contadores`, `usuarios` (apenas para admin)
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  - [x] 4.2 Criar template `templates/painel_visitas.html` estendendo `base.html`
    - Contadores de status no topo com badges/cards
    - Formulário de filtros: `<select>` de status, inputs de data inicial/final, campo de busca textual, botão Filtrar e link Limpar
    - Tabela com colunas: Data, CPF do RF, Nome do RF, Motivo, Status (badge colorido), Entrevistador Atribuído, Ações (Detalhe, Editar — se permitido)
    - Mensagem "Nenhuma solicitação encontrada para os filtros selecionados." quando lista vazia
    - Componente de paginação seguindo o padrão de `dashboard.html`
    - Link "+ Nova Solicitação" no topo
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  - [x] 4.3 Escrever teste de propriedade: listagem respeita visibilidade por perfil
    - **Property 5: Listagem respeita visibilidade por perfil**
    - **Validates: Requisitos 2.2, 2.3**
    - Usar `@given` para popular a tabela com solicitações de múltiplos usuários; verificar que entrevistador recebe somente `solicitante_id=uid OR responsavel_id=uid` e que admin recebe todos os registros
    - _Requisitos: 2.2, 2.3_
  - [x] 4.4 Escrever teste de propriedade: filtros retornam apenas resultados correspondentes
    - **Property 6: Filtros retornam apenas resultados que correspondem ao critério**
    - **Validates: Requisitos 2.4, 2.5, 2.6**
    - Usar `@given` para gerar conjuntos de registros e parâmetros de filtro; verificar que: filtro por status retorna somente registros com aquele status; filtro de período retorna somente registros dentro do intervalo; filtro de texto retorna somente registros com match em `cpf_rf` ou `nome_rf`
    - _Requisitos: 2.4, 2.5, 2.6_
  - [ ] 4.5 Escrever teste de propriedade: paginação limita a 20 resultados por página
    - **Property 7: Paginação limita resultados a no máximo 20 por página**
    - **Validates: Requisito 2.7**
    - Usar `@given` para gerar N > 20 registros; verificar que cada página retorna no máximo 20 registros e que a soma de todas as páginas é igual a N
    - _Requisitos: 2.7_

- [x] 5. Implementar rota `GET /visitas/<id>` e template `detalhe_visita.html`
  - [x] 5.1 Criar rota `detalhe_visita` em `app.py`
    - Proteger com `_requer_login()`
    - Buscar solicitação por `visita_id` com `_fetchone`; se não existir, flash `'erro'` e redirecionar para `painel_visitas`
    - Verificar permissão: entrevistador só acessa se `solicitante_id=uid` ou `responsavel_id=uid`; caso contrário, flash `'erro'` e redirecionar para `painel_visitas`
    - Buscar dados do solicitante e do responsável com `_fetchone`
    - Calcular flags `pode_editar` (`status` não é terminal e o usuário tem permissão) e `pode_excluir` (`session['perfil'] == 'admin'`)
    - Passar ao template: `visita`, `solicitante`, `responsavel`, `pode_editar`, `pode_excluir`
    - _Requisitos: 6.1, 6.2, 6.3_
  - [x] 5.2 Criar template `templates/detalhe_visita.html` estendendo `base.html`
    - Exibir todos os campos da solicitação em layout de card (CPF, Nome, Endereço, Motivo, Data Prevista, Data Realizada, Status com badge, Entrevistador, Observações, Motivo Cancelamento)
    - Exibir link para o atendimento gerado quando `status == 'Realizada'` e `atendimento_id` não for nulo
    - Seção de histórico de status ao final (entradas de `audit_log` filtradas por solicitação, em ordem cronológica)
    - Botões condicionais: "Editar" (se `pode_editar`), "Atualizar Status" (se `pode_editar`), "Excluir" com `confirm()` em POST (se `pode_excluir`)
    - _Requisitos: 6.1, 6.2, 6.3_
  - [ ] 5.3 Escrever teste de propriedade: detalhe exibe todos os campos e respeita controle de acesso
    - **Property 8: Detalhe exibe todos os campos e respeita controle de acesso**
    - **Validates: Requisitos 6.1, 6.2, 6.3**
    - Usar `@given` para gerar solicitações e diferentes usuários; verificar que entrevistador que não é solicitante nem responsável recebe redirecionamento, e que acesso legítimo retorna todos os campos especificados
    - _Requisitos: 6.1, 6.2, 6.3_

- [x] 6. Implementar rota `GET/POST /visitas/<id>/editar` e template `editar_visita.html`
  - [x] 6.1 Criar rota `editar_visita` em `app.py`
    - Proteger com `_requer_login()`
    - No `GET`: buscar solicitação; verificar permissão e que `status` não é terminal; renderizar formulário preenchido com dados atuais
    - No `POST`: validar campos obrigatórios; verificar que status não é terminal; executar `UPDATE solicitacoes_visita SET nome_rf=?, endereco=?, motivo=?, data_prevista=?, responsavel_id=?, observacoes=?, atualizado_em=? WHERE id=?`
    - Rejeitar tentativa de alterar `responsavel_id` quando perfil é `entrevistador` (ignorar o campo silenciosamente)
    - Chamar `audit('VISITA_EDITADA', ...)` com id da solicitação
    - _Requisitos: 4.1, 4.2, 4.3, 3.6_
  - [x] 6.2 Criar template `templates/editar_visita.html` estendendo `base.html`
    - Formulário pré-preenchido: Nome do RF, Endereço, Motivo, Data Prevista, Observações
    - Exibir `<select name="responsavel_id">` somente para admin
    - Exibir mensagens flash de erro com classe `alerta-erro`
    - Botões "Salvar Alterações" (`btn-primary`) e "Cancelar" (link para `detalhe_visita`)
    - _Requisitos: 4.1, 4.2_
  - [ ] 6.3 Escrever teste de propriedade: edição persiste exatamente os campos submetidos
    - **Property 9: Edição persiste exatamente os campos submetidos**
    - **Validates: Requisito 4.1**
    - Usar `@given` para gerar solicitações com status `Pendente` ou `Em Andamento` e valores editados válidos; após POST, verificar que os valores no banco são iguais aos submetidos
    - _Requisitos: 4.1_
  - [ ] 6.4 Escrever teste de propriedade: edição gera entrada de auditoria
    - **Property 10: Edição gera entrada de auditoria**
    - **Validates: Requisito 4.3**
    - Para cada edição bem-sucedida, verificar que existe uma entrada em `audit_log` com `acao='VISITA_EDITADA'` contendo o ID da solicitação no campo `detalhe`
    - _Requisitos: 4.3_

- [x] 7. Implementar rota `POST /visitas/<id>/status` (atualização de status e conclusão)
  - [x] 7.1 Criar rota `atualizar_status_visita` em `app.py`
    - Proteger com `_requer_login()`; verificar permissão (entrevistador somente em solicitações suas)
    - Ler `novo_status` do formulário; rejeitar se valor for inválido ou status atual já for terminal
    - Validações condicionais: se `novo_status == 'Realizada'`, exigir `data_realizada` preenchida; se `novo_status == 'Cancelada'`, exigir `motivo_cancelamento`
    - Para `novo_status == 'Realizada'`: dentro de uma transação, inserir linha em `atendimentos` com `tipo='Visita Domiciliar'`, `origem='Visita Domiciliar'`, `data=data_realizada`, `cpf=cpf_rf`, `nome_rf`, `usuario_id=session['usuario_id']`, `criado_em=now`; em caso de falha, manter status inalterado e flash `'erro'`; em caso de sucesso, armazenar `id` do atendimento em `solicitacoes_visita.atendimento_id`
    - Executar `UPDATE solicitacoes_visita SET status=?, data_realizada=?, motivo_cancelamento=?, atualizado_em=? WHERE id=?`
    - Chamar `audit('VISITA_STATUS_ATUALIZADO', ...)` com id, status anterior e novo; chamar `audit('VISITA_CONCLUIDA', ...)` quando `Realizada`
    - Flash `'ok'` e redirecionar para `detalhe_visita`
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ] 7.2 Escrever teste de propriedade: transições de status exigem campos condicionais corretos
    - **Property 11: Transições de status exigem campos condicionais corretos**
    - **Validates: Requisitos 3.2, 3.3, 3.4, 3.5**
    - Usar `@given` para gerar solicitações e combinações de `(novo_status, data_realizada, motivo_cancelamento)`; verificar as 4 combinações válidas/inválidas
    - _Requisitos: 3.2, 3.3, 3.4, 3.5_
  - [ ] 7.3 Escrever teste de propriedade: atualização de status gera auditoria com estado anterior e novo
    - **Property 12: Atualização de status gera auditoria com estado anterior e novo**
    - **Validates: Requisito 3.8**
    - Para qualquer transição bem-sucedida, verificar que existe entrada em `audit_log` com `acao='VISITA_STATUS_ATUALIZADO'` contendo id, status anterior e novo no campo `detalhe`
    - _Requisitos: 3.8_

- [x] 8. Implementar rota `POST /visitas/<id>/excluir` e histórico de status
  - [x] 8.1 Criar rota `excluir_visita` em `app.py`
    - Proteger com `_requer_login()`; verificar `session['perfil'] == 'admin'`; se não, redirecionar silenciosamente para `painel_visitas` (padrão de `excluir_atendimento`)
    - Buscar solicitação com `_fetchone`; se não existir, redirecionar para `painel_visitas`
    - Executar `DELETE FROM solicitacoes_visita WHERE id=?`
    - Chamar `audit('VISITA_EXCLUIDA', ...)` com id e cpf_rf
    - Flash `'ok'` e redirecionar para `painel_visitas`
    - _Requisitos: 6.1, 6.2, 6.3_
  - [x] 8.2 Adicionar seção de histórico de status em `detalhe_visita.html`
    - Renderizar entradas de `audit_log` filtradas por `detalhe LIKE '%id:<visita_id>%'` em ordem cronológica crescente
    - Exibir: data/hora, nome do usuário (`usuario_nome`), ação, detalhe
    - _Requisitos: 6.1_
  - [ ] 8.3 Escrever teste de propriedade: exclusão é restrita a admin e gera auditoria
    - **Property 13: Exclusão é restrita a admin e gera auditoria**
    - **Validates: Requisitos 6.1, 6.3**
    - Usar `@given` para gerar solicitações e perfis de usuário; verificar que: POST de entrevistador é bloqueado e registro permanece; DELETE de admin remove o registro e gera entrada em `audit_log` com `acao='VISITA_EXCLUIDA'`
    - _Requisitos: 6.1, 6.3_

- [x] 9. Checkpoint — verificar rotas e templates do núcleo
  - Garantir que todas as 6 rotas respondem corretamente (criar, painel, detalhe, editar, atualizar status, excluir), que os templates renderizam sem erros Jinja2, e que os ciclos de vida Pendente → Realizada e Pendente → Cancelada funcionam end-to-end. Todos os testes das tarefas 2–8 devem passar.

- [x] 10. Integrar módulo com `base.html` e `dashboard.html`
  - [x] 10.1 Adicionar link "Visitas" na `<nav>` de `templates/base.html`
    - Inserir `<a href="{{ url_for('painel_visitas') }}" class="nav-link {% if request.endpoint == 'painel_visitas' %}ativo{% endif %}">Visitas</a>` na posição adequada na navegação
    - Verificar que a classe `ativo` é aplicada corretamente quando o endpoint é `painel_visitas`
    - _Requisitos: 7.1, 7.2, 7.3_
  - [x] 10.2 Adicionar card de visitas pendentes em `templates/dashboard.html`
    - Adicionar `stat-card` na `stats-grid` exibindo a contagem de solicitações `status='Pendente'` visíveis para o usuário atual
    - O card deve ser um link para `url_for('painel_visitas', status='Pendente')`
    - _Requisitos: 9.1, 9.2_
  - [x] 10.3 Atualizar a rota `dashboard` em `app.py` para calcular `total_visitas_pendentes`
    - Adicionar query `SELECT COUNT(*) ...` com o filtro de visibilidade por perfil
    - Passar `total_visitas_pendentes` ao contexto do template `dashboard.html`
    - _Requisitos: 9.1_
  - [ ] 10.4 Escrever teste de propriedade: dashboard exibe contagem correta de Pendentes visíveis
    - **Property 15: Dashboard exibe contagem correta de Pendentes visíveis**
    - **Validates: Requisito 9.1**
    - Usar `@given` para gerar conjuntos de solicitações com status variados e diferentes usuários; verificar que a contagem retornada para cada usuário é igual ao número de registros `status='Pendente'` visíveis para aquele usuário
    - _Requisitos: 9.1_
  - [ ] 10.5 Escrever testes de exemplo: navegação e link ativo
    - Verificar que o link "Visitas" está presente na nav para usuário autenticado (Req. 7.1)
    - Verificar que a classe `ativo` é aplicada ao link quando o endpoint é `painel_visitas` (Req. 7.2)
    - Verificar que o card do dashboard é um link para `painel_visitas?status=Pendente` (Req. 9.2)
    - _Requisitos: 7.1, 7.2, 9.2_

- [ ] 11. Escrever testes de integração
  - [ ] 11.1 Escrever teste de integração: ciclo de vida completo Pendente → Realizada
    - Criar solicitação → atualizar status para `Em Andamento` → atualizar para `Realizada` com `data_realizada`
    - Verificar que um atendimento do tipo `Visita Domiciliar` foi criado na tabela `atendimentos`
    - Verificar que `atendimento_id` foi armazenado na solicitação
    - Verificar que `audit_log` contém entradas para `VISITA_CRIADA`, `VISITA_STATUS_ATUALIZADO` (x2) e `VISITA_CONCLUIDA`
    - _Requisitos: 5.1, 5.2, 5.4, 5.5_
  - [ ] 11.2 Escrever teste de integração: ciclo de cancelamento Pendente → Cancelada
    - Criar solicitação → atualizar para `Cancelada` com `motivo_cancelamento`
    - Verificar que nenhum atendimento foi criado
    - Verificar que `motivo_cancelamento` foi persistido
    - _Requisitos: 3.4, 3.5_
  - [ ] 11.3 Escrever teste de integração: visibilidade cruzada entre entrevistadores
    - Criar solicitações para dois entrevistadores distintos (A e B)
    - Autenticar como entrevistador A e verificar que o painel não exibe solicitações do entrevistador B
    - Verificar que `detalhe_visita` redireciona entrevistador A ao tentar acessar solicitação do entrevistador B
    - _Requisitos: 2.2, 6.3_
  - [ ] 11.4 Escrever teste de integração: filtros combinados (status + período + texto)
    - Popular tabela com registros variados
    - Enviar GET ao painel com `status`, `data_ini`, `data_fim` e `busca` combinados
    - Verificar que somente registros que satisfazem **todos** os critérios simultaneamente são retornados
    - _Requisitos: 2.4, 2.5, 2.6_

- [x] 12. Checkpoint final — suite completa de testes
  - Executar `pytest` para garantir que todos os testes (unitários, de propriedade e de integração) passam. Verificar que `init_db()` não levanta exceção quando executado em uma instância já inicializada.

---

## Notes

- Tarefas marcadas com `*` são opcionais (testes de propriedade/integração); podem ser puladas para entrega mais rápida de MVP
- Todos os testes de propriedade usam **Hypothesis** — instalar com `pip install hypothesis pytest`
- Os testes de propriedade devem ser colocados em `tests/test_visitas_properties.py` e os de integração em `tests/test_visitas_integration.py`
- Toda a lógica de banco segue o padrão `get_db()` / `_exec()` / `_fetchone()` / `_fetchall()` com `PH` como placeholder
- Checkpoints (tarefas 3, 9, 12) garantem validação incremental a cada grupo de mudanças

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "2.5", "2.6"] },
    { "id": 4, "tasks": ["3"] },
    { "id": 5, "tasks": ["4.1"] },
    { "id": 6, "tasks": ["4.2", "4.3", "4.4", "4.5"] },
    { "id": 7, "tasks": ["5.1"] },
    { "id": 8, "tasks": ["5.2", "5.3"] },
    { "id": 9, "tasks": ["6.1"] },
    { "id": 10, "tasks": ["6.2", "6.3", "6.4"] },
    { "id": 11, "tasks": ["7.1"] },
    { "id": 12, "tasks": ["7.2", "7.3"] },
    { "id": 13, "tasks": ["8.1", "8.2"] },
    { "id": 14, "tasks": ["8.3"] },
    { "id": 15, "tasks": ["9"] },
    { "id": 16, "tasks": ["10.1", "10.3"] },
    { "id": 17, "tasks": ["10.2", "10.4", "10.5"] },
    { "id": 18, "tasks": ["11.1", "11.2", "11.3", "11.4"] },
    { "id": 19, "tasks": ["12"] }
  ]
}
```
