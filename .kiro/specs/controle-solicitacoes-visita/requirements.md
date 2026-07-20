# Requirements Document

## Introduction

O módulo de **Controle de Solicitações de Visita** adiciona ao sistema CadÚnico/PBF a capacidade de registrar, acompanhar e concluir solicitações de visita domiciliar. Atualmente, visitas domiciliares são registradas apenas como um tipo de atendimento (`Visita Domiciliar`), sem nenhum fluxo de solicitação prévia, agendamento, atribuição a entrevistadores ou controle de situação (pendente → agendada → realizada/cancelada).

O módulo permitirá que supervisores e entrevistadores registrem solicitações de visita vinculadas a um beneficiário (CPF), acompanhem o status de cada solicitação e, ao concluir a visita, gerem automaticamente um atendimento do tipo "Visita Domiciliar" no sistema existente.

---

## Glossary

- **Solicitacao_Visita**: Registro de uma solicitação de visita domiciliar a um beneficiário, contendo dados do beneficiário, motivo, status e histórico de alterações.
- **Beneficiario**: Pessoa cadastrada no CadÚnico identificada pelo CPF do Responsável Familiar (RF).
- **Entrevistador**: Usuário com perfil `entrevistador` ou `admin`, responsável por executar a visita domiciliar.
- **Solicitante**: Usuário que criou a solicitação de visita (qualquer usuário autenticado).
- **Sistema**: A aplicação Flask CadÚnico/PBF.
- **Status_Visita**: Estado atual de uma solicitação, podendo ser: `Pendente`, `Agendada`, `Realizada` ou `Cancelada`.
- **Painel_Visitas**: Tela do módulo que lista e filtra todas as solicitações de visita.
- **Historico_Visita**: Registro imutável de todas as mudanças de status de uma solicitação de visita.

---

## Requirements

### Requisito 1: Registrar Solicitação de Visita

**User Story:** Como entrevistador ou administrador, quero registrar uma solicitação de visita domiciliar para um beneficiário, para que a equipe possa acompanhar e organizar as visitas pendentes.

#### Critérios de Aceitação

1. WHEN um usuário autenticado submete o formulário de nova solicitação com CPF do RF, nome do RF, endereço, data prevista e motivo da visita preenchidos, THE Sistema SHALL criar uma Solicitacao_Visita com Status_Visita igual a `Pendente` e registrar o id do Solicitante, a data/hora de criação e o endereço IP no banco de dados.
2. WHEN o usuário submete o formulário com CPF inválido (que não passa na validação de dígitos verificadores), THE Sistema SHALL rejeitar a submissão e exibir a mensagem "CPF inválido — verifique os dígitos."
3. WHEN o usuário informa um CPF válido no formulário e esse CPF já possui atendimentos registrados no sistema, THE Sistema SHALL preencher automaticamente o campo "Nome do RF" com o nome associado ao atendimento mais recente, ordenado de forma decrescente por data.
4. WHEN o usuário submete o formulário com campo obrigatório em branco (CPF, nome do RF, endereço, data prevista ou motivo), THE Sistema SHALL rejeitar a submissão e exibir mensagem indicando qual campo está faltando.
5. WHEN uma Solicitacao_Visita é criada com sucesso, THE Sistema SHALL registrar no audit_log a ação `CRIAR_SOLICITACAO_VISITA` com o CPF e nome do RF.
6. WHERE o perfil do usuário autenticado for `admin`, THE Sistema SHALL exibir um campo opcional para atribuir a solicitação a um Entrevistador específico no momento da criação, e o entrevistador selecionado SHALL ser salvo como responsável da solicitação.

---

### Requisito 2: Visualizar e Filtrar Solicitações de Visita

**User Story:** Como entrevistador ou administrador, quero visualizar uma lista de solicitações de visita com filtros por status e período, para que eu possa acompanhar o andamento das visitas.

#### Critérios de Aceitação

1. THE Sistema SHALL exibir no Painel_Visitas uma tabela com as colunas: data de solicitação, CPF do RF, nome do RF, motivo, status, entrevistador atribuído e ações disponíveis.
2. WHEN um usuário com perfil `entrevistador` acessa o Painel_Visitas, THE Sistema SHALL exibir apenas as solicitações criadas por esse usuário ou atribuídas a esse usuário.
3. WHEN um usuário com perfil `admin` acessa o Painel_Visitas, THE Sistema SHALL exibir todas as solicitações de todos os usuários.
4. WHEN o usuário aplica o filtro por Status_Visita, THE Sistema SHALL retornar apenas as solicitações com o status selecionado.
5. WHEN o usuário aplica o filtro por período (data inicial e data final), THE Sistema SHALL retornar apenas as solicitações cuja data de criação esteja dentro do intervalo informado, inclusive as datas limites.
6. WHEN o usuário aplica o filtro por CPF ou nome (campo de busca textual), THE Sistema SHALL retornar solicitações cujo CPF contenha ou cujo nome do RF contenha o texto informado (busca parcial, sem distinção de maiúsculas/minúsculas).
7. THE Sistema SHALL exibir contadores de solicitações por status (Pendente, Agendada, Realizada, Cancelada) no topo do Painel_Visitas.
8. WHEN não há solicitações correspondentes aos filtros aplicados, THE Sistema SHALL exibir a mensagem "Nenhuma solicitação encontrada para os filtros selecionados."

---

### Requisito 3: Atualizar Status da Solicitação de Visita

**User Story:** Como entrevistador ou administrador, quero atualizar o status de uma solicitação de visita, para que o sistema reflita o andamento real do processo.

#### Critérios de Aceitação

1. WHEN um usuário autenticado altera o Status_Visita de uma Solicitacao_Visita para qualquer valor válido (`Pendente`, `Agendada`, `Realizada`, `Cancelada`), THE Sistema SHALL salvar o novo status e registrar a transição no Historico_Visita com o id do usuário, o status anterior, o status novo e a data/hora da alteração.
2. WHEN o usuário altera o status para `Agendada`, THE Sistema SHALL exibir um campo obrigatório para informar a data agendada da visita.
3. IF o usuário tenta salvar o status `Agendada` sem preencher a data agendada, THEN THE Sistema SHALL rejeitar a operação e exibir a mensagem "Informe a data agendada para a visita."
4. WHEN o usuário altera o status para `Cancelada`, THE Sistema SHALL exigir o preenchimento de um campo de observação com o motivo do cancelamento.
5. IF o usuário tenta salvar o status `Cancelada` sem preencher o motivo, THEN THE Sistema SHALL rejeitar a operação e exibir a mensagem "Informe o motivo do cancelamento."
6. WHILE o Status_Visita de uma Solicitacao_Visita for `Realizada` ou `Cancelada`, THE Sistema SHALL exibir os controles de alteração de status como desabilitados.
7. WHEN um usuário com perfil `entrevistador` tenta alterar o status de uma solicitação que não foi criada por ele e não está atribuída a ele, THE Sistema SHALL rejeitar a operação e redirecionar para o Painel_Visitas.
8. THE Sistema SHALL registrar no audit_log a ação `ATUALIZAR_STATUS_VISITA` com o id da solicitação, o status anterior e o novo status a cada alteração bem-sucedida.

---

### Requisito 4: Atribuir Entrevistador à Solicitação

**User Story:** Como administrador, quero atribuir um entrevistador a uma solicitação de visita, para que fique claro quem é responsável por realizar a visita.

#### Critérios de Aceitação

1. WHEN um usuário com perfil `admin` seleciona um Entrevistador e salva a atribuição em uma Solicitacao_Visita, THE Sistema SHALL registrar o id do Entrevistador atribuído na Solicitacao_Visita e registrar a alteração no Historico_Visita.
2. WHEN um usuário com perfil `entrevistador` tenta atribuir ou reatribuir o entrevistador de uma solicitação, THE Sistema SHALL rejeitar a operação sem alterar a solicitação.
3. WHERE um Entrevistador estiver atribuído a uma Solicitacao_Visita, THE Sistema SHALL exibir o nome do Entrevistador na tabela do Painel_Visitas.
4. THE Sistema SHALL registrar no audit_log a ação `ATRIBUIR_ENTREVISTADOR_VISITA` com o id da solicitação e o id do entrevistador atribuído.

---

### Requisito 5: Concluir Visita e Gerar Atendimento

**User Story:** Como entrevistador ou administrador, quero registrar a conclusão de uma visita domiciliar e gerar automaticamente um atendimento no sistema, para que o registro de atendimentos reflita a visita realizada.

#### Critérios de Aceitação

1. WHEN o usuário altera o Status_Visita para `Realizada` e confirma a conclusão, THE Sistema SHALL criar automaticamente um registro na tabela `atendimentos` com tipo `Visita Domiciliar`, CPF e nome do RF da Solicitacao_Visita, origem `Visita Domiciliar`, data igual à data de realização informada e usuario_id do usuário que está concluindo a visita.
2. WHEN o atendimento é gerado a partir de uma Solicitacao_Visita, THE Sistema SHALL armazenar o id do atendimento gerado na Solicitacao_Visita para permitir rastreabilidade.
3. IF a criação do atendimento falhar por qualquer motivo, THEN THE Sistema SHALL manter o Status_Visita inalterado e exibir a mensagem "Erro ao gerar atendimento. Tente novamente."
4. WHEN a conclusão da visita é registrada com sucesso, THE Sistema SHALL exibir ao usuário um link direto para o atendimento gerado.
5. THE Sistema SHALL registrar no audit_log a ação `CONCLUIR_VISITA` com o id da solicitação e o id do atendimento gerado.

---

### Requisito 6: Visualizar Histórico de uma Solicitação

**User Story:** Como entrevistador ou administrador, quero visualizar o histórico completo de alterações de uma solicitação de visita, para que eu possa auditar o processo de cada visita.

#### Critérios de Aceitação

1. WHEN o usuário acessa a página de detalhes de uma Solicitacao_Visita, THE Sistema SHALL exibir o Historico_Visita em ordem cronológica crescente, mostrando: data/hora da alteração, nome do usuário que realizou a alteração, status anterior, novo status e observação (quando houver).
2. THE Sistema SHALL exibir, na página de detalhes da solicitação, o link para o atendimento gerado quando o Status_Visita for `Realizada`.
3. WHEN um usuário com perfil `entrevistador` tenta acessar a página de detalhes de uma Solicitacao_Visita que não está vinculada a ele, THE Sistema SHALL redirecionar para o Painel_Visitas sem exibir os dados da solicitação.

---

### Requisito 7: Acesso e Navegação pelo Menu

**User Story:** Como usuário autenticado, quero acessar o módulo de Controle de Solicitações de Visita pelo menu principal, para que eu possa navegar facilmente até a funcionalidade.

#### Critérios de Aceitação

1. WHEN um usuário autenticado acessa qualquer página do Sistema, THE Sistema SHALL exibir na barra de navegação um link "Visitas" que direciona ao Painel_Visitas.
2. WHEN um usuário não autenticado tenta acessar qualquer rota do módulo de visitas, THE Sistema SHALL redirecionar para a página de login.
3. THE Sistema SHALL manter o estilo visual (cores, fontes, layout) do módulo de visitas consistente com o design existente definido em `base.html`.
