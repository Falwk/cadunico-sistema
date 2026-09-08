# 🗄️ Dicionário de Dados e Arquitetura do Banco de Dados
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Este documento detalha a estrutura do banco de dados relacional **PostgreSQL (Supabase)** utilizado em produção, incluindo tabelas, tipos de dados, chaves primárias, chaves estrangeiras, índices e políticas de segurança.

---

## 🔒 Segurança em Nível de Linha (Row Level Security - RLS)
Todas as tabelas no schema `public` possuem o **Row Level Security (RLS)** ativado (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).
* **Proteção contra Acesso Externo:** Nenhuma chave anônima da API pública web do Supabase pode consultar ou alterar registros sem autorização.
* **Acesso do Backend:** A aplicação Flask conecta via driver PostgreSQL direto com a conta `postgres` (possuindo privilégios administrativos internos com bypass seguro).

---

## 📊 Estrutura das Tabelas

### 1. Tabela `usuarios`
Armazena as credenciais, perfis de acesso e unidade de lotação dos servidores.

| Coluna | Tipo | Nulo? | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Não | Auto | Identificador único do usuário |
| `nome` | `TEXT` | Não | - | Nome completo do servidor |
| `login` | `TEXT UNIQUE` | Não | - | Nome de usuário para login |
| `senha` | `TEXT` | Não | - | Hash criptográfico PBKDF2/SHA256 |
| `perfil` | `TEXT` | Não | `'entrevistador'` | Perfil: `admin` ou `entrevistador` |
| `acesso_sibec` | `INTEGER` | Não | `0` | Flag de permissão para opções SIBEC (0 ou 1) |
| `trocar_senha` | `INTEGER` | Não | `0` | Flag de troca obrigatória de senha (0 ou 1) |
| `tentativas_login` | `INTEGER` | Não | `0` | Contador de tentativas consecutivas incorretas |
| `email` | `TEXT` | Sim | `NULL` | E-mail institucional do servidor |
| `telefone` | `TEXT` | Sim | `NULL` | Telefone para contato |
| `unidade` | `TEXT` | Sim | `NULL` | Polo: `'Quatro Bocas'` ou `'Tomé-Açu (Sede)'` |

---

### 2. Tabela `atendimentos`
Registra os atendimentos presenciais e orientações prestadas às famílias.

| Coluna | Tipo | Nulo? | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Não | Auto | Identificador único do atendimento |
| `data` | `TEXT` | Não | - | Data do atendimento (`DD/MM/AAAA` ou ISO) |
| `cpf` | `TEXT` | Não | - | CPF do Responsável Familiar (11 dígitos formatados) |
| `nome_rf` | `TEXT` | Não | - | Nome do Responsável Familiar (apenas letras) |
| `bairro` | `TEXT` | Não | - | Bairro urbano ou comunidade/ramal rural |
| `codigo_familiar` | `TEXT` | Não | - | Código Familiar gerado no Cadastro Único |
| `qtd_membros` | `INTEGER` | Não | - | Quantidade de membros na composição familiar |
| `renda_per_capita`| `TEXT` | Não | - | Renda familiar per capita formatada (ex: `R$ 218,00`) |
| `origem` | `TEXT` | Não | - | Origem: `Demanda Espontânea`, `Encaminhamento`, etc. |
| `tipos` | `TEXT` | Não | - | Tipos de atendimento selecionados (JSON/separado por vírgula) |
| `usuario_id` | `INTEGER REFERENCES usuarios(id)` | Não | - | ID do entrevistador que realizou o atendimento |
| `orgao_encaminhador`| `TEXT` | Sim | `NULL` | Órgão que originou o ofício (CRAS, CREAS, Judiciário...) |
| `numero_oficio` | `TEXT` | Sim | `NULL` | Número do ofício de encaminhamento |
| `data_encaminhamento`| `TEXT` | Sim | `NULL` | Data de recebimento do ofício |
| `servidor_encaminhador`| `TEXT` | Sim | `NULL` | Nome do servidor solicitante |
| `motivo_encaminhamento`| `TEXT` | Sim | `NULL` | Motivo do encaminhamento |
| `obs_encaminhamento` | `TEXT` | Sim | `NULL` | Observações detalhadas |
| `situacao_encaminhamento`| `TEXT`| Sim | `'Atendido'` | Situação: `Atendido`, `Pendente`, `Cancelado` |

---

### 3. Tabela `solicitacoes_visita`
Controla todo o fluxo de visitas domiciliares, agendamentos, geolocalização e pareceres.

| Coluna | Tipo | Nulo? | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Não | Auto | Identificador numérico da visita |
| `numero_vd` | `TEXT UNIQUE` | Não | - | Código oficial sequencial (ex: `VD-2026-0042`) |
| `cpf_rf` | `TEXT` | Não | - | CPF do Responsável Familiar |
| `nome_rf` | `TEXT` | Não | - | Nome completo do RF |
| `logradouro` | `TEXT` | Não | - | Rua, Travessa, Rodovia ou Ramal |
| `numero` | `TEXT` | Não | - | Número da residência ou `S/N` |
| `complemento` | `TEXT` | Sim | `NULL` | Casa, Bloco, etc. |
| `bairro` | `TEXT` | Não | - | Bairro ou localidade |
| `referencia` | `TEXT` | Sim | `NULL` | Ponto de referência |
| `zona` | `TEXT` | Não | `'Urbana'` | `Urbana` ou `Rural` |
| `motivo` | `TEXT` | Não | - | Motivo da averiguação ou visita |
| `status` | `TEXT` | Não | `'Pendente'`| `Pendente`, `Agendada`, `Realizada`, `Cancelada` |
| `solicitante_id` | `INTEGER REFERENCES usuarios(id)` | Não | - | ID de quem criou a solicitação |
| `responsavel_id` | `INTEGER REFERENCES usuarios(id)` | Sim | `NULL` | ID do técnico designado para a visita |
| `data_solicitacao`| `TEXT` | Não | - | Data de abertura |
| `data_agendada` | `TEXT` | Sim | `NULL` | Data prevista para realização |
| `data_realizada` | `TEXT` | Sim | `NULL` | Data de efetiva conclusão em campo |
| `parecer_tecnico`| `TEXT` | Sim | `NULL` | Relatório descritivo da Assistente Social / Técnico |
| `anexo_url` | `TEXT` | Sim | `NULL` | Link no Cloudinary do documento/ofício |
| `criado_em` | `TEXT` | Não | - | Timestamp ISO de criação |
| `atualizado_em` | `TEXT` | Sim | `NULL` | Timestamp ISO da última alteração |

---

### 4. Tabela `visita_fotos`
Armazena as fotografias comprobatórias tiradas durante a visita domiciliar.

| Coluna | Tipo | Nulo? | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Não | Auto | Identificador da foto |
| `visita_id` | `INTEGER REFERENCES solicitacoes_visita(id) ON DELETE CASCADE` | Não | - | ID da visita vinculada |
| `url` | `TEXT` | Não | - | URL segura da imagem no Cloudinary |
| `descricao` | `TEXT` | Sim | `NULL` | Legenda da foto (ex: Fachada, Cômodos) |
| `criado_em` | `TEXT` | Não | - | Data/hora do envio |

---

### 5. Tabela `audit_log`
Trilha de auditoria para conformidade e segurança da informação.

| Coluna | Tipo | Nulo? | Padrão | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Não | Auto | Identificador do log |
| `timestamp` | `TEXT` | Não | - | Data/hora no fuso horário oficial de Belém/PA |
| `usuario_id` | `INTEGER` | Sim | `NULL` | ID do usuário que executou a ação |
| `usuario_nome`| `TEXT` | Sim | `NULL` | Nome do usuário |
| `acao` | `TEXT` | Não | - | Código da ação (ex: `LOGIN`, `REGISTRAR_ATENDIMENTO`, `EXCLUIR_ATENDIMENTO`) |
| `detalhes` | `TEXT` | Sim | `NULL` | Metadados (IDs, CPFs manipulados, IP) |

---

### 6. Tabela `config_relatorio`
Armazena parâmetros institucionais, cabeçalhos de ofícios e configurações do sistema.

| Coluna | Tipo | Nulo? | Descrição |
| :--- | :--- | :---: | :--- |
| `chave` | `TEXT PRIMARY KEY` | Não | Identificador da configuração (ex: `telegram_bot_token`, `nome_coordenador`) |
| `valor` | `TEXT` | Sim | Conteúdo da configuração |

---

### 7. Tabela `documentos_editaveis`
Modelos de formulários, termos de declaração e ofícios oficiais gerados dinamicamente em PDF e DOCX.
